const { app, BrowserWindow, ipcMain, Tray, Menu, nativeImage, Notification, screen } = require('electron')
const { spawn } = require('child_process')
const path = require('path')
const http = require('http')

let petWindow, hudWindow, chatWindow, tray
let pythonProcess = null
const BACKEND_PORT = 7432
const fs = require('fs')
const crashFlagPath = path.join(app.getPath('userData'), 'crash_flag')
const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`

function startPython() {
  const pythonCmd = path.join(__dirname, 'venv', 'Scripts', 'python.exe')
  const backendPath = path.join(__dirname, 'backend', 'main.py')
  pythonProcess = spawn(pythonCmd, [backendPath], {
    cwd: path.join(__dirname, 'backend'),
    stdio: ['ignore', 'pipe', 'pipe'],
  })
  pythonProcess.stdout.on('data', (d) => console.log('[PY]', d.toString().trim()))
  pythonProcess.stderr.on('data', (d) => console.error('[PY ERR]', d.toString().trim()))
  pythonProcess.on('exit', (code) => {
    console.log(`[PY] exited code ${code}`)
    if (code !== 0) {
      const hasCrashFlag = fs.existsSync(crashFlagPath)
      if (!hasCrashFlag) {
        try { fs.writeFileSync(crashFlagPath, Date.now().toString()) } catch {}
        setTimeout(startPython, 2000)
      } else {
        new Notification({ title: 'CodeWaifu Error', body: 'Backend crashed.' }).show()
      }
    } else {
      try { if (fs.existsSync(crashFlagPath)) fs.unlinkSync(crashFlagPath) } catch {}
    }
  })
}

function pollBackend(retries = 60) {
  return new Promise((resolve, reject) => {
    let attempts = 0
    const check = () => {
      http.get(`${BACKEND_URL}/health`, (res) => {
        if (res.statusCode === 200) resolve()
        else retry()
      }).on('error', () => retry())
    }
    const retry = () => {
      attempts++
      if (attempts >= retries) reject(new Error('Backend did not start in time'))
      else setTimeout(check, 2000)
    }
    check()
  })
}

function createWindows() {
  const { width, height } = screen.getPrimaryDisplay().workAreaSize

  petWindow = new BrowserWindow({
    width: 240,
    height: 320,
    x: width - 260,
    y: height - 340,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    hasShadow: false,
    skipTaskbar: true,
    resizable: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  })
  petWindow.setAlwaysOnTop(true, 'screen-saver')
  
  petWindow.setIgnoreMouseEvents(false)
  petWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'))

  hudWindow = new BrowserWindow({
    width: 300,
    height: 120,
    x: width - 316,
    y: 8,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    hasShadow: false,
    skipTaskbar: true,
    resizable: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  })
  hudWindow.setAlwaysOnTop(true, 'screen-saver')
  hudWindow.setIgnoreMouseEvents(true, { forward: true })
  hudWindow.loadFile(path.join(__dirname, 'renderer', 'hud.html'))

  chatWindow = new BrowserWindow({
    width: 380,
    height: 520,
    show: false,
    frame: true,
    resizable: false,
    title: 'CodeWaifu',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  })
  chatWindow.loadFile(path.join(__dirname, 'renderer', 'chat.html'))
  chatWindow.on('close', (e) => {
    e.preventDefault()
    chatWindow.hide()
  })
}

function updateTrayMood(mood) {
  if (!tray) return
  const MOOD_COLORS = {
    HAPPY: [255,204,0], BORED: [136,136,136], DANGEROUS: [255,68,0],
    COLD: [0,255,255], UNHINGED: [204,0,255], WORRIED: [170,136,255],
    DOMINANT: [255,34,51], IMPRESSED: [68,255,136], SOFT: [255,68,255],
    OBSESSED: [255,68,204], DISGUSTED: [170,170,0], FOCUSED: [0,255,238],
    NEUTRAL: [170,170,170],
  }
  const [r,g,b] = MOOD_COLORS[mood] || [136,136,136]
  const size = 16
  const buf = Buffer.alloc(size * size * 4)
  const cx = size/2, cy = size/2, rad = size/2 - 1
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const dx = x - cx, dy = y - cy
      const inside = dx*dx + dy*dy <= rad*rad
      const i = (y * size + x) * 4
      buf[i]   = inside ? r : 0
      buf[i+1] = inside ? g : 0
      buf[i+2] = inside ? b : 0
      buf[i+3] = inside ? 255 : 0
    }
  }
  try {
    const icon = nativeImage.createFromBuffer(buf, { width: size, height: size })
    tray.setImage(icon)
  } catch {}
}

function createTray() {
  const iconPath = path.join(__dirname, 'assets', 'icon.png')
  let icon
  try {
    icon = nativeImage.createFromPath(iconPath)
    if (icon.isEmpty()) icon = nativeImage.createEmpty()
  } catch {
    icon = nativeImage.createEmpty()
  }
  tray = new Tray(icon)
  tray.setToolTip('CodeWaifu V2')
  const menu = Menu.buildFromTemplate([
    { label: 'Show/Hide Pet', click: () => petWindow.isVisible() ? petWindow.hide() : petWindow.show() },
    { label: 'Feed', click: () => makeRequest('POST', '/feed', { food_type: 'snack' }) },
    { label: 'Open Chat', click: () => chatWindow.show() },
    { type: 'separator' },
    { label: 'Quit', click: () => { app.isQuitting = true; app.quit() } },
    { type: 'separator' },
    { label: 'Start on Login', type: 'checkbox', checked: app.getLoginItemSettings().openAtLogin,
      click: (item) => app.setLoginItemSettings({ openAtLogin: item.checked }) },
  ])
  tray.setContextMenu(menu)
}

function setupIPC() {
  ipcMain.on('toggle-chat', () => {
    chatWindow.isVisible() ? chatWindow.hide() : chatWindow.show()
  })

  
  ipcMain.on('mouse-move', (_, { x, y, overPet }) => {
    if (petWindow) petWindow.setIgnoreMouseEvents(!overPet, { forward: true })
  })

  ipcMain.on('set-ignore-mouse', (_, ignore) => {
    if (petWindow) petWindow.setIgnoreMouseEvents(ignore, { forward: true })
  })

  ipcMain.on('pet-dragged', (_, { x, y }) => {
    if (petWindow) petWindow.setPosition(Math.round(x), Math.round(y))
  })

  ipcMain.handle('get-state', async () => makeRequest('GET', '/state'))

  ipcMain.handle('chat', async (_, msg) => {
    const result = await makeRequest('POST', '/chat', { message: msg })
    if (result && result.reply) {
      if (petWindow) petWindow.webContents.send('awareness-event', {
        type: 'chat_reply', message: result.reply, mood: result.mood,
      })
    }
    return result
  })

  ipcMain.handle('feed', async (_, foodType) => makeRequest('POST', '/feed', { food_type: foodType || 'snack' }))
  ipcMain.handle('pet-action', async () => makeRequest('POST', '/pet'))
  ipcMain.handle('get-skills', async () => makeRequest('GET', '/skills'))
  ipcMain.handle('teach-skill', async (_, skillId) => makeRequest('POST', '/skills/teach', { skill_id: skillId }))
}

function makeRequest(method, endpoint, body) {
  return new Promise((resolve, reject) => {
    const data = body ? JSON.stringify(body) : null
    const opts = {
      hostname: '127.0.0.1', port: BACKEND_PORT, path: endpoint, method,
      headers: { 'Content-Type': 'application/json', ...(data ? { 'Content-Length': Buffer.byteLength(data) } : {}) },
    }
    const req = http.request(opts, (res) => {
      let raw = ''
      res.on('data', (c) => raw += c)
      res.on('end', () => { try { resolve(JSON.parse(raw)) } catch { resolve({ error: 'parse_error', raw }) } })
    })
    req.on('error', reject)
    req.setTimeout(20000, () => { req.destroy(); reject(new Error('timeout')) })
    if (data) req.write(data)
    req.end()
  })
}

function startSSERelay() {
  const relay = () => {
    http.get(`${BACKEND_URL}/events`, (res) => {
      res.on('data', (chunk) => {
        const lines = chunk.toString().split('\n')
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const evt = JSON.parse(line.slice(6))
              if (petWindow) petWindow.webContents.send('awareness-event', evt)
              if (hudWindow) hudWindow.webContents.send('awareness-event', evt)
              if (chatWindow) chatWindow.webContents.send('awareness-event', evt)
            } catch {}
          }
        }
      })
      res.on('end', () => setTimeout(relay, 1000))
      res.on('error', () => setTimeout(relay, 3000))
    }).on('error', () => setTimeout(relay, 3000))
  }
  relay()
}

function startStateBroadcast() {
  setInterval(async () => {
    try {
      const state = await makeRequest('GET', '/state')
      if (petWindow) petWindow.webContents.send('state-update', state)
      if (hudWindow) hudWindow.webContents.send('state-update', state)
      if (state && state.pet && state.pet.current_mood) updateTrayMood(state.pet.current_mood)
      if (chatWindow && chatWindow.isVisible()) chatWindow.webContents.send('state-update', state)
    } catch {}
  }, 3000)
}

app.whenReady().then(async () => {
  startPython()
  try {
    await pollBackend(60)
    console.log('[MAIN] backend ready')
  } catch (e) {
    console.error('[MAIN] backend failed to start:', e.message)
  }
  createWindows()
  createTray()
  setupIPC()
  startSSERelay()
  startStateBroadcast()
})

app.on('window-all-closed', (e) => e.preventDefault())
app.on('before-quit', () => {
  if (pythonProcess) { pythonProcess.kill('SIGTERM'); pythonProcess = null }
})

