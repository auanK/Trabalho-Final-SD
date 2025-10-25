const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');

let authWindow;
let mainWindow;

function createAuthWindow() {
  authWindow = new BrowserWindow({
    width: 400,
    height: 600,
    minWidth: 400,
    minHeight: 600,
    maxWidth: 400,
    maxHeight: 600,

    webPreferences: {
      preload: path.join(__dirname, 'preload.js')
    }

  });

  authWindow.loadFile('src/views/auth.html');
}

function createMainWindow() {

  mainWindow = new BrowserWindow({
    width: 800,
    height: 600,

    minWidth: 800,
    minHeight: 600,

    autoplayPolicy: 'no-user-gesture-required',
    
    webPreferences: {
      preload: path.join(__dirname, 'preload.js')
    }
  });

  mainWindow.maximize();

  mainWindow.loadFile('src/views/main.html');
}

app.whenReady().then(() => {
  createAuthWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createAuthWindow();
    }
  });
});

// Evento de login bem-sucedido
ipcMain.on('login-success', () => {
  if (authWindow) {
    authWindow.close();
  }
  createMainWindow();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
