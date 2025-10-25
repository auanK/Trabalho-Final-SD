#ifndef AUDIO_CONSTANTS_H
#define AUDIO_CONSTANTS_H

#include <opus/opus.h>
#include <portaudio.h>

#include <algorithm>
#include <cstdint>
#include <vector>

namespace audio {

struct Config {
    int sample_rate = 48000;
    int channels = 1;
    PaSampleFormat pa_format = paInt16;
    int frame_duration_ms = 20;
    int opus_bitrate_bps = 48000;
    int jitter_target_ms = 60;
    int jitter_max_ms = 200;
};

using SampleT = opus_int16;

struct Packet {
    std::vector<unsigned char> data;
};

constexpr int bytes_per_sample = sizeof(SampleT);
constexpr int max_packet_size_opus = 1276;
constexpr int max_frame_samples_opus = 5760 * 1;

inline int frames_per_buffer(const Config& c) {
    return (c.sample_rate * c.frame_duration_ms) / 1000;
}

inline int ms_to_packets(int ms, int frame_duration_ms) {
    return std::max(1, ms / std::max(1, frame_duration_ms));
}

inline int jitter_target_packets(const Config& c) {
    return ms_to_packets(c.jitter_target_ms, c.frame_duration_ms);
}
inline int jitter_max_packets(const Config& c) {
    return std::max(jitter_target_packets(c),
                    ms_to_packets(c.jitter_max_ms, c.frame_duration_ms));
}

}  // namespace audio

#endif