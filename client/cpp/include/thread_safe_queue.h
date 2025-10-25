#ifndef THREAD_SAFE_QUEUE_H
#define THREAD_SAFE_QUEUE_H

#include <mutex>
#include <queue>
#include <utility>

namespace audio {

template <typename T>
class ThreadSafeQueue {
   private:
    mutable std::mutex _mtx;
    std::queue<T> _q;

   public:
    ThreadSafeQueue() = default;
    ~ThreadSafeQueue() = default;
    ThreadSafeQueue(const ThreadSafeQueue&) = delete;
    ThreadSafeQueue& operator=(const ThreadSafeQueue&) = delete;

    void push(T item) {
        std::lock_guard<std::mutex> lock(_mtx);
        _q.push(std::move(item));
    }

    bool try_pop(T& out) {
        std::lock_guard<std::mutex> lock(_mtx);
        if (_q.empty()) return false;
        out = std::move(_q.front());
        _q.pop();
        return true;
    }

    size_t size() const {
        std::lock_guard<std::mutex> lock(_mtx);
        return _q.size();
    }

    void clear() {
        std::lock_guard<std::mutex> lock(_mtx);
        std::queue<T> empty_q;
        _q.swap(empty_q);
    }
};

}  // namespace audio

#endif