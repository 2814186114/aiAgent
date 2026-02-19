const { app, BrowserWindow, dialog, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

const isDev = !app.isPackaged;

if (isDev) {
    app.setPath('userData', path.join(__dirname, 'electron-data'));
}

let mainWindow = null;
let nodeServerProcess = null;
let pythonProcess = null;

const NODE_PORT = 3001;
const PYTHON_PORT = 8000;

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1200,
        height: 800,
        minWidth: 800,
        minHeight: 600,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js'),
        },
        title: 'Academic Assistant Agent',
        show: false,
    });

    mainWindow.once('ready-to-show', () => {
        mainWindow.show();
    });

    if (isDev) {
        mainWindow.loadURL('http://localhost:5173');
        mainWindow.webContents.openDevTools();
    } else {
        mainWindow.loadFile(path.join(__dirname, 'dist', 'index.html'));
    }

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

function spawnProcess(command, args, name, cwd = __dirname) {
    return new Promise((resolve, reject) => {
        const isWindows = process.platform === 'win32';
        const shell = isWindows ? true : false;

        const proc = spawn(command, args, {
            cwd,
            shell,
            env: { ...process.env },
        });

        let hasResolved = false;

        proc.stdout.on('data', (data) => {
            console.log(`[${name}] ${data.toString().trim()}`);
            if (!hasResolved) {
                hasResolved = true;
                resolve(proc);
            }
        });

        proc.stderr.on('data', (data) => {
            console.error(`[${name} ERROR] ${data.toString().trim()}`);
        });

        proc.on('error', (err) => {
            console.error(`[${name}] Failed to start: ${err.message}`);
            if (!hasResolved) {
                reject(err);
            }
        });

        proc.on('close', (code) => {
            console.log(`[${name}] Process exited with code ${code}`);
        });

        setTimeout(() => {
            if (!hasResolved) {
                hasResolved = true;
                resolve(proc);
            }
        }, 3000);
    });
}

async function startServices() {
    const errors = [];

    try {
        console.log('Starting Node.js server...');
        nodeServerProcess = await spawnProcess('node', ['server.js'], 'NodeServer');
        console.log('Node.js server started successfully');
    } catch (err) {
        errors.push(`Node.js server failed to start: ${err.message}`);
    }

    try {
        console.log('Starting Python FastAPI server...');
        const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
        pythonProcess = await spawnProcess(
            pythonCmd,
            ['-m', 'uvicorn', 'main:app', '--host', '0.0.0.0', '--port', PYTHON_PORT.toString()],
            'PythonServer'
        );
        console.log('Python server started successfully');
    } catch (err) {
        errors.push(`Python server failed to start: ${err.message}`);
    }

    return errors;
}

function stopServices() {
    if (nodeServerProcess) {
        nodeServerProcess.kill();
        nodeServerProcess = null;
    }
    if (pythonProcess) {
        pythonProcess.kill();
        pythonProcess = null;
    }
}

async function checkServicesHealth() {
    const http = require('http');

    const checkHealth = (port, name) => {
        return new Promise((resolve) => {
            const req = http.get(`http://localhost:${port}/health`, (res) => {
                resolve({ name, status: res.statusCode === 200 ? 'healthy' : 'unhealthy' });
            });
            req.on('error', () => {
                resolve({ name, status: 'unhealthy' });
            });
            req.setTimeout(2000, () => {
                req.destroy();
                resolve({ name, status: 'timeout' });
            });
        });
    };

    const nodeHealth = await checkHealth(NODE_PORT, 'Node.js');

    const pythonHealth = await new Promise((resolve) => {
        const req = http.get(`http://localhost:${PYTHON_PORT}/ping`, (res) => {
            resolve({ name: 'Python', status: res.statusCode === 200 ? 'healthy' : 'unhealthy' });
        });
        req.on('error', () => {
            resolve({ name: 'Python', status: 'unhealthy' });
        });
        req.setTimeout(2000, () => {
            req.destroy();
            resolve({ name: 'Python', status: 'timeout' });
        });
    });

    return [nodeHealth, pythonHealth];
}

app.whenReady().then(async () => {
    if (!isDev) {
        const errors = await startServices();
        if (errors.length > 0) {
            dialog.showErrorBox('Service Startup Error', errors.join('\n'));
        }
    }

    createWindow();

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

app.on('window-all-closed', () => {
    stopServices();
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('before-quit', () => {
    stopServices();
});

ipcMain.handle('check-health', async () => {
    return await checkServicesHealth();
});

ipcMain.handle('restart-services', async () => {
    stopServices();
    await new Promise(resolve => setTimeout(resolve, 1000));
    return await startServices();
});
