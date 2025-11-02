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

// Atalho de namespace para facilitar o uso do ASIO
using asio::ip::udp;

// Define os tipos de pacotes que o cliente pode enviar/receber
enum class PacketType : uint8_t { AUDIO_OPUS = 0x01, CONTROL_JSON = 0x02 };

// Token mágico estático usado para validação de pacotes
const std::vector<char> STATIC_MAGIC_TOKEN = {
    (char)0xDE, (char)0xAD, (char)0xBE, (char)0xEF,
    (char)0xCA, (char)0xFE, (char)0xBA, (char)0xBE};

// Comprimento esperado do ID da sessão
constexpr int SESSION_ID_LEN = 16;
// Comprimento esperado do token mágico
constexpr int TOKEN_LEN = 8;
// Comprimento do tipo de pacote
constexpr int PACKET_TYPE_LEN = sizeof(PacketType);
// Comprimento total do cabeçalho do pacote
constexpr int HEADER_LEN = SESSION_ID_LEN + TOKEN_LEN;
// Comprimento total do cabeçalho do pacote incluindo o tipo
constexpr int PACKET_HEADER_LEN_FULL = HEADER_LEN + PACKET_TYPE_LEN;
// Tamanho máximo do pacote UDP (1500 evita fragmentação)
constexpr int MAX_PACKET_SIZE = 1500;
// Intervalo de sono do loop de envio em milissegundos
constexpr int SEND_LOOP_SLEEP_MS = 10;

// Classe principal que gerencia a lógica do cliente VoIP
class VoipClient : public Napi::ObjectWrap<VoipClient> {
   private:
    // A instância da engine de áudio (que gerencia PortAudio e Opus)
    audio::audio_engine _engine;

    // Flag atômica para controlar o estado de execução dos threads
    std::atomic<bool> _is_running{false};

    // Thread para pegar pacotes UDP da engine e enviar
    std::thread _sender_thread;

    // Thread para receber pacotes UDP e repassar para a engine
    std::thread _receiver_thread;

    // Ponte segura para enviar eventos do C++ (threads) de volta para o
    // callback do JavaScript
    Napi::ThreadSafeFunction _tsfn;

    // O cérebro do Asio, necessário para as operações de I/O
    asio::io_context _io_context;
    // Socket UDP usado para comunicação (Abstração do Asio)
    udp::socket _socket;
    // Endpoint do servidor VoIP
    udp::endpoint _server_endpoint;

    // Cabeçalho de pacote pré-construído para pacotes de áudio
    std::array<char, PACKET_HEADER_LEN_FULL> _audio_packet_header;

    // A função que roda na thread de envio
    void send_thread_func();

    // A função que roda na thread de recebimento
    void recv_thread_func();

    // Função para garantir que o ID da sessão tem o tamanho correto
    std::vector<char> pad_session_id(const std::string& id_str);

    // Função de parada, desliga threads e sockets
    void CppStop();

   public:
    // Ponto de entrada estático chamado pelo N-API, registra a classe
    // VoipClient no Node.js
    static Napi::Object Init(Napi::Env env, Napi::Object exports);

    // Construtor chamado quando new VoipClient() é invocado no JavaScript
    VoipClient(const Napi::CallbackInfo& info);

    // Destrutor C++ chamado quando o objeto JS é coletado pelo Garbage
    // Collector
    ~VoipClient();

    // Inicia a sessão VoIP, criando threads e abrindo socket. (client.start()
    // no JS)
    Napi::Value Start(const Napi::CallbackInfo& info);

    // Para a sessão VoIP, fechando threads e socket. (client.stop() no JS)
    Napi::Value Stop(const Napi::CallbackInfo& info);
};

#endif