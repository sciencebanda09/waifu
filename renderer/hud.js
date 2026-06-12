

const MOOD_COLOR = {
  DOMINANT: '#FF2233', COLD: '#00FFFF', IMPRESSED: '#44FF88',
  DANGEROUS: '#FF4400', UNHINGED: '#CC00FF', SOFT: '#FF44FF',
  OBSESSED: '#FF44CC', DISGUSTED: '#AAAA00', BORED: '#888888',
  HAPPY: '#FFCC00', WORRIED: '#AA88FF', FOCUSED: '#00FFEE',
  NEUTRAL: '#AAAAAA',
}

const STAGE_NAMES = ['EGG', 'CHIBI', 'TEEN', 'ADULT', 'ASCENDED']

function el(id) { return document.getElementById(id) }

function animateBar(barEl, targetPct) {
  barEl.style.width = targetPct + '%'
}

function updateHUD(state) {
  if (!state || !state.pet) return
  const pet = state.pet
  const lp  = state.level_progress || {}

  
  el('pet-name').textContent = (pet.name || 'WAIFU').toUpperCase()
  el('stage-badge').textContent = STAGE_NAMES[pet.evolution_stage || 0]

  
  const mood = pet.current_mood || 'BORED'
  const col  = MOOD_COLOR[mood] || '#888888'
  el('mood-dot').style.background = col
  el('mood-name').textContent = mood

  
  el('level').textContent = pet.level || 1
  const xpCur  = pet.xp || 0
  const xpNext = pet.xp_next || 100
  const xpPct  = Math.min(100, Math.round((xpCur / xpNext) * 100))
  el('xp-text').textContent = `${xpCur} / ${xpNext} XP`
  animateBar(el('xp-bar'), xpPct)

  
  const hunger = Math.max(0, Math.min(100, pet.hunger || 0))
  el('hunger-text').textContent = Math.round(hunger)
  animateBar(el('hunger-bar'), hunger)

  const hBar = el('hunger-bar')
  hBar.classList.remove('hunger-low', 'hunger-critical')
  if (hunger <= 5) {
    hBar.classList.add('hunger-critical')
  } else if (hunger <= 20) {
    hBar.classList.add('hunger-low')
  }
}


async function poll() {
  try {
    const state = await window.cw?.getState()
    if (state) updateHUD(state)
  } catch {}
}

poll()
setInterval(poll, 3000)

window.cw?.onStateUpdate((state) => updateHUD(state))
window.cw?.onAwarenessEvent((evt) => {
  if (evt && evt.type === 'hunger_warning') {
    const hBar = el('hunger-bar')
    hBar.classList.add('hunger-critical')
  }
})


setInterval(() => { fetch('http://127.0.0.1:7432/ping', {method:'POST'}).catch(()=>{}) }, 60000)
