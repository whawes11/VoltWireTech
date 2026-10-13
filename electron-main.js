const { app, BrowserWindow } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow;
let serverProcess;

function startBackend() {
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
  serverProcess = spawn(pythonCmd, ['server.py'], {
    cwd: __dirname,
    env: { ...process.env, PORT: '8080' }
  });

  serverProcess.stdout.on('data', (data) => {
    console.log(`Server: ${data}`);
  });

  serverProcess.stderr.on('data', (data) => {
    console.error(`Server error: ${data}`);
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 850,
    minWidth: 900,
    minHeight: 650,
    title: 'VoltWire - Low Voltage Field Service Dispatch',
    backgroundColor: '#000000',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  // Wait 1.5 seconds for python server to start, then load
  setTimeout(() => {
    mainWindow.loadURL('http://127.0.0.1:8080');
  }, 1500);

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(() => {
  startBackend();
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (serverProcess) {
    serverProcess.kill();
  }
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
