#ifndef AUDIO_ENGINE_H
#define AUDIO_ENGINE_H

#include <opus/opus.h>
#include <portaudio.h>

#include <atomic>

#include "audio_constants.h"
#include "jitter_buffer.h"
#include "thread_safe_queue.h"

namespace audio {

// Classe que implementa a lógica principal do cliente de áudio, incluindo a
// captura de áudio, codificação/decodificação, e reprodução.
class audio_engine {
   private:
    // Armazena as configurações de áudio.
    Config _config;
    // Ponteiro para o stream de áudio (entrada/saída) do PortAudio.
    PaStream* _stream = nullptr;
    // Ponteiro para a instância do codificador Opus (mic -> rede).
    OpusEncoder* _encoder = nullptr;
    // Ponteiro para a instância do decodificador Opus (rede -> alto-falante).
    OpusDecoder* _decoder = nullptr;
    // Flag para inicializar/parar o motor de áudio.
    std::atomic<bool> _is_running{false};

    // Fila segura para pacotes de áudio de saída.
    // A thread de áudio escreve pacotes aqui, e a thread de rede os lê.
    ThreadSafeQueue<Packet> _outgoing_queue;

    // Fila segura para pacotes de áudio de entrada.
    // A thread de rede escreve pacotes aqui, e a thread de áudio os lê.
    ThreadSafeQueue<Packet> _incoming_queue;

    // Buffer de jitter para suavizar a reprodução de áudio.
    JitterBuffer _jitter_buffer;

    // Callback de áudio principal.
    // Esta função é chamada em uma thread de áudio de alta prioridade pelo
    // PortAudio e é responsável por capturar o áudio cru do microfone,
    // codificá-lo usando o Opus, e colocá-lo na fila de saída. Também pega
    // pacotes de áudio da fila de entrada, decodifica-os e os coloca no buffer
    // de saída para reprodução.
    int audio_callback(const void* in, void* out, unsigned long frames);

    // Função estática para servir como trampolim para o callback de áudio.
    // Isso é necessário porque o PortAudio espera uma função C-style.
    static int pa_callback_trampoline(const void* in, void* out,
                                      unsigned long frames,
                                      const PaStreamCallbackTimeInfo* time_info,
                                      PaStreamCallbackFlags flags, void* user);

   public:
    // Construtor, inicializa o motor de áudio com as configurações padrões caso
    // não sejam fornecidas.
    explicit audio_engine(const Config& config = {});

    // Destrutor, garante que stop() seja chamado para liberar recursos.
    ~audio_engine();

    // Desabilita cópia e movimentação
    audio_engine(const audio_engine&) = delete;
    audio_engine& operator=(const audio_engine&) = delete;
    audio_engine(audio_engine&&) = delete;
    audio_engine& operator=(audio_engine&&) = delete;

    // Tenta inicializar o PortAudio, Opus, e inicia o stream de áudio.
    bool start();

    // Para o stream de áudio e libera recursos.
    void stop();

    // Verifica se o motor de áudio está em execução.
    bool is_running() const;

    // Chamada pela thread de rede (send_thread_func), tenta obter o próximo
    // pacote de áudio codificado para envio.
    bool get_next_outgoing_packet(Packet& packet);

    // Chamado pela thread de rede (recv_thread_func), para enviar um pacote de
    // áudio recebido
    void submit_incoming_packet(const Packet& packet);
};

}  // namespace audio

#endif