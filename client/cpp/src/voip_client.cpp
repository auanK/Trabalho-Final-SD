#include "voip_client.h"

VoipClient::VoipClient(const Napi::CallbackInfo& info)
    : Napi::ObjectWrap<VoipClient>(info), _socket(_io_context) {
    _audio_packet_header.fill(0);
}

VoipClient::~VoipClient() { CppStop(); }

Napi::Object VoipClient::Init(Napi::Env env, Napi::Object exports) {
    Napi::Function func =
        DefineClass(env, "VoipClient",
                    {
                        InstanceMethod("start", &VoipClient::Start),
                        InstanceMethod("stop", &VoipClient::Stop),
                    });
    exports.Set("VoipClient", func);
    return exports;
}

void VoipClient::send_thread_func() {
    while (_is_running.load()) {
        audio::Packet packet_out;
        if (_engine.get_next_outgoing_packet(packet_out)) {
            std::array<asio::const_buffer, 2> send_buffers = {
                asio::buffer(_audio_packet_header),
                asio::buffer(packet_out.data)};

            try {
                _socket.send_to(send_buffers, _server_endpoint);
            } catch (const std::exception& e) {
                if (_is_running.load()) {
                    std::cerr << "ERRO C++: send_to() falhou: " << e.what()
                              << std::endl;
                }
            }
        }
        std::this_thread::sleep_for(
            std::chrono::milliseconds(SEND_LOOP_SLEEP_MS));
    }
}

void VoipClient::recv_thread_func() {
    char recv_buffer[MAX_PACKET_SIZE];

    while (_is_running.load()) {
        try {
            udp::endpoint sender_endpoint;
            size_t bytes_recvd = _socket.receive_from(
                asio::buffer(recv_buffer, MAX_PACKET_SIZE), sender_endpoint);

            if (sender_endpoint != _server_endpoint ||
                bytes_recvd <= PACKET_HEADER_LEN_FULL) {
                continue;
            }

            if (memcmp(recv_buffer + SESSION_ID_LEN, STATIC_MAGIC_TOKEN.data(),
                       TOKEN_LEN) != 0) {
                continue;
            }

            PacketType packet_type =
                static_cast<PacketType>(recv_buffer[HEADER_LEN]);
            char* payload_start = recv_buffer + PACKET_HEADER_LEN_FULL;
            int payload_size = bytes_recvd - PACKET_HEADER_LEN_FULL;

            if (payload_size <= 0) continue;

            switch (packet_type) {
                case PacketType::AUDIO_OPUS:
                    _engine.submit_incoming_packet({std::vector<unsigned char>(
                        payload_start, payload_start + payload_size)});
                    break;
                case PacketType::CONTROL_JSON: {
                    std::string json_payload(payload_start, payload_size);
                    _tsfn.BlockingCall([json_payload](
                                           Napi::Env env,
                                           Napi::Function js_callback) {
                        Napi::Object event = Napi::Object::New(env);
                        event.Set("type", "notification");
                        event.Set("data", Napi::String::New(env, json_payload));
                        js_callback.Call({event});
                    });
                    break;
                }
                default:
                    break;
            }

        } catch (const std::exception& e) {
            if (_is_running.load()) {
                std::string error_msg = "ERRO C++: recv_thread_func falhou: " +
                                        std::string(e.what());
                _tsfn.BlockingCall(
                    [error_msg](Napi::Env env, Napi::Function js_callback) {
                        Napi::Object event = Napi::Object::New(env);
                        event.Set("type", "error");
                        event.Set("data", Napi::String::New(env, error_msg));
                        js_callback.Call({event});
                    });
            }
            break;
        }
    }
}

void VoipClient::CppStop() {
    bool expected = true;
    if (!_is_running.compare_exchange_strong(expected, false)) {
        return;
    }
    _engine.stop();
    if (_socket.is_open()) {
        _socket.close();
    }
    if (_receiver_thread.joinable()) {
        _receiver_thread.join();
    }
    if (_sender_thread.joinable()) {
        _sender_thread.join();
    }
}

std::vector<char> VoipClient::pad_session_id(const std::string& id_str) {
    std::vector<char> session_id(SESSION_ID_LEN, 0);
    std::copy(id_str.begin(),
              id_str.begin() + std::min(id_str.size(), (size_t)SESSION_ID_LEN),
              session_id.begin());
    return session_id;
}

Napi::Value VoipClient::Start(const Napi::CallbackInfo& info) {
    Napi::Env env = info.Env();
    if (_is_running.load()) {
        Napi::Error::New(env, "Chamada ja esta em andamento")
            .ThrowAsJavaScriptException();
        return env.Undefined();
    }
    if (info.Length() < 2 || !info[0].IsObject() || !info[1].IsFunction()) {
        Napi::Error::New(
            env, "Argumentos invalidos: start(options, callback) e esperado")
            .ThrowAsJavaScriptException();
        return env.Undefined();
    }

    try {
        Napi::Object options = info[0].As<Napi::Object>();
        std::string relay_ip = options.Get("relay_server")
                                   .As<Napi::Object>()
                                   .Get("ip")
                                   .As<Napi::String>()
                                   .Utf8Value();
        int relay_port = options.Get("relay_server")
                             .As<Napi::Object>()
                             .Get("port")
                             .As<Napi::Number>()
                             .Int32Value();
        std::string session_id_str =
            options.Get("session_id").As<Napi::String>().Utf8Value();
        std::string my_info_json =
            options.Get("my_user_info_json").As<Napi::String>().Utf8Value();

        Napi::Function js_callback = info[1].As<Napi::Function>();
        _tsfn = Napi::ThreadSafeFunction::New(env, js_callback,
                                              "VoipClientCallback", 0, 1);

        std::vector<char> session_id_bytes = pad_session_id(session_id_str);

        char* p = _audio_packet_header.data();
        memcpy(p, session_id_bytes.data(), SESSION_ID_LEN);
        p += SESSION_ID_LEN;
        memcpy(p, STATIC_MAGIC_TOKEN.data(), TOKEN_LEN);
        p += TOKEN_LEN;
        *p = static_cast<char>(PacketType::AUDIO_OPUS);

        udp::resolver resolver(_io_context);
        _server_endpoint =
            *resolver.resolve(udp::v4(), relay_ip, std::to_string(relay_port))
                 .begin();
        _socket.open(udp::v4());

        if (!_engine.start()) {
            Napi::Error::New(env, "Falha ao iniciar audio_engine")
                .ThrowAsJavaScriptException();
            if (_socket.is_open()) _socket.close();
            _tsfn.Release();
            return env.Undefined();
        }

        std::vector<char> registration_header(PACKET_HEADER_LEN_FULL);
        p = registration_header.data();
        memcpy(p, session_id_bytes.data(), SESSION_ID_LEN);
        p += SESSION_ID_LEN;
        memcpy(p, STATIC_MAGIC_TOKEN.data(), TOKEN_LEN);
        p += TOKEN_LEN;
        *p = static_cast<char>(PacketType::CONTROL_JSON);

        std::array<asio::const_buffer, 2> reg_buffers = {
            asio::buffer(registration_header), asio::buffer(my_info_json)};
        _socket.send_to(reg_buffers, _server_endpoint);

        _is_running.store(true);
        _receiver_thread = std::thread(&VoipClient::recv_thread_func, this);
        _sender_thread = std::thread(&VoipClient::send_thread_func, this);

    } catch (const Napi::Error& e) {
        Napi::Error::New(env, "Erro ao processar 'options': " + e.Message())
            .ThrowAsJavaScriptException();
        return env.Undefined();
    } catch (const std::exception& e) {
        Napi::Error::New(
            env, "Erro interno C++ (Asio) ao iniciar: " + std::string(e.what()))
            .ThrowAsJavaScriptException();
        return env.Undefined();
    }
    return env.Undefined();
}

Napi::Value VoipClient::Stop(const Napi::CallbackInfo& info) {
    Napi::Env env = info.Env();
    CppStop();
    if (_tsfn) {
        _tsfn.BlockingCall([](Napi::Env env, Napi::Function js_callback) {
            Napi::Object event = Napi::Object::New(env);
            event.Set("type", "stopped");
            event.Set("data",
                      Napi::String::New(env, "Chamada encerrada pelo C++"));
            js_callback.Call({event});
        });
        _tsfn.Release();
    }
    return env.Undefined();
}