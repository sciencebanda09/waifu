

const MOOD_COLOR = {
  DOMINANT: '#FF2233', COLD: '#00FFFF', IMPRESSED: '#44FF88',
  DANGEROUS: '#FF4400', UNHINGED: '#CC00FF', SOFT: '#FF44FF',
  OBSESSED: '#FF44CC', DISGUSTED: '#AAAA00', BORED: '#888888',
  HAPPY: '#FFCC00', WORRIED: '#AA88FF', FOCUSED: '#00FFEE',
  NEUTRAL: '#AAAAAA',
}

const MOODS = ['DOMINANT','COLD','IMPRESSED','DANGEROUS','UNHINGED','SOFT',
               'OBSESSED','DISGUSTED','BORED','HAPPY','WORRIED','FOCUSED']

const STAGE_PREFIX = ['EGG', 'CHIBI', 'TEEN', 'ADULT', 'ASCENDED']

const ANIM_STATES = {
  IDLE:         { frames: [0,1,2],     fps: 4,  loop: true  },
  BLINK:        { frames: ['blink'],   fps: 8,  loop: false, next: 'IDLE' },
  SLEEP:        { frames: ['sleep'],   fps: 1,  loop: true  },
  REACT:        { frames: [0,1,2,1,0], fps: 8,  loop: false, next: 'IDLE' },
  HAPPY_BOUNCE: { frames: [0,1,2,1],   fps: 10, loop: false, next: 'IDLE' },
  EAT:          { frames: [0,1,2,1,0], fps: 6,  loop: false, next: 'IDLE' },
}



let currentState = null
let currentMood = 'BORED'
let currentStage = 0
let animState = 'IDLE'
let animFrame = 0
let animTimer = 0
let breathPhase = 0


let isDragging = false
let dragStartTime = 0
let dragStartX = 0, dragStartY = 0
let velX = 0, velY = 0
let lastMouseX = 0, lastMouseY = 0
let longPressTimer = null


let bubbleActive = false
let bubbleTimer = 0
let bubbleDuration = 180
let bubbleFullText = ''
let bubbleDisplayText = ''
let bubbleTypingIndex = 0
let bubbleTypingTimer = 0


const particles = []


const texCache = {}



const app = new PIXI.Application({
  width: 240,
  height: 320,
  backgroundAlpha: 0,
  antialias: true,
  resolution: window.devicePixelRatio || 1,
  autoDensity: true,
})
document.body.appendChild(app.view)

const petContainer = new PIXI.Container()
petContainer.x = 120
petContainer.y = 290
app.stage.addChild(petContainer)

const spriteHolder = new PIXI.Container()
petContainer.addChild(spriteHolder)

let currentSprite = null


const bubbleGraphics = new PIXI.Graphics()
const bubbleText = new PIXI.Text('', {
  fontFamily: 'Courier New, monospace',
  fontSize: 11,
  fill: 0xffffff,
  wordWrap: true,
  wordWrapWidth: 180,
  lineHeight: 15,
})
bubbleGraphics.addChild(bubbleText)
bubbleGraphics.x = -110
bubbleGraphics.y = -260
bubbleGraphics.visible = false
app.stage.addChild(bubbleGraphics)


const glowFilter = null



function spritePath(mood, stage, frameKey) {
  const prefix = STAGE_PREFIX[stage] || 'EGG'
  const base = (location.href.replace(/renderer\/[^/]*$/, '') + 'assets/sprites/')
  if (stage === 0) {
    if (frameKey === 'sleep') return `${base}EGG_sleep.png`
    if (frameKey === 'blink') return `${base}EGG_idle_0.png`
    return `${base}EGG_idle_${frameKey}.png`
  }
  if (frameKey === 'blink') return `${base}${prefix}_${mood}_blink.png`
  if (frameKey === 'sleep') return `${base}sleep.png`
  return `${base}${prefix}_${mood}_idle_${frameKey}.png`
}

async function loadTexture(path) {
  if (texCache[path]) return texCache[path]
  try {
    const tex = await PIXI.Assets.load(path)
    texCache[path] = tex
    return tex
  } catch {
    
    const fallback = `../assets/sprites/HAPPY_idle_0.png`
    if (texCache[fallback]) return texCache[fallback]
    try {
      const t = await PIXI.Assets.load(fallback)
      texCache[path] = t
      texCache[fallback] = t
      return t
    } catch {
      return PIXI.Texture.WHITE
    }
  }
}

async function setSprite(mood, stage, frameKey) {
  const path = spritePath(mood, stage, frameKey)
  const tex = await loadTexture(path)
  if (currentSprite) spriteHolder.removeChild(currentSprite)
  currentSprite = new PIXI.Sprite(tex)
  currentSprite.anchor.set(0.5, 1.0)
  currentSprite.x = 0
  currentSprite.y = 0
  currentSprite.scale.set(0.5)
  spriteHolder.addChild(currentSprite)
}



function enterAnimState(name) {
  animState = name
  animFrame = 0
  animTimer = 0
}

let ticksSinceLastBlink = 0
let nextBlinkAt = randomRange(180, 420) 
let ticksSinceLastIdle = 0
let nextIdleAt = randomRange(900, 1800)

function randomRange(min, max) {
  return Math.floor(Math.random() * (max - min)) + min
}

app.ticker.add((delta) => {
  
  breathPhase += 0.018 * delta
  const breathY = 1 + Math.sin(breathPhase) * 0.012
  const breathX = 1 - Math.sin(breathPhase) * 0.006
  petContainer.scale.set(breathX, breathY)

  
  if (currentStage >= 4) {
    const color = MOOD_COLOR[currentMood] || '#AAAAAA'
    spawnAscendedAura()
  }

  
  const state = ANIM_STATES[animState]
  if (state) {
    animTimer += delta
    const interval = 60 / state.fps
    if (animTimer >= interval) {
      animTimer = 0
      animFrame++
      if (animFrame >= state.frames.length) {
        if (state.loop) {
          animFrame = 0
        } else {
          enterAnimState(state.next || 'IDLE')
          return
        }
      }
      const frameKey = state.frames[animFrame]
      setSprite(currentMood, currentStage, frameKey)
    }
  }

  
  ticksSinceLastBlink += delta
  if (animState === 'IDLE' && ticksSinceLastBlink >= nextBlinkAt) {
    ticksSinceLastBlink = 0
    nextBlinkAt = randomRange(180, 420)
    enterAnimState('BLINK')
  }

  
  ticksSinceLastIdle += delta
  if (animState === 'IDLE' && ticksSinceLastIdle >= nextIdleAt) {
    ticksSinceLastIdle = 0
    nextIdleAt = randomRange(900, 1800)
    if (Math.random() < 0.4) enterAnimState('REACT')
  }

  
  if (!isDragging && (Math.abs(velX) > 0.1 || Math.abs(velY) > 0.1)) {
    velX *= 0.92
    velY *= 0.92
    const screenW = window.screen.availWidth
    const screenH = window.screen.availHeight
    const petX = window.screenX
    const petY = window.screenY
    if (petX <= 0 || petX >= screenW - 240) velX *= -0.7
    if (petY <= 0 || petY >= screenH - 320) velY *= -0.7
    const pos = { x: app.renderer.view.ownerDocument?.defaultView?.screenX ?? 0, y: 0 }
    window.cw?.onPetDrag(pos.x + velX, pos.y + velY)
  }

  
  updateParticles(delta)

  
  if (bubbleActive) {
    bubbleTypingTimer += delta
    if (bubbleTypingTimer >= 2 && bubbleTypingIndex < bubbleFullText.length) {
      bubbleTypingTimer = 0
      bubbleTypingIndex++
      bubbleDisplayText = bubbleFullText.slice(0, bubbleTypingIndex)
      drawBubble(bubbleDisplayText, currentMood)
    }
    bubbleTimer += delta
    if (bubbleTimer >= bubbleDuration) {
      bubbleActive = false
      bubbleGraphics.visible = false
    }
  }

  
  if (currentStage === 0 && currentSprite) {
    const pulse = 0.85 + Math.sin(breathPhase * 2) * 0.15
    currentSprite.alpha = pulse
  } else if (currentSprite) {
    currentSprite.alpha = 1
  }
})



function wrapText(text, maxChars) {
  const words = text.split(' ')
  const lines = []
  let line = ''
  for (const word of words) {
    if ((line + word).length > maxChars) {
      if (line) lines.push(line.trim())
      line = word + ' '
    } else {
      line += word + ' '
    }
    if (lines.length >= 2) break
  }
  if (lines.length < 2 && line) lines.push(line.trim())
  return lines.slice(0, 2).join('\n')
}

function drawBubble(text, mood) {
  const color = parseInt((MOOD_COLOR[mood] || '#888888').replace('#', ''), 16)
  const padding = 8
  bubbleText.text = text
  const w = Math.min(200, bubbleText.width + padding * 2)
  const h = bubbleText.height + padding * 2
  bubbleGraphics.clear()
  bubbleGraphics.beginFill(0x0a0a0f, 0.92)
  bubbleGraphics.lineStyle(1, color, 0.8)
  bubbleGraphics.drawRoundedRect(0, 0, w, h, 6)
  bubbleGraphics.endFill()
  
  bubbleGraphics.beginFill(0x0a0a0f, 0.92)
  bubbleGraphics.lineStyle(1, color, 0.8)
  bubbleGraphics.moveTo(w / 2 - 6, h)
  bubbleGraphics.lineTo(w / 2, h + 10)
  bubbleGraphics.lineTo(w / 2 + 6, h)
  bubbleGraphics.endFill()
  bubbleText.x = padding
  bubbleText.y = padding
  bubbleGraphics.visible = true
}

function showBubble(text, mood, duration = 180) {
  const wrapped = wrapText(text, 28)
  bubbleFullText = wrapped
  bubbleDisplayText = ''
  bubbleTypingIndex = 0
  bubbleTypingTimer = 0
  bubbleTimer = 0
  bubbleDuration = duration
  bubbleActive = true
  currentMood = mood || currentMood
  drawBubble('', mood)
}



function makeParticle(x, y, vx, vy, color, shape, lifetime) {
  const g = new PIXI.Graphics()
  app.stage.addChild(g)
  const p = { g, x, y, vx, vy, color, shape, lifetime, age: 0 }
  particles.push(p)
  return p
}

function updateParticles(delta) {
  for (let i = particles.length - 1; i >= 0; i--) {
    const p = particles[i]
    p.age += delta
    if (p.age >= p.lifetime) {
      app.stage.removeChild(p.g)
      p.g.destroy()
      particles.splice(i, 1)
      continue
    }
    const life = 1 - p.age / p.lifetime
    p.x += p.vx * delta
    p.y += p.vy * delta
    p.vy += 0.05 * delta 
    p.g.clear()
    p.g.alpha = life
    const col = parseInt(p.color.replace('#', ''), 16)
    p.g.beginFill(col, 1)
    if (p.shape === 'heart') {
      drawHeart(p.g, p.x, p.y, 5 * life)
    } else if (p.shape === 'star') {
      drawStar(p.g, p.x, p.y, 4 * life)
    } else if (p.shape === 'drop') {
      p.g.drawCircle(p.x, p.y, 2 * life)
    } else {
      p.g.drawCircle(p.x, p.y, 2 * life)
    }
    p.g.endFill()
  }
}

function drawHeart(g, x, y, s) {
  g.moveTo(x, y + s * 0.3)
  g.bezierCurveTo(x, y, x - s, y, x - s, y + s * 0.3)
  g.bezierCurveTo(x - s, y + s * 0.7, x, y + s, x, y + s)
  g.bezierCurveTo(x, y + s, x + s, y + s * 0.7, x + s, y + s * 0.3)
  g.bezierCurveTo(x + s, y, x, y, x, y + s * 0.3)
}

function drawStar(g, x, y, r) {
  for (let i = 0; i < 5; i++) {
    const a = (i * 4 * Math.PI) / 5 - Math.PI / 2
    const px = x + Math.cos(a) * r
    const py = y + Math.sin(a) * r
    if (i === 0) g.moveTo(px, py); else g.lineTo(px, py)
  }
  g.closePath()
}

function burstHearts(x, y, n = 6) {
  for (let i = 0; i < n; i++) {
    const angle = -Math.PI / 2 + (Math.random() - 0.5) * Math.PI
    const speed = 0.5 + Math.random() * 1.5
    makeParticle(x, y, Math.cos(angle) * speed, Math.sin(angle) * speed - 1,
      '#FF88AA', 'heart', 80 + Math.random() * 40)
  }
}

function burstStars(x, y, n = 8) {
  for (let i = 0; i < n; i++) {
    const angle = (i / n) * Math.PI * 2
    const speed = 1 + Math.random() * 2
    makeParticle(x, y, Math.cos(angle) * speed, Math.sin(angle) * speed,
      '#FFCC00', 'star', 60 + Math.random() * 40)
  }
}

function burstSparks(x, y, color, n = 10) {
  for (let i = 0; i < n; i++) {
    const angle = Math.random() * Math.PI * 2
    const speed = 0.5 + Math.random() * 3
    makeParticle(x, y, Math.cos(angle) * speed, Math.sin(angle) * speed - 0.5,
      color || '#FF8800', 'spark', 30 + Math.random() * 30)
  }
}

function floatText(x, y, text, color) {
  const t = new PIXI.Text(text, {
    fontFamily: 'Courier New',
    fontSize: 11,
    fill: parseInt((color || '#FFFFFF').replace('#', ''), 16),
    fontWeight: 'bold',
  })
  t.x = x - t.width / 2
  t.y = y
  app.stage.addChild(t)
  let life = 0
  const tick = (delta) => {
    life += delta
    t.y -= 0.5 * delta
    t.alpha = Math.max(0, 1 - life / 90)
    if (life >= 90) {
      app.ticker.remove(tick)
      app.stage.removeChild(t)
      t.destroy()
    }
  }
  app.ticker.add(tick)
}

function rainDrops(n = 20) {
  for (let i = 0; i < n; i++) {
    const x = Math.random() * 240
    makeParticle(x, 0, (Math.random() - 0.5) * 0.3, 2 + Math.random() * 2,
      '#4488FF', 'drop', 60 + Math.random() * 60)
  }
}

function glowPulse(color) {
  if (!currentSprite) return
  let t = 0
  const tick = (delta) => {
    t += delta / 30
    currentSprite.alpha = 1 - Math.sin(t * Math.PI) * 0.25
    if (t >= 1) { app.ticker.remove(tick); if (currentSprite) currentSprite.alpha = 1 }
  }
  app.ticker.add(tick)
}

function blendColor(c1, c2, t) {
  const r1 = (c1 >> 16) & 0xFF, g1 = (c1 >> 8) & 0xFF, b1 = c1 & 0xFF
  const r2 = (c2 >> 16) & 0xFF, g2 = (c2 >> 8) & 0xFF, b2 = c2 & 0xFF
  const r = Math.round(r1 + (r2 - r1) * t)
  const g = Math.round(g1 + (g2 - g1) * t)
  const b = Math.round(b1 + (b2 - b1) * t)
  return parseInt(((r << 16) | (g << 8) | b).toString(16).padStart(6,'0'), 16)
}

function spawnAscendedAura() {
  if (Math.random() > 0.05) return
  const x = 80 + Math.random() * 80
  const y = 100 + Math.random() * 80
  const col = MOOD_COLOR[currentMood] || '#FFFFFF'
  makeParticle(x, y, (Math.random() - 0.5) * 0.3, -0.5 - Math.random(),
    col, 'star', 40 + Math.random() * 40)
}



function playEvolutionAnimation(newStage, cb) {
  burstStars(120, 160, 20)
  burstHearts(120, 160, 10)
  glowPulse(MOOD_COLOR[currentMood] || '#FFFFFF')
  floatText(120, 140, `→ ${STAGE_PREFIX[newStage]}`, '#FFFFFF')
  setTimeout(() => {
    currentStage = newStage
    enterAnimState('HAPPY_BOUNCE')
    if (cb) cb()
  }, 1500)
}



const view = app.view



function isOverPet(x, y) {
  return x >= 60 && x <= 180 && y >= 130 && y <= 310
}

view.addEventListener('mousemove', (e) => {
  const over = isOverPet(e.clientX, e.clientY)
  window.cw?.mouseMove(e.clientX, e.clientY, over)
})

let isMouseDown = false

view.addEventListener('pointerdown', (e) => {
  if (e.button === 2) return
  isMouseDown = true
  isDragging = false
  dragStartTime = Date.now()
  dragStartX = e.clientX
  dragStartY = e.clientY
  lastMouseX = e.clientX
  lastMouseY = e.clientY
  velX = 0; velY = 0

  longPressTimer = setTimeout(async () => {
    longPressTimer = null
    burstHearts(120, 160, 8)
    floatText(120, 130, '+trust', '#FF88AA')
    try { await window.cw?.pet() } catch {}
  }, 600)
})

view.addEventListener('pointermove', (e) => {
  if (!isMouseDown) return
  const dx = e.clientX - lastMouseX
  const dy = e.clientY - lastMouseY
  if (Math.abs(e.clientX - dragStartX) > 4 || Math.abs(e.clientY - dragStartY) > 4) {
    if (!isDragging) {
      isDragging = true
      if (longPressTimer) { clearTimeout(longPressTimer); longPressTimer = null }
    }
  }
  velX = dx
  velY = dy
  lastMouseX = e.clientX
  lastMouseY = e.clientY
  if (isDragging) {
    window.cw?.onPetDrag(e.screenX - 120, e.screenY - 200)
    const walkFrame = Math.floor(Date.now() / 150) % 3
    setSprite(currentMood, currentStage, walkFrame)
  }
})

view.addEventListener('pointerup', (e) => {
  isMouseDown = false
  if (longPressTimer) { clearTimeout(longPressTimer); longPressTimer = null }
  const duration = Date.now() - dragStartTime
  if (!isDragging && duration < 600) {
    window.cw?.toggleChat()
  }
  isDragging = false
})

window.addEventListener('mouseup', () => { isMouseDown = false; isDragging = false })

view.addEventListener('contextmenu', (e) => {
  e.preventDefault()
  
  window.cw?.feed('snack').then(() => {
    burstSparks(120, 160, '#44FF88', 6)
    floatText(120, 130, 'nom nom', '#44FF88')
  })
})



async function applyState(state) {
  if (!state || !state.pet) return
  const pet = state.pet
  const prevMood = currentMood
  const prevStage = currentStage

  currentMood = pet.current_mood || 'BORED'
  const newStage = pet.evolution_stage || 0

  if (newStage > prevStage) {
    playEvolutionAnimation(newStage)
  } else {
    currentStage = newStage
  }

  if (currentMood !== prevMood) {
    glowPulse(MOOD_COLOR[currentMood] || '#888888')
  }

  if (pet.is_sleeping) {
    enterAnimState('SLEEP')
  } else if (animState === 'SLEEP') {
    enterAnimState('IDLE')
  }
}


setInterval(async () => {
  try {
    const state = await window.cw?.getState()
    if (state) { currentState = state; await applyState(state) }
  } catch {}
}, 5000)


window.cw?.onAwarenessEvent((evt) => {
  if (!evt) return
  if (evt.message) showBubble(evt.message, currentMood, 240)
  if (evt.type === 'level_up') {
    burstStars(120, 160, 12)
    floatText(120, 120, `LEVEL UP!`, '#FFCC00')
    enterAnimState('HAPPY_BOUNCE')
  }
  if (evt.type === 'evolution') playEvolutionAnimation(evt.stage || currentStage + 1)
  if (evt.type === 'hunger_warning') rainDrops(15)
  if (evt.type === 'mood_change') glowPulse(MOOD_COLOR[evt.mood] || '#888888')
  if (evt.xp_gained) floatText(120, 100, `+${evt.xp_gained} XP`, '#00FFCC')
})


window.cw?.onStateUpdate((state) => {
  if (state) { currentState = state; applyState(state) }
})


;(async () => {
  try {
    await setSprite('NEUTRAL', 0, 0)
    const state = await window.cw?.getState()
    if (state) { currentState = state; await applyState(state) }
  } catch {}
  enterAnimState('IDLE')
})()

