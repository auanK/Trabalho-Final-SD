#ifndef AUDIO_CONSTANTS_H
#define AUDIO_CONSTANTS_H

#include <opus/opus.h>
#include <portaudio.h>

#include <algorithm>
#include <cstdint>
#include <vector>

namespace audio {

// Armazena todas as configurações de áudio relevantes.
struct Config {
    // Taxa de amostragem, 48kHz é o padrão comum para áudio de alta qualidade.
    int sample_rate = 48000;
    // Número de canais de áudio, 1 para mono, 2 para estéreo.
    int channels = 1;
    // Profundidade de bits por amostra, 16 bits é padrão CD.
    PaSampleFormat pa_format = paInt16;
    // A duração de cada frame de áudio em milissegundos.
    int frame_duration_ms = 20;
    // Taxa de bits para codificação Opus em bits por segundo.
    int opus_bitrate_bps = 48000;
    // Número mínimo de pacotes a serem acumulados no buffer de jitter para
    // reprodução.
    int jitter_target_ms = 60;
    // Número máximo de pacotes que o buffer de jitter pode conter antes de
    // descartar pacotes antigos.
    int jitter_max_ms = 200;
};

// Alias para o tipo de amostra usado pelo Opus.
using SampleT = opus_int16;

// Representa um único pacote de dados de áudio.
struct Packet {
    // Os bytes brutos do pacote de áudio.
    std::vector<unsigned char> data;
};

// Número de bytes por amostra de áudio.
constexpr int bytes_per_sample = sizeof(SampleT);

// Tamanho máximo do pacote Opus em bytes.
constexpr int max_packet_size_opus = 1276;

// Número máximo de amostras por frame que o Opus pode lidar, 120ms a 48kHz.
constexpr int max_frame_samples_opus = 5760 * 1;

// Função auxiliar para calcular o número de frames por buffer.
inline int frames_per_buffer(const Config& c) {
    return (c.sample_rate * c.frame_duration_ms) / 1000;
}

// Função auxiliar para converter milissegundos em número de pacotes.
inline int ms_to_packets(int ms, int frame_duration_ms) {
    return std::max(1, ms / std::max(1, frame_duration_ms));
}

// Cálculo do número de pacotes alvo e máximo para o buffer de jitter.
inline int jitter_target_packets(const Config& c) {
    return ms_to_packets(c.jitter_target_ms, c.frame_duration_ms);
}

// Calcula o número máximo de pacotes no buffer de jitter.
inline int jitter_max_packets(const Config& c) {
    return std::max(jitter_target_packets(c),
                    ms_to_packets(c.jitter_max_ms, c.frame_duration_ms));
}

}  // namespace audio

#endif