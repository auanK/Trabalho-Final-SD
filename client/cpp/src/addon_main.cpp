#include <napi.h>

#include "voip_client.h"

Napi::Object Init(Napi::Env env, Napi::Object exports) {
    VoipClient::Init(env, exports);
    return exports;
}

NODE_API_MODULE(voip_addon, Init)