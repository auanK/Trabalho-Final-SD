const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const net = require('net');
const fs = require('fs');

let authWindow;
let mainWindow;

let SERVER_HOST;
let SERVER_PORT;

let userRequestedQuit = false;
const client = new net.Socket();
let tcpBuffer = Buffer.alloc(0);

// Mapeamento de códigos de comando
const CommandCode = {
    REGISTER: 0x01, LOGIN: 0x02, GET_INITIAL_DATA: 0x03, SEARCH_USER: 0x04,
    ADD_FRIEND: 0x05, ACCEPT_FRIEND: 0x06, REJECT_FRIEND: 0x07, INVITE: 0x10,
    ACCEPT: 0x11, REJECT: 0x12, BYE: 0x13,
    REGISTER_RESPONSE: 0x81, LOGIN_RESPONSE: 0x82, FRIEND_LIST: 0x83,
    PENDING_FRIEND_REQUESTS: 0x84, SEARCH_RESPONSE: 0x85, ADD_FRIEND_RESPONSE: 0x86,
    INCOMING_FRIEND_REQUEST: 0x87, FRIEND_REQUEST_ACCEPTED: 0x88, INVITE_RESPONSE: 0x90,
    INCOMING_CALL: 0x91, CALL_ACCEPTED: 0x92, CALL_REJECTED: 0x93,
    CALL_ENDED: 0x94, STATUS_UPDATE: 0xA0, ERROR: 0xFF
};
const CODE_TO_COMMAND_NAME = Object.fromEntries(Object.entries(CommandCode).map(([k, v]) => [v, k]));

function serializeString(str) {
    const strBuffer = Buffer.from(str || '', 'utf-8');
    const lenBuffer = Buffer.alloc(2);
    lenBuffer.writeUInt16BE(strBuffer.length, 0);
    return Buffer.concat([lenBuffer, strBuffer]);
}

function deserializeString(buffer, offset = 0) {
    if (buffer.length < offset + 2) throw new Error("Buffer insuficiente (tam str)");
    const strLen = buffer.readUInt16BE(offset);
    const dataOffset = offset + 2;
    const endOffset = dataOffset + strLen;
    if (buffer.length < endOffset) throw new Error(`Buffer insuficiente (str data ${strLen} bytes)`);
    const str = buffer.toString('utf-8', dataOffset, endOffset);
    return { value: str, nextOffset: endOffset };
}

function serializeBool(boolVal) {
    const buf = Buffer.alloc(1);
    buf.writeUInt8(boolVal ? 1 : 0, 0);
    return buf;
}

function deserializeBool(buffer, offset = 0) {
    if (buffer.length < offset + 1) throw new Error("Buffer insuficiente (bool)");
    const val = buffer.readUInt8(offset);
    return { value: val !== 0, nextOffset: offset + 1 };
}

function serializeUInt16BE(num) {
    const buf = Buffer.alloc(2);
    buf.writeUInt16BE(num || 0, 0);
    return buf;
}

function deserializeUInt16BE(buffer, offset = 0) {
    if (buffer.length < offset + 2) throw new Error("Buffer insuficiente (UInt16)");
    const val = buffer.readUInt16BE(offset);
    return { value: val, nextOffset: offset + 2 };
}

function serializePayload(commandCode, payload) {
    const buffers = [];
    try {
        if (commandCode === CommandCode.REGISTER || commandCode === CommandCode.LOGIN) {
            buffers.push(serializeString(payload.nickname));
            buffers.push(serializeString(payload.password));
            if (commandCode === CommandCode.REGISTER) {
                buffers.push(serializeString(payload.name));
            }
        } else if (commandCode === CommandCode.GET_INITIAL_DATA || commandCode === CommandCode.BYE) {
        } else if (commandCode === CommandCode.SEARCH_USER) {
            buffers.push(serializeString(payload.nickname_query));
        } else if (commandCode === CommandCode.ADD_FRIEND) {
            buffers.push(serializeString(payload.target_nickname));
        } else if (commandCode === CommandCode.ACCEPT_FRIEND || commandCode === CommandCode.REJECT_FRIEND) {
            buffers.push(serializeString(payload.requester_nickname));
        } else if (commandCode === CommandCode.INVITE) {
            buffers.push(serializeString(payload.target_nickname));
        } else if (commandCode === CommandCode.ACCEPT || commandCode === CommandCode.REJECT) {
            buffers.push(serializeString(payload.caller_nickname));
        }
        else if (commandCode === CommandCode.REGISTER_RESPONSE || commandCode === CommandCode.LOGIN_RESPONSE ||
            commandCode === CommandCode.ADD_FRIEND_RESPONSE || commandCode === CommandCode.INVITE_RESPONSE ||
            commandCode === CommandCode.ERROR) {
            buffers.push(serializeBool(payload.success));
            buffers.push(serializeString(payload.message));
            if (commandCode === CommandCode.LOGIN_RESPONSE && payload.success) {
                buffers.push(serializeString(payload.nickname));
            }
        } else if (commandCode === CommandCode.FRIEND_LIST) {
            const friends = payload.friends || [];
            buffers.push(serializeUInt16BE(friends.length));
            friends.forEach(f => {
                buffers.push(serializeString(f.nickname));
                buffers.push(serializeString(f.status));
            });
        }
        else {
            console.warn(`Serialização manual não implementada para ${CODE_TO_COMMAND_NAME[commandCode]}, enviando payload vazio.`);
            return Buffer.alloc(0);
        }
        return Buffer.concat(buffers);
    } catch (e) {
        console.error(`Erro ao serializar payload para ${CODE_TO_COMMAND_NAME[commandCode]}:`, e);
        return Buffer.alloc(0);
    }
}

function deserializePayload(commandCode, payloadBuffer) {
    let offset = 0;
    const payload = {};
    try {
        if (commandCode === CommandCode.REGISTER_RESPONSE || commandCode === CommandCode.LOGIN_RESPONSE ||
            commandCode === CommandCode.ADD_FRIEND_RESPONSE || commandCode === CommandCode.INVITE_RESPONSE ||
            commandCode === CommandCode.ERROR) 
            {
            let result = deserializeBool(payloadBuffer, offset); payload.success = result.value; offset = result.nextOffset;
            result = deserializeString(payloadBuffer, offset); payload.message = result.value; offset = result.nextOffset;
            if (commandCode === CommandCode.LOGIN_RESPONSE && payload.success) {
                result = deserializeString(payloadBuffer, offset); payload.nickname = result.value; offset = result.nextOffset;
            }
        }
        else if (commandCode === CommandCode.FRIEND_LIST) {
            let result = deserializeUInt16BE(payloadBuffer, offset); const count = result.value; offset = result.nextOffset;
            payload.friends = [];
            for (let i = 0; i < count; i++) {
                let nickRes = deserializeString(payloadBuffer, offset); offset = nickRes.nextOffset;
                let statusRes = deserializeString(payloadBuffer, offset); offset = statusRes.nextOffset;
                payload.friends.push({ nickname: nickRes.value, status: statusRes.value });
            }
        }
        else if (commandCode === CommandCode.PENDING_FRIEND_REQUESTS) {
            let result = deserializeUInt16BE(payloadBuffer, offset); const count = result.value; offset = result.nextOffset;
            payload.requests_from = [];
            for (let i = 0; i < count; i++) {
                let nickRes = deserializeString(payloadBuffer, offset); offset = nickRes.nextOffset;
                payload.requests_from.push(nickRes.value);
            }
        }
        else if (commandCode === CommandCode.SEARCH_RESPONSE) {
            let result = deserializeBool(payloadBuffer, offset); payload.success = result.value; offset = result.nextOffset;
            result = deserializeUInt16BE(payloadBuffer, offset); const count = result.value; offset = result.nextOffset;
            payload.results = [];
            for (let i = 0; i < count; i++) {
                let nickRes = deserializeString(payloadBuffer, offset); offset = nickRes.nextOffset;
                let nameRes = deserializeString(payloadBuffer, offset); offset = nameRes.nextOffset;
                payload.results.push({ nickname: nickRes.value, name: nameRes.value });
            }
        }
        else if (commandCode === CommandCode.INCOMING_FRIEND_REQUEST) {
            let result = deserializeString(payloadBuffer, offset); payload.from_nickname = result.value; offset = result.nextOffset;
        }
        else if (commandCode === CommandCode.FRIEND_REQUEST_ACCEPTED) {
            let result = deserializeString(payloadBuffer, offset); payload.by_nickname = result.value; offset = result.nextOffset;
            result = deserializeString(payloadBuffer, offset); payload.status = result.value; offset = result.nextOffset;
        }
        else if (commandCode === CommandCode.INCOMING_CALL) {
            let result = deserializeString(payloadBuffer, offset); payload.from_nickname = result.value; offset = result.nextOffset;
        }
        else if (commandCode === CommandCode.CALL_ACCEPTED) {
            let result = deserializeString(payloadBuffer, offset); payload.callee_nickname = result.value; offset = result.nextOffset;
            result = deserializeString(payloadBuffer, offset); payload.relay_ip = result.value; offset = result.nextOffset;
            result = deserializeUInt16BE(payloadBuffer, offset); payload.relay_port = result.value; offset = result.nextOffset;
            result = deserializeString(payloadBuffer, offset); payload.token = result.value; offset = result.nextOffset;
        }
        else if (commandCode === CommandCode.CALL_REJECTED) {
            let result = deserializeString(payloadBuffer, offset); payload.callee_nickname = result.value; offset = result.nextOffset;
        }
        else if (commandCode === CommandCode.CALL_ENDED) {
            let result = deserializeString(payloadBuffer, offset); payload.from_nickname = result.value; offset = result.nextOffset;
        }
        else if (commandCode === CommandCode.STATUS_UPDATE) {
            let result = deserializeString(payloadBuffer, offset); payload.nickname = result.value; offset = result.nextOffset;
            result = deserializeString(payloadBuffer, offset); payload.status = result.value; offset = result.nextOffset;
        }
        else if (commandCode === CommandCode.REGISTER || commandCode === CommandCode.LOGIN ||
            commandCode === CommandCode.GET_INITIAL_DATA || commandCode === CommandCode.SEARCH_USER ||
            commandCode === CommandCode.ADD_FRIEND || commandCode === CommandCode.ACCEPT_FRIEND ||
            commandCode === CommandCode.REJECT_FRIEND || commandCode === CommandCode.INVITE ||
            commandCode === CommandCode.ACCEPT || commandCode === CommandCode.REJECT ||
            commandCode === CommandCode.BYE) 
            { }
        else { throw new Error(`Desserialização não implementada para ${CODE_TO_COMMAND_NAME[commandCode]}`); }

        if (offset !== payloadBuffer.length) {
            console.warn(`Bytes extras (${payloadBuffer.length - offset}) no payload para ${CODE_TO_COMMAND_NAME[commandCode]}`);
        }
        return payload;

    } catch (e) {
        const cmdName = CODE_TO_COMMAND_NAME[commandCode] || `UNKNOWN(0x${commandCode.toString(16)})`;
        let dataPreview = payloadBuffer.length > 50 ? payloadBuffer.subarray(0, 50).toString('hex') + '...' : payloadBuffer.toString('hex');
        console.error(`Erro ao desserializar payload BINÁRIO para comando ${cmdName}:`, e.message, `- Buffer (hex): ${dataPreview}`);
        return { error: `Falha na desserialização do payload binário: ${e.message}` };
    }
}

// Cria mensagem binária completa (cabeçalho + payload)
function createBinaryMessage(commandCode, payload) {
    const payloadBuffer = serializePayload(commandCode, payload);
    const headerBuffer = Buffer.alloc(3);
    headerBuffer.writeUInt8(commandCode, 0);
    headerBuffer.writeUInt16BE(payloadBuffer.length, 1);
    return Buffer.concat([headerBuffer, payloadBuffer]);
}


// Criação das janelas Auth e Main
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


// Quando o app estiver pronto, conectar ao servidor, cria a janela de autenticação e lida dados do servidor
app.whenReady().then(() => {
    let configPath;

    if (app.isPackaged) {
        configPath = path.join(process.resourcesPath, 'config.json');
    } else {
        configPath = path.join(app.getAppPath(), 'config.json');
    }

    try {
        console.log(`Modo: ${app.isPackaged ? 'Produção' : 'Desenvolvimento'}`);
        console.log(`Lendo configuração do arquivo: ${configPath}`);

        const configData = fs.readFileSync(configPath, 'utf8');
        const config = JSON.parse(configData);

        SERVER_HOST = config.server_host || '127.0.0.1';
        SERVER_PORT = config.server_port || 8888;

        console.log(`configurado para: ${SERVER_HOST}:${SERVER_PORT}`);
    } catch (err) {
        console.error('Erro ao ler o arquivo de configuração:', err.message);
        console.error('Usando valores padrão: 127.0.0.1:8888');

        SERVER_HOST = '127.0.0.1';
        SERVER_PORT = 8888;
    }

    console.log('Tentando conectar ao servidor Python...');
    client.connect(SERVER_PORT, SERVER_HOST, () => {
        console.log('[DEBUG] Dentro do callback de client.connect!');
        console.log('Cliente Electron conectado ao servidor Python.');
        createAuthWindow();
    });

    // Recebendo dados do Servidor
    client.on('data', (data) => {
        tcpBuffer = Buffer.concat([tcpBuffer, data]);
        while (true) {
            if (tcpBuffer.length < 3) break;
            const commandCode = tcpBuffer.readUInt8(0);
            const payloadLength = tcpBuffer.readUInt16BE(1);
            const totalMessageLength = 3 + payloadLength;
            if (tcpBuffer.length < totalMessageLength) break;
            const payloadBuffer = tcpBuffer.subarray(3, totalMessageLength);
            tcpBuffer = tcpBuffer.subarray(totalMessageLength);
            try {
                const payload = deserializePayload(commandCode, payloadBuffer);
                const commandName = CODE_TO_COMMAND_NAME[commandCode] || `UNKNOWN(0x${commandCode.toString(16)})`;
                console.log(`Servidor de sinalização -> Electron: Cmd=${commandName}, Payload=`, payload);
                const response = { command: commandName, payload: payload };
                const activeWindow = (mainWindow && !mainWindow.isDestroyed()) ? mainWindow :
                    (authWindow && !authWindow.isDestroyed()) ? authWindow : null;

                // Enviando dados desserializados para a janela ativa                     
                if (activeWindow) {
                    activeWindow.webContents.send('from-server', response);
                } else {
                    console.warn("Dados recebidos sem janela ativa.");
                }
            } catch (e) {
                console.error('Erro ao desserializar/encaminhar:', e);
            }
        }
    });

    // Tratamento de erros de conexão
    client.on('error', (err) => {
        console.error('Erro no Socket TCP:', err.message);
        const activeWindow = (mainWindow && !mainWindow.isDestroyed()) ? mainWindow :
            (authWindow && !authWindow.isDestroyed()) ? authWindow : null;
        if (activeWindow) {
            activeWindow.webContents.send('server-error', `Erro de Conexão: ${err.message}`);
        }
        if (mainWindow) mainWindow.close();
        if (!authWindow) createAuthWindow();
    });

    // Tratamento de fechamento da conexão
    client.on('close', () => {
        console.log('Conexão com o servidor de sinalização fechada.');
        tcpBuffer = Buffer.alloc(0);

        if (userRequestedQuit) {
            console.log("Socket fechado durante o processo de quit iniciado pelo usuário. Não recriar janela.");
        } else {
            console.log("Socket fechado inesperadamente (não iniciado pelo quit-app).");
            if (mainWindow && !mainWindow.isDestroyed()) {
                console.log("Fechando mainWindow e recriando authWindow.");
                mainWindow.close();
                createAuthWindow();
            } else if (!authWindow || authWindow.isDestroyed()) {
                console.log("Recriando authWindow após fechamento inesperado (sem mainWindow).");
                createAuthWindow();
            }
        }
    });

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            if (!client.connecting && client.destroyed) {
                client.connect(SERVER_PORT, SERVER_HOST);
            } else if (!authWindow) {
                createAuthWindow();
            }
        }
    });

});

// Lidando com login sucedido
ipcMain.on('login-success', () => {
    if (authWindow) { authWindow.close(); authWindow = null; }
    createMainWindow();
});

// Envio de mensagens para o Servidor
ipcMain.on('to-server', (event, data) => {
    try {
        const commandCode = CommandCode[data.command];
        if (commandCode === undefined) {
            console.error(`Comando desconhecido do Renderer: ${data.command}`);
            return;
        }
        const messageBuffer = createBinaryMessage(commandCode, data.payload);
        console.log(`Electron -> Servidor de sinalização: Cmd=${data.command}(0x${commandCode.toString(16)}), Len=${messageBuffer.length - 3}`);
        client.write(messageBuffer);
    } catch (e) {
        console.error('Falha ao criar ou enviar mensagem binária:', e);
    }
});

// Tratamento do pedido de encerramento da aplicação
ipcMain.on('quit-app', () => {
    console.log("Recebido 'quit-app', definindo flag e encerrando a aplicação...");
    userRequestedQuit = true;
    app.quit();
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('before-quit', () => {
    console.log("App 'before-quit' event. Destruindo socket TCP se existir.");
    if (client && !client.destroyed) {
        client.destroy();
    }
});