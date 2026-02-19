/// <reference types="vite/client" />

interface ElectronAPI {
    checkHealth: () => Promise<Array<{ name: string; status: string }>>
    restartServices: () => Promise<string[]>
}

declare global {
    interface Window {
        electronAPI?: ElectronAPI
    }
}

export { }
