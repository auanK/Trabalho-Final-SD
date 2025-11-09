#ifndef JITTER_BUFFER_H
#define JITTER_BUFFER_H

#include <algorithm>
#include <deque>

#include "audio_constants.h"

namespace audio {

// Implementa um buffer de jitter simples para armazenar pacotes de áudio. O
// buffer é a variação no tempo de chegada dos pacotes e ajuda a garantir uma
// reprodução suave, mesmo quando os pacotes chegam em intervalos irregulares.
class JitterBuffer {
   private:
    std::deque<Packet> _buffer;  // A fila de pacotes armazenados
    int _target;                 // Número alvo de pacotes para reprodução
    int _max;  // Número máximo de pacotes que o buffer pode conter

   public:
    // Construtor
    explicit JitterBuffer(int target_packets, int max_packets)
        : _target(std::max(1, target_packets)),
          _max(std::max(_target, max_packets)) {}

    // Adiciona um pacote ao buffer de jitter.
    void push(const Packet& p) {
        if (_buffer.size() >= static_cast<size_t>(_max)) {
            _buffer.pop_front();
        }
        _buffer.push_back(p);
    }

    // Tenta remover e retornar um pacote do buffer de jitter.
    bool pop(Packet& out) {
        if (_buffer.size() >= static_cast<size_t>(_target)) {
            out = std::move(_buffer.front());
            _buffer.pop_front();
            return true;
        }
        return false;
    }

    // Retorna o número atual de pacotes no buffer.
    size_t size() const { return _buffer.size(); }

    // Limpa todos os pacotes do buffer.
    void clear() { _buffer.clear(); }
};

}  // namespace audio

#endif