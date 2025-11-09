const { contextBridge, ipcRenderer } = require('electron');
const path = require('path');

// Lógica do Addon C++ 
try {
    const addonPath = path.resolve(__dirname, '../voip_addon.node');
    const voipAddon = require(addonPath);
    const clientInstance = new voipAddon.VoipClient();
    console.log("Preload: Addon C++ carregado e instanciado com sucesso.");

    contextBridge.exposeInMainWorld('voip', {
        startCall: (options, callback) => {
            try {
                console.log("Preload: Chamando voip_client.start() com:", options);
                clientInstance.start(options, callback);
                return { success: true };
            } catch (e) {
                console.error("Preload: Erro ao chamar clientInstance.start:", e);
                return { success: false, error: e.message };
            }
        },

        stopCall: () => {
            try {
                console.log("Preload: Chamando voip_client.stop()...");
                clientInstance.stop();
                return { success: true };
            } catch (e) {
                console.error("Preload: Erro ao chamar clientInstance.stop:", e);
                return { success: false, error: e.message };
            }
        }
    });

} catch (e) {
    console.error("!!!!!!!!!!!! FALHA CRÍTICA AO CARREGAR O voip_addon.node !!!!!!!!!!!!");
    console.error("Verifique se o caminho está correto e se o addon foi compilado.");
    console.error(`Caminho tentado: ${path.resolve(__dirname, '../voip_addon.node')}`);
    console.error(e);
}

// API de comunicação RMI (Refatorada)
contextBridge.exposeInMainWorld('api', {
    callRMI: (method, params = []) => {
        return ipcRenderer.invoke('rmi-call', { method, params });
    },

    send: (channel, data) => {
        const validChannels = ['login-success', 'quit-app'];
        if (validChannels.includes(channel)) {
            ipcRenderer.send(channel, data);
        }
    },

    receive: (channel, func) => {
        const validChannels = ['server-error'];
        if (validChannels.includes(channel)) {
            ipcRenderer.on(channel, (event, ...args) => func(...args));
        }
    }
});