const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
    checkHealth: () => ipcRenderer.invoke('check-health'),
    restartServices: () => ipcRenderer.invoke('restart-services'),
});
