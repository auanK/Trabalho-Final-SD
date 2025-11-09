const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const fs = require('fs');
const xmlrpc = require('xmlrpc'); // Cliente XML-RPC

let authWindow;
let mainWindow;

let SERVER_HOST;
let SERVER_PORT;
let rmiClient;

let userRequestedQuit = false; // Adicionada flag

function createAuthWindow() {
    if (authWindow) return;
    authWindow = new BrowserWindow({
        width: 400, height: 600, minWidth: 400, minHeight: 600, maxWidth: 400, maxHeight: 600,
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            nodeIntegration: false,
            contextIsolation: true,
            sandbox: false
        }
    });
    authWindow.loadFile('src/views/auth.html');
    authWindow.on('closed', () => { authWindow = null; });
}
function createMainWindow() {
    if (mainWindow) return;
    mainWindow = new BrowserWindow({
        width: 800, height: 600, minWidth: 800, minHeight: 600,
        autoplayPolicy: 'no-user-gesture-required',
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            nodeIntegration: false,
            contextIsolation: true,
            sandbox: false
        }
    });
    mainWindow.maximize();
    mainWindow.loadFile('src/views/main.html');
    mainWindow.on('closed', () => { mainWindow = null; });
}

// --- Lógica de Inicialização ---
app.whenReady().then(() => {
    let configPath;
    if (app.isPackaged) {
        configPath = path.join(process.resourcesPath, 'config.json');
    } else {
        configPath = path.join(app.getAppPath(), 'config.json');
    }
    try {
        const configData = fs.readFileSync(configPath, 'utf8');
        const config = JSON.parse(configData);
        SERVER_HOST = config.server_host || '127.0.0.1';
        SERVER_PORT = config.server_port || 8888;
    } catch (err) {
        console.error('Erro ao ler config.json, usando padrão.', err.message);
        SERVER_HOST = '127.0.0.1';
        SERVER_PORT = 8888;
    }
    
    // Criar o cliente RMI
    const rmiUrl = `http://${SERVER_HOST}:${SERVER_PORT}`;
    console.log(`[RMI] Configurando cliente para ${rmiUrl}`);
    rmiClient = xmlrpc.createClient({ url: rmiUrl });

    // Inicia a janela de autenticação
    createAuthWindow();

    // Lógica 'activate'
    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createAuthWindow();
        }
    });
});


ipcMain.on('login-success', () => {
    if (authWindow) { authWindow.close(); authWindow = null; }
    createMainWindow();
});

// Handler de Chamadas RMI
ipcMain.handle('rmi-call', async (event, { method, params }) => {
    console.log(`[RMI] -> Chamando: ${method} com params:`, params);
    
    return new Promise((resolve, reject) => {
        rmiClient.methodCall(method, params, (error, value) => {
            if (error) {
                console.error(`[RMI] <- Erro em ${method}:`, error.message);
                reject(error); 
            } else {
                console.log(`[RMI] <- Resposta de ${method}:`, value);
                resolve(value); 
            }
        });
    });
});

ipcMain.on('quit-app', () => {
    console.log("Recebido 'quit-app', encerrando a aplicação...");
    userRequestedQuit = true;
    app.quit();
});

// --- Lógica de Encerramento ---

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

// Lógica 'before-quit' para logout RMI
app.on('before-quit', async (event) => {
    if (!userRequestedQuit) {
        console.log("Encerramento não iniciado pelo 'quit-app' detectado.");
    }
    
    console.log("Tentando notificar o servidor sobre o logout antes de sair...");
    event.preventDefault(); 
    
    try {
        console.log("Fechando sem notificar o servidor (lógica de token está no renderer).");
        
    } catch (e) {
        console.warn("Erro ao tentar fazer logout RMI:", e.message);
    } finally {
        userRequestedQuit = true; 
        app.quit();
    }
});