const { contextBridge, ipcRenderer } = require('electron');
const path = require('path');

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

contextBridge.exposeInMainWorld('electron', {
    send: (channel, data) => {
        ipcRenderer.send(channel, data);
    },

    receive: (channel, func) => {
        const validChannels = ['from-server', 'server-error'];

        if (validChannels.includes(channel)) {
            ipcRenderer.on(channel, (event, ...args) => func(...args));
        }
    }
});