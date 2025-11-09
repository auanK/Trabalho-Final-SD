#ifndef THREAD_SAFE_QUEUE_H
#define THREAD_SAFE_QUEUE_H

#include <mutex>
#include <queue>
#include <utility>

namespace audio {

template <typename T>

// Uma fila FIFO simples e segura para acesso concorrente por múltiplas threads.
class ThreadSafeQueue {
   private:
    // O mutex protege o acesso à fila interna.
    mutable std::mutex _mtx;
    // A fila interna que armazena os elementos.
    std::queue<T> _q;

   public:
    // Construtor padrão
    ThreadSafeQueue() = default;

    // Destrutor padrão
    ~ThreadSafeQueue() = default;

    // Desabilita a cópia e movimentação
    ThreadSafeQueue(const ThreadSafeQueue&) = delete;
    ThreadSafeQueue& operator=(const ThreadSafeQueue&) = delete;

    // Adiciona um item ao final da fila.
    void push(T item) {
        std::lock_guard<std::mutex> lock(_mtx);
        _q.push(std::move(item));
    }

    // Tenta remover o item do início da fila.
    bool try_pop(T& out) {
        std::lock_guard<std::mutex> lock(_mtx);
        if (_q.empty()) return false;
        out = std::move(_q.front());
        _q.pop();
        return true;
    }

    // Retorna o tamanho atual da fila.
    size_t size() const {
        std::lock_guard<std::mutex> lock(_mtx);
        return _q.size();
    }

    // Verifica se a fila está vazia.
    void clear() {
        std::lock_guard<std::mutex> lock(_mtx);
        std::queue<T> empty_q;
        _q.swap(empty_q);
    }
};

}  // namespace audio

#endif