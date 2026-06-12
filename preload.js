const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('cw', {
  getState:        ()          => ipcRenderer.invoke('get-state'),
  chat:            (msg)       => ipcRenderer.invoke('chat', msg),
  feed:            (foodType)  => ipcRenderer.invoke('feed', foodType),
  pet:             ()          => ipcRenderer.invoke('pet-action'),
  getSkills:       ()          => ipcRenderer.invoke('get-skills'),
  teachSkill:      (skillId)   => ipcRenderer.invoke('teach-skill', skillId),
  toggleChat:      ()          => ipcRenderer.send('toggle-chat'),
  setIgnoreMouse:  (ignore)    => ipcRenderer.send('set-ignore-mouse', ignore),
  onPetDrag:       (x, y)     => ipcRenderer.send('pet-dragged', { x, y }),
  mouseMove:       (x, y, overPet) => ipcRenderer.send('mouse-move', { x, y, overPet }),
  onStateUpdate:   (cb)        => ipcRenderer.on('state-update', (_, data) => cb(data)),
  onAwarenessEvent:(cb)        => ipcRenderer.on('awareness-event', (_, data) => cb(data)),
})
