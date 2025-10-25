#ifndef JITTER_BUFFER_H
#define JITTER_BUFFER_H

#include <algorithm>
#include <deque>

#include "audio_constants.h"

namespace audio {

class JitterBuffer {
   public:
    explicit JitterBuffer(int target_packets, int max_packets)
        : _target(std::max(1, target_packets)),
          _max(std::max(_target, max_packets)) {}

    void push(const Packet& p) {
        if (_buffer.size() >= static_cast<size_t>(_max)) {
            _buffer.pop_front();
        }
        _buffer.push_back(p);
    }

    bool pop(Packet& out) {
        if (_buffer.size() >= static_cast<size_t>(_target)) {
            out = std::move(_buffer.front());
            _buffer.pop_front();
            return true;
        }
        return false;
    }

    size_t size() const { return _buffer.size(); }
    void clear() { _buffer.clear(); }

   private:
    std::deque<Packet> _buffer;
    int _target;
    int _max;
};

}  // namespace audio

#endif