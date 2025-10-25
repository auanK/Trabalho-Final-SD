#include "audio_engine.h"

#include <portaudio.h>

#include <cstring>
#include <iostream>
#include <stdexcept>

namespace audio {

audio_engine::audio_engine(const Config& config)
    : _config(config),
      _jitter_buffer(jitter_target_packets(config),
                     jitter_max_packets(config)) {}
audio_engine::~audio_engine() { stop(); }

bool audio_engine::start() {
    if (_is_running.load()) return true;

    PaError pa_err;
    int opus_err;

    pa_err = Pa_Initialize();
    if (pa_err != paNoError) {
        std::cerr << "ERRO Pa_Initialize: " << Pa_GetErrorText(pa_err)
                  << std::endl;
        return false;
    }

    _encoder = opus_encoder_create(_config.sample_rate, _config.channels,
                                   OPUS_APPLICATION_VOIP, &opus_err);
    if (opus_err != OPUS_OK) {
        std::cerr << "ERRO opus_encoder_create: " << opus_strerror(opus_err)
                  << std::endl;
        Pa_Terminate();
        return false;
    }
    opus_encoder_ctl(_encoder, OPUS_SET_BITRATE(_config.opus_bitrate_bps));

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

    PaStreamParameters inputParams{}, outputParams{};
    const int frames = frames_per_buffer(_config);

    inputParams.device = Pa_GetDefaultInputDevice();
    inputParams.channelCount = _config.channels;
    inputParams.sampleFormat = _config.pa_format;
    inputParams.suggestedLatency =
        Pa_GetDeviceInfo(Pa_GetDefaultInputDevice())->defaultLowInputLatency;

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

    pa_err = Pa_OpenStream(&_stream, &inputParams, &outputParams,
                           _config.sample_rate, frames, paClipOff,
                           pa_callback_trampoline, this);
    if (pa_err != paNoError) {
        std::cerr << "ERRO Pa_OpenStream: " << Pa_GetErrorText(pa_err)
                  << std::endl;
        stop();
        return false;
    }

    pa_err = Pa_StartStream(_stream);
    if (pa_err != paNoError) {
        std::cerr << "ERRO Pa_StartStream: " << Pa_GetErrorText(pa_err)
                  << std::endl;
        stop();
        return false;
    }

    _is_running.store(true);
    return true;
}

void audio_engine::stop() {
    bool expected = true;
    if (!_is_running.compare_exchange_strong(expected, false)) return;

    if (_stream) {
        Pa_AbortStream(_stream);

        Pa_CloseStream(_stream);
        _stream = nullptr;
    }
    if (_encoder) {
        opus_encoder_destroy(_encoder);
        _encoder = nullptr;
    }
    if (_decoder) {
        opus_decoder_destroy(_decoder);
        _decoder = nullptr;
    }
    Pa_Terminate();

    _outgoing_queue.clear();
    _incoming_queue.clear();
    _jitter_buffer.clear();
}

bool audio_engine::is_running() const {
    return _is_running.load(std::memory_order_relaxed);
}

bool audio_engine::get_next_outgoing_packet(Packet& packet) {
    return _outgoing_queue.try_pop(packet);
}

void audio_engine::submit_incoming_packet(const Packet& packet) {
    _incoming_queue.push(packet);
}

int audio_engine::pa_callback_trampoline(const void* input, void* output,
                                         unsigned long frames,
                                         const PaStreamCallbackTimeInfo*,
                                         PaStreamCallbackFlags, void* user) {
    audio_engine* engine = static_cast<audio_engine*>(user);
    if (engine && engine->_is_running.load(std::memory_order_relaxed)) {
        return engine->audio_callback(input, output, frames);
    }
    return paComplete;
}

int audio_engine::audio_callback(const void* input_buffer_raw,
                                 void* output_buffer_raw,
                                 unsigned long frames_per_buffer) {
    if (input_buffer_raw && _encoder) {
        const SampleT* input_samples =
            static_cast<const SampleT*>(input_buffer_raw);
        unsigned char compressed_payload[max_packet_size_opus];

        opus_int32 compressed_bytes =
            opus_encode(_encoder, input_samples, frames_per_buffer,
                        compressed_payload, max_packet_size_opus);

        if (compressed_bytes > 0) {
            Packet packet_out;
            packet_out.data.assign(compressed_payload,
                                   compressed_payload + compressed_bytes);
            _outgoing_queue.push(std::move(packet_out));
        }
    }

    if (output_buffer_raw && _decoder) {
        SampleT* output_samples = static_cast<SampleT*>(output_buffer_raw);

        Packet net_packet;
        while (_incoming_queue.try_pop(net_packet)) {
            _jitter_buffer.push(net_packet);
        }

        Packet packet_to_decode;
        int decoded_frames = -1;

        if (_jitter_buffer.pop(packet_to_decode)) {
            decoded_frames = opus_decode(_decoder, packet_to_decode.data.data(),
                                         packet_to_decode.data.size(),
                                         output_samples, frames_per_buffer, 0);
        } else {
            decoded_frames = opus_decode(_decoder, nullptr, 0, output_samples,
                                         frames_per_buffer, 0);
        }

        if (decoded_frames != static_cast<int>(frames_per_buffer)) {
            memset(output_buffer_raw, 0,
                   frames_per_buffer * _config.channels * bytes_per_sample);
        }
    } else if (output_buffer_raw) {
        memset(output_buffer_raw, 0,
               frames_per_buffer * _config.channels * bytes_per_sample);
    }

    return paContinue;
}
}  // namespace audio