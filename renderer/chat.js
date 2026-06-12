

const MOOD_COLOR = {
  DOMINANT: '#FF2233', COLD: '#00FFFF', IMPRESSED: '#44FF88',
  DANGEROUS: '#FF4400', UNHINGED: '#CC00FF', SOFT: '#FF44FF',
  OBSESSED: '#FF44CC', DISGUSTED: '#AAAA00', BORED: '#888888',
  HAPPY: '#FFCC00', WORRIED: '#AA88FF', FOCUSED: '#00FFEE',
  NEUTRAL: '#AAAAAA',
}

const STAGE_NAMES = ['EGG', 'CHIBI', 'TEEN', 'ADULT', 'ASCENDED']

let currentMood = 'BORED'
let currentState = null
let isWaiting = false
let messages = []



const msgContainer = document.getElementById('chat-messages')
const chatInput    = document.getElementById('chat-input')
const headerMood   = document.getElementById('header-mood')
const headerName   = document.getElementById('header-name')
const headerLevel  = document.getElementById('header-level')
const skillPanel   = document.getElementById('skill-panel')
const skillList    = document.getElementById('skill-list')
const skillClose   = document.getElementById('skill-close')



function timeNow() {
  const d = new Date()
  return `${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}



function addMessage(role, text, mood) {
  const wrap = document.createElement('div')
  const col  = MOOD_COLOR[mood || currentMood] || '#AAAAAA'

  if (role === 'user') {
    wrap.className = 'msg-user'
    wrap.innerHTML = `<div>${escHtml(text)}</div><div class="msg-time">${timeNow()}</div>`
  } else {
    wrap.className = 'msg-pet'
    wrap.style.borderLeft = `2px solid ${col}`
    wrap.style.color = col
    wrap.innerHTML = `<div>${escHtml(text)}</div><div class="msg-time" style="color:rgba(255,255,255,0.3)">${timeNow()}</div>`
  }

  messages.push({ role, text, mood, wrap })
  if (messages.length > 50) {
    const old = messages.shift()
    if (old.wrap.parentNode) old.wrap.parentNode.removeChild(old.wrap)
  }

  msgContainer.appendChild(wrap)
  msgContainer.scrollTop = msgContainer.scrollHeight
}

function escHtml(s) {
  return String(s)
    .replace(/&/g,'&amp;')
    .replace(/</g,'&lt;')
    .replace(/>/g,'&gt;')
    .replace(/\n/g,'<br>')
}



let typingEl = null

function showTyping() {
  if (typingEl) return
  typingEl = document.createElement('div')
  typingEl.className = 'typing-dots'
  typingEl.innerHTML = '<span></span><span></span><span></span>'
  msgContainer.appendChild(typingEl)
  msgContainer.scrollTop = msgContainer.scrollHeight
}

function hideTyping() {
  if (typingEl) {
    typingEl.remove()
    typingEl = null
  }
}



async function sendMessage(text) {
  text = text.trim()
  if (!text) return

  
  if (text.startsWith('/')) {
    await handleCommand(text)
    return
  }

  if (isWaiting) return

  isWaiting = true
  addMessage('user', text)
  chatInput.value = ''
  chatInput.style.height = 'auto'
  showTyping()

  try {
    const res = await window.cw.chat(text)
    hideTyping()
    if (res && res.reply) {
      addMessage('pet', res.reply, res.mood)
      if (res.mood) updateMoodDisplay(res.mood)
      if (res.xp_gained) {
        
        const prev = headerLevel.textContent
        headerLevel.style.color = '#00FFCC'
        setTimeout(() => { headerLevel.style.color = 'rgba(255,255,255,0.25)' }, 800)
      }
    } else {
      addMessage('pet', '*she stares blankly*', currentMood)
    }
  } catch {
    hideTyping()
    addMessage('pet', '*connection lost*', 'BORED')
  }

  isWaiting = false
}



async function handleCommand(cmd) {
  const parts = cmd.split(' ')
  const base  = parts[0].toLowerCase()

  switch (base) {
    case '/feed': {
      const food = parts[1] || 'snack'
      addMessage('user', cmd)
      chatInput.value = ''
      showTyping()
      try {
        const res = await window.cw.feed(food)
        hideTyping()
        if (res && res.message) addMessage('pet', res.message, res.mood)
        else addMessage('pet', `*eats the ${food}*`, 'HAPPY')
      } catch {
        hideTyping()
        addMessage('pet', '*chews something*', 'HAPPY')
      }
      break
    }

    case '/skills': {
      addMessage('user', '/skills')
      chatInput.value = ''
      await openSkillPanel()
      break
    }

    case '/status': {
      addMessage('user', '/status')
      chatInput.value = ''
      if (currentState && currentState.pet) {
        const p = currentState.pet
        const per = currentState.personality || {}
        const lines = [
          `name: ${p.name || 'waifu'}  stage: ${STAGE_NAMES[p.evolution_stage||0].toLowerCase()}`,
          `level: ${p.level}  xp: ${p.xp}/${p.xp_next}`,
          `hunger: ${Math.round(p.hunger)}  trust: ${p.trust}  affection: ${p.affection}`,
          `mood: ${(p.current_mood||'bored').toLowerCase()}`,
          `warm: ${(per.warmth||0).toFixed(2)}  play: ${(per.playfulness||0).toFixed(2)}  clingy: ${(per.clinginess||0).toFixed(2)}`,
          `chaos: ${(per.chaos||0).toFixed(2)}  express: ${(per.expressiveness||0).toFixed(2)}`,
        ].join('\n')
        addMessage('pet', lines, currentMood)
      } else {
        addMessage('pet', '*no data*', currentMood)
      }
      break
    }

    case '/diary': {
      addMessage('user', '/diary')
      chatInput.value = ''
      isWaiting = true
      showTyping()
      try {
        const res = await window.cw.chat('/diary')
        hideTyping()
        addMessage('pet', res?.reply || '*no diary yet*', res?.mood || currentMood)
      } catch {
        hideTyping()
        addMessage('pet', '*diary pages are blank*', currentMood)
      }
      isWaiting = false
      break
    }

    case '/roast': {
      addMessage('user', '/roast')
      chatInput.value = ''
      isWaiting = true
      showTyping()
      try {
        const res = await window.cw.chat('/roast me')
        hideTyping()
        addMessage('pet', res?.reply || '*she considers it*', res?.mood || currentMood)
      } catch {
        hideTyping()
        addMessage('pet', '*she considers roasting you... another time*', currentMood)
      }
      isWaiting = false
      break
    }

    case '/name': {
      const name = parts.slice(1).join(' ')
      if (name) {
        chatInput.value = ''
        try {
          await fetch('http://127.0.0.1:7432/setname', {
            method: 'POST', headers: {'Content-Type':'application/json'},
            body: JSON.stringify({name})
          })
          addMessage('user', cmd)
          addMessage('pet', `*she looks up* ...${name}? she'll remember that.`, currentMood)
        } catch { addMessage('pet', '*she ignores you*', currentMood) }
      }
      break
    }

    case '/outfit': {
      const outfit = parts[1] || 'seifuku2'
      addMessage('user', cmd)
      chatInput.value = ''
      try {
        await fetch('http://127.0.0.1:7432/outfit', {
          method: 'POST',
          headers: {'Content-Type':'application/json'},
          body: JSON.stringify({outfit})
        })
        addMessage('pet', `*changes into ${outfit}*`, currentMood)
        await fetch('http://127.0.0.1:7432/regen-sprites', {method:'POST'}).catch(()=>{})
      } catch { addMessage('pet', '*ignores the wardrobe*', currentMood) }
      break
    }

    case '/pomo': {
      const minutes = parseInt(parts[1]) || 25
      addMessage('pet', `*sets timer for ${minutes} minutes. don't slack.*`, currentMood)
      chatInput.value = ''
      fetch('http://127.0.0.1:7432/pomo-start', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({minutes})
      }).catch(()=>{})
      setTimeout(() => {
        new Notification('CodeWaifu', { body: `${minutes} minutes. take a break.` })
      }, minutes * 60 * 1000)
      break
    }

    default:
      addMessage('pet', `unknown command: ${base}`, currentMood)
      chatInput.value = ''
  }
}



async function openSkillPanel() {
  skillPanel.classList.add('open')
  skillList.innerHTML = '<div style="color:rgba(255,255,255,0.3);font-size:10px;letter-spacing:1px;margin-bottom:8px">SKILLS</div>'

  try {
    const res = await window.cw.getSkills()
    const skills = res?.skills || res || []
    if (!skills.length) {
      skillList.innerHTML += '<div style="color:rgba(255,255,255,0.2);font-size:11px">no skills yet</div>'
      return
    }

    for (const s of skills) {
      const div = document.createElement('div')
      div.className = `skill-item ${s.unlocked ? 'unlocked' : ''}`
      const statusColor = s.unlocked ? '#00FFCC' : 'rgba(255,80,80,0.5)'
      const statusText  = s.unlocked ? 'unlocked' : `lv ${s.unlock_level} to unlock`
      div.innerHTML = `
        <div class="skill-name">${s.name}</div>
        <div class="skill-meta">${s.description || s.category || ''}</div>
        <div class="skill-lock" style="color:${statusColor}">${statusText}</div>
      `
      if (s.unlocked) {
        div.style.cursor = 'pointer'
        div.addEventListener('click', async () => {
          try { await window.cw.teachSkill(s.id) } catch {}
        })
      }
      skillList.appendChild(div)
    }
  } catch {
    skillList.innerHTML += '<div style="color:rgba(255,80,80,0.5);font-size:11px">failed to load skills</div>'
  }
}

skillClose.addEventListener('click', () => {
  skillPanel.classList.remove('open')
})



function updateMoodDisplay(mood) {
  currentMood = mood || 'BORED'
  const col = MOOD_COLOR[currentMood] || '#888888'
  headerMood.textContent = `mood: ${currentMood.toLowerCase()}`
  headerMood.style.color = col
}

function applyState(state) {
  if (!state) return
  currentState = state
  const pet = state.pet || {}
  headerName.textContent  = (pet.name || 'waifu').toUpperCase()
  headerLevel.textContent = `lv ${pet.level || 1}`
  updateMoodDisplay(pet.current_mood)
}



chatInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage(chatInput.value)
  }
})

chatInput.addEventListener('input', () => {
  chatInput.style.height = 'auto'
  chatInput.style.height = Math.min(chatInput.scrollHeight, 80) + 'px'
})


window.addEventListener('focus', () => {
  chatInput.focus()
})


document.querySelectorAll('.pill').forEach((pill) => {
  pill.addEventListener('click', () => {
    const cmd = pill.dataset.cmd
    chatInput.value = cmd + ' '
    chatInput.focus()
  })
})



window.cw?.onStateUpdate((state) => applyState(state))
window.cw?.onAwarenessEvent((evt) => {
  if (evt && evt.message) {
    addMessage('pet', evt.message, evt.mood || currentMood)
  }
  if (evt && evt.mood) updateMoodDisplay(evt.mood)
})


;(async () => {
  try {
    const state = await window.cw?.getState()
    applyState(state)
    addMessage('pet', '...', currentMood)
  } catch {
    addMessage('pet', '*backend offline*', 'BORED')
  }
  chatInput.focus()
})()
