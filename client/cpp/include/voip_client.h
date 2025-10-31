#ifndef VOIP_CLIENT_H
#define VOIP_CLIENT_H

#include <napi.h>

#include <array>
#include <asio.hpp>
#include <atomic>
#include <chrono>
#include <cstring>
#include <iostream>
#include <string>
#include <thread>
#include <vector>

#include "audio_constants.h"
#include "audio_engine.h"

using asio::ip::udp;

enum class PacketType : uint8_t { AUDIO_OPUS = 0x01, CONTROL_JSON = 0x02 };

const std::vector<char> STATIC_MAGIC_TOKEN = {
    (char)0xDE, (char)0xAD, (char)0xBE, (char)0xEF,
    (char)0xCA, (char)0xFE, (char)0xBA, (char)0xBE};

constexpr int SESSION_ID_LEN = 16;
constexpr int TOKEN_LEN = 8;
constexpr int PACKET_TYPE_LEN = sizeof(PacketType);
constexpr int HEADER_LEN = SESSION_ID_LEN + TOKEN_LEN;
constexpr int PACKET_HEADER_LEN_FULL = HEADER_LEN + PACKET_TYPE_LEN;
constexpr int MAX_PACKET_SIZE = 1500;
constexpr int SEND_LOOP_SLEEP_MS = 10;

class VoipClient : public Napi::ObjectWrap<VoipClient> {
   private:
    audio::audio_engine _engine;
    std::atomic<bool> _is_running{false};

    std::thread _sender_thread;
    std::thread _receiver_thread;

    Napi::ThreadSafeFunction _tsfn;

    asio::io_context _io_context;
    udp::socket _socket;
    udp::endpoint _server_endpoint;

    std::array<char, PACKET_HEADER_LEN_FULL> _audio_packet_header;

    void send_thread_func();
    void recv_thread_func();
    std::vector<char> pad_session_id(const std::string& id_str);
    void CppStop();

   public:
    static Napi::Object Init(Napi::Env env, Napi::Object exports);
    VoipClient(const Napi::CallbackInfo& info);
    ~VoipClient();

    Napi::Value Start(const Napi::CallbackInfo& info);
    Napi::Value Stop(const Napi::CallbackInfo& info);
};

#endif