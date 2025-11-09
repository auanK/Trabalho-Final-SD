#include "audio_engine.h"

#include <portaudio.h>

#include <cstring>
#include <iostream>
#include <stdexcept>

namespace audio {

// Inicializa o motor de áudio com as configurações padrões ou fornecidas.
audio_engine::audio_engine(const Config& config)
    : _config(config),
      _jitter_buffer(jitter_target_packets(config),
                     jitter_max_packets(config)) {}

// Destrutor, garante que stop() seja chamado para liberar recursos.
audio_engine::~audio_engine() { stop(); }

// Tenta inicializar o PortAudio, Opus, e inicia o stream de áudio.
bool audio_engine::start() {
    if (_is_running.load()) return true;

    PaError pa_err;
    int opus_err;

    // Inicializa PortAudio
    pa_err = Pa_Initialize();
    if (pa_err != paNoError) {
        std::cerr << "ERRO Pa_Initialize: " << Pa_GetErrorText(pa_err)
                  << std::endl;
        return false;
    }

    // Cria o codificador Opus (Para áudio do microfone -> rede)
    _encoder = opus_encoder_create(_config.sample_rate, _config.channels,
                                   OPUS_APPLICATION_VOIP, &opus_err);
    if (opus_err != OPUS_OK) {
        std::cerr << "ERRO opus_encoder_create: " << opus_strerror(opus_err)
                  << std::endl;
        Pa_Terminate();
        return false;
    }

    // Define a taxa de bits do codificador Opus
    opus_encoder_ctl(_encoder, OPUS_SET_BITRATE(_config.opus_bitrate_bps));

    // Cria o decodificador Opus (Para áudio da rede -> alto-falante)
    _decoder =
        opus_decoder_create(_config.sample_rate, _config.channels, &opus_err);
    if (opus_err != OPUS_OK) {
        std::cerr << "ERRO opus_decoder_create: " << opus_strerror(opus_err)
                  << std::endl;
        opus_encoder_destroy(_encoder);
        _encoder = nullptr;
        Pa_Terminate();
        return false;
    }

    // Configura os parâmetros do stream de áudio
    PaStreamParameters inputParams{}, outputParams{};
    const int frames = frames_per_buffer(_config);

    // Configura o microfone
    inputParams.device = Pa_GetDefaultInputDevice();
    inputParams.channelCount = _config.channels;
    inputParams.sampleFormat = _config.pa_format;
    inputParams.suggestedLatency =
        Pa_GetDeviceInfo(Pa_GetDefaultInputDevice())->defaultLowInputLatency;

    // Configura o alto-falante
    outputParams.device = Pa_GetDefaultOutputDevice();
    outputParams.channelCount = _config.channels;
    outputParams.sampleFormat = _config.pa_format;
    outputParams.suggestedLatency =
        Pa_GetDeviceInfo(Pa_GetDefaultOutputDevice())->defaultLowOutputLatency;

    if (inputParams.device == paNoDevice || outputParams.device == paNoDevice) {
        std::cerr
            << "ERRO: Dispositivo de entrada ou saída padrão não encontrado."
            << std::endl;
        stop();
        return false;
    }

    // Abre o stream de áudio
    pa_err = Pa_OpenStream(&_stream, &inputParams, &outputParams,
                           _config.sample_rate, frames, paClipOff,
                           pa_callback_trampoline, this);
    if (pa_err != paNoError) {
        std::cerr << "ERRO Pa_OpenStream: " << Pa_GetErrorText(pa_err)
                  << std::endl;
        stop();
        return false;
    }

    // Inicia o stream de áudio
    pa_err = Pa_StartStream(_stream);
    if (pa_err != paNoError) {
        std::cerr << "ERRO Pa_StartStream: " << Pa_GetErrorText(pa_err)
                  << std::endl;
        stop();
        return false;
    }

    // Sinaliza que o motor de áudio está em execução
    _is_running.store(true);
    return true;
}

// Para o stream de áudio e libera recursos.
void audio_engine::stop() {
    // Garante que essa função só execute uma vez
    bool expected = true;
    if (!_is_running.compare_exchange_strong(expected, false)) return;

    // Para o stream do PortAudio e libera recursos
    if (_stream) {
        Pa_AbortStream(_stream);
        Pa_CloseStream(_stream);
        _stream = nullptr;
    }
    // Libera o codificador Opus
    if (_encoder) {
        opus_encoder_destroy(_encoder);
        _encoder = nullptr;
    }
    // Libera o decodificador Opus
    if (_decoder) {
        opus_decoder_destroy(_decoder);
        _decoder = nullptr;
    }
    // Desliga a biblioteca PortAudio
    Pa_Terminate();

    // Limpa as filas de dados
    _outgoing_queue.clear();
    _incoming_queue.clear();
    _jitter_buffer.clear();
}

// Verifica se o motor de áudio está em execução.
bool audio_engine::is_running() const {
    return _is_running.load(std::memory_order_relaxed);
}

// Chamada pela thread de rede (send_thread_func), tenta obter o próximo
// pacote de áudio codificado para envio.
bool audio_engine::get_next_outgoing_packet(Packet& packet) {
    return _outgoing_queue.try_pop(packet);
}

// Chamado pela thread de rede (recv_thread_func), para enviar um pacote de
// áudio recebido
void audio_engine::submit_incoming_packet(const Packet& packet) {
    _incoming_queue.push(packet);
}

// Função estática para servir como trampolim para o callback de áudio.
// Isso é necessário porque o PortAudio espera uma função C-style.
int audio_engine::pa_callback_trampoline(const void* input, void* output,
                                         unsigned long frames,
                                         const PaStreamCallbackTimeInfo*,
                                         PaStreamCallbackFlags, void* user) {
    // Converte o ponteiro user de volta para a instância do audio_engine
    audio_engine* engine = static_cast<audio_engine*>(user);

    // Chama o método de callback real se o motor estiver em execução para pular
    // para a função membro C++ real
    if (engine && engine->_is_running.load(std::memory_order_relaxed)) {
        return engine->audio_callback(input, output, frames);
    }
    // Se o motor não estiver em execução, indica que o PortAudio deve parar
    return paComplete;
}

// Callback de áudio principal.
// Esta função é chamada em uma thread de áudio de alta prioridade pelo
// PortAudio e é responsável por capturar o áudio cru do microfone,
// codificá-lo usando o Opus, e colocá-lo na fila de saída. Também pega
// pacotes de áudio da fila de entrada, decodifica-os e os coloca no buffer
// de saída para reprodução.
int audio_engine::audio_callback(const void* input_buffer_raw,
                                 void* output_buffer_raw,
                                 unsigned long frames_per_buffer) {
    // Microfone -> Rede
    if (input_buffer_raw && _encoder) {
        // Pega o buffer de entrada e o converte para o tipo correto
        const SampleT* input_samples =
            static_cast<const SampleT*>(input_buffer_raw);

        // Buffer temporário para o áudio comprimido
        unsigned char compressed_payload[max_packet_size_opus];

        // Codifica o áudio usando Opus
        opus_int32 compressed_bytes =
            opus_encode(_encoder, input_samples, frames_per_buffer,
                        compressed_payload, max_packet_size_opus);

        // Envia para a fila de saída
        if (compressed_bytes > 0) {
            Packet packet_out;
            // Copia os dados codificados para o pacote
            packet_out.data.assign(compressed_payload,
                                   compressed_payload + compressed_bytes);
            // Coloca o pacote na fila de saída
            _outgoing_queue.push(std::move(packet_out));
        }
    }

    // Rede -> Alto-falante
    if (output_buffer_raw && _decoder) {
        // Pega o buffer de saída e o converte para o tipo correto
        SampleT* output_samples = static_cast<SampleT*>(output_buffer_raw);

        // Move todos os pacotes disponíveis da fila de entrada para o buffer de
        // jitter
        Packet net_packet;
        while (_incoming_queue.try_pop(net_packet)) {
            _jitter_buffer.push(net_packet);
        }

        // Prepara um pacote para decodificação
        Packet packet_to_decode;
        int decoded_frames = -1;

        // Tenta pegar um pacote do buffer de jitter
        if (_jitter_buffer.pop(packet_to_decode)) {
            // Decodifica o pacote usando Opus para áudio cru
            decoded_frames = opus_decode(_decoder, packet_to_decode.data.data(),
                                         packet_to_decode.data.size(),
                                         output_samples, frames_per_buffer, 0);
        } else {
            // Se não houver pacote disponível, gera silêncio
            decoded_frames = opus_decode(_decoder, nullptr, 0, output_samples,
                                         frames_per_buffer, 0);
        }

        // Se a decodificação falhar ou não retornar frames suficientes,
        // preenche o restante com silêncio
        if (decoded_frames != static_cast<int>(frames_per_buffer)) {
            memset(output_buffer_raw, 0,
                   frames_per_buffer * _config.channels * bytes_per_sample);
        }
    } else if (output_buffer_raw) {
        // Se o áudio de saída está ligado mas não há decodificador, gera
        // silêncio
        memset(output_buffer_raw, 0,
               frames_per_buffer * _config.channels * bytes_per_sample);
    }

    // Sinalza para o PortAudio continuar chamando o callback
    return paContinue;
}
}  // namespace audio