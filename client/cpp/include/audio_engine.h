#ifndef AUDIO_ENGINE_H
#define AUDIO_ENGINE_H

#include <opus/opus.h>
#include <portaudio.h>

#include <atomic>

#include "audio_constants.h"
#include "jitter_buffer.h"
#include "thread_safe_queue.h"

namespace audio {

class audio_engine {
   private:
    int audio_callback(const void* in, void* out, unsigned long frames);
    static int pa_callback_trampoline(const void* in, void* out,
                                      unsigned long frames,
                                      const PaStreamCallbackTimeInfo* time_info,
                                      PaStreamCallbackFlags flags, void* user);

    Config _config;
    PaStream* _stream = nullptr;
    OpusEncoder* _encoder = nullptr;
    OpusDecoder* _decoder = nullptr;
    std::atomic<bool> _is_running{false};

    ThreadSafeQueue<Packet> _outgoing_queue;
    ThreadSafeQueue<Packet> _incoming_queue;
    JitterBuffer _jitter_buffer;

   public:
    explicit audio_engine(const Config& config = {});
    ~audio_engine();

    audio_engine(const audio_engine&) = delete;
    audio_engine& operator=(const audio_engine&) = delete;
    audio_engine(audio_engine&&) = delete;
    audio_engine& operator=(audio_engine&&) = delete;

    bool start();
    void stop();
    bool is_running() const;

    bool get_next_outgoing_packet(Packet& packet);
    void submit_incoming_packet(const Packet& packet);
};

}  // namespace audio

#endif