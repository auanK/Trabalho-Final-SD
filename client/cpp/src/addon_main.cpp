#include <napi.h>

#include "voip_client.h"

// Função de inicialização do módulo chamada pelo N-API, o node chama essa
// função quando o .node é carregado pela primeira vez (ex: com
// require('./addon.node'))
Napi::Object Init(Napi::Env env, Napi::Object exports) {
    // Chama a função estática 'Init' da nossa classe VoipClient.
    VoipClient::Init(env, exports);

    // Retorna o objeto exports que agora contém a classe VoipClient
    return exports;
}

// Macro do Node.js que registra o addon.
NODE_API_MODULE(voip_addon, Init)