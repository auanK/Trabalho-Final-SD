const { app, BrowserWindow, ipcMain } = require('electron'); 
const path = require('path');                
const net = require('net');                 

let authWindow; // instância Janela de login/registro
let mainWindow; // Instancia Janela principal após o login

// Configurações do Servidor
const SERVER_HOST = '127.0.0.1'; // Endereço IP do seu servidor Python
const SERVER_PORT = 8888;        // Porta em que o servidor Python está escutando
const socket = new net.Socket(); // Objeto cliente TCP para conectar ao server
let tcpBuffer = "";              // Buffer ara armazenar dados TCP recebidos

// Responsável por criar e configurar a janela de autenticação.
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
  // Carrega o arquivo HTML
  authWindow.loadFile('src/views/auth.html');
}

// Responsável por criar e configurar a janela principal (pós-login).
function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 800,
    height: 600,
    minWidth: 800,
    minHeight: 600,
    autoplayPolicy: 'no-user-gesture-required', // Permite tocar áudio automaticamente
    webPreferences: {
      preload: path.join(__dirname, 'preload.js')
    }
  });
  // Carrega o arquivo HTML
  mainWindow.loadFile('src/views/main.html');
}

// O Electron dispara o evento 'ready' quando ele terminou de inicializar.
app.whenReady().then(() => {

  // TENTA CONECTAR AO SERVIDOR DE SINALIZAÇÃO
  socket.connect(SERVER_PORT, SERVER_HOST, () => {
    console.log('Cliente Electron conectado ao servidor de sinalização.');
    // Depois de se conectar, cria a janela de login.
    createAuthWindow();
  });

  // O evento 'data' é disparado sempre que o servidor de sinalização envia alguma informação.
  socket.on('data', (data) => {
    tcpBuffer += data.toString('utf-8');
    let messages = tcpBuffer.split('\n');
    // A última parte pode ser uma mensagem incompleta, então ela é guardada de volta no buffer.
    tcpBuffer = messages.pop();

    for (const msg of messages) {
      if (!msg) continue;
      try {
        // Tenta converter a string json em um objeto js.
        const response = JSON.parse(msg);
        console.log(' - Servidor de sinalização -> Electron:', response, "\n");

        // O main.js atua como um ROTEADOR. Ele pega a mensagem do servidor de sinalização
        // e a REPASSA para a janela que estiver ABERTA no momento.
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send('from-server', response);
        }
        if (authWindow && !authWindow.isDestroyed()) {
          authWindow.webContents.send('from-server', response);
        }
      } catch (e) {
        console.error('Erro ao parsear JSON do servidor:', msg);
      }
    }
  });

  // Disparado se houver um erro na conexão TCP com o servidor
  socket.on('error', (err) => {
    console.error('Erro no Socket TCP:', err.message);
    if (authWindow) {
      authWindow.webContents.send('server-error', err.message);
    
    }
  });

  // Disparado quando a conexão TCP é fechada (pelo servidor ou pelo cliente).
  socket.on('close', () => {
    console.log('Conexão com o servidor de sinalização fechada.');
    // Se a janela principal estava aberta, fecha ela e volta para a tela de login.
    // Forçando o usuário a relogar se a conexão cair.
    if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.close();
        createAuthWindow();
    }
  });
});

// ipcMain.on(canal, callback) escuta por mensagens enviadas pelas janelas
ipcMain.on('login-success', () => {
  // auth.html -> preload.js -> Main.js 
  console.log(" - Recebido 'login-success' do auth.html \n");

  if (authWindow) {
    authWindow.close();
    authWindow = null; 
  }
  createMainWindow();
});

// Este ouvinte recebe QUALQUER comando que as janelas queiram enviar para o servidor de sinalização
ipcMain.on('to-server', (event, data) => {
  // pagina -> preload.js -> Main.js -> servidor de sinalização

  try {
    const msg = JSON.stringify(data) + '\n';
    console.log(' - Electron -> Servidor de sinalização:', msg.trim(), "\n");
    socket.write(msg);
  } catch (e) {
    console.error('Falha ao enviar dados para o servidor:', e);
  }
});

// Escuta pela mensagem enviada pelo botão Logout.
ipcMain.on('quit-app', () => {
  console.log("Recebido 'quit-app', encerrando a aplicação...");
  app.quit();
});

// Evento padrão do Electron para fechar o app quando todas as janelas são fechadas
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});