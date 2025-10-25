#include <chrono>
#include <deque>
#include <iostream>
#include <thread>
#include <utility>

#include "audio_engine.h"

using Packet = audio::Packet;
using namespace std::chrono;

constexpr int TEST_DURATION_SECONDS = 120;
constexpr int ARTIFICIAL_DELAY_MS = 10000;

int main() {
    audio::audio_engine engine;

    if (!engine.start()) {
        std::cerr << "ERRO: Falha ao iniciar audio_engine!" << std::endl;
        return 1;
    }

    std::deque<std::pair<steady_clock::time_point, Packet>> delay_buffer;
    auto start_time = steady_clock::now();

    while (engine.is_running() && (steady_clock::now() - start_time <
                                   seconds(TEST_DURATION_SECONDS))) {
        Packet current_packet;
        auto current_time = steady_clock::now();

        if (engine.get_next_outgoing_packet(current_packet)) {
            delay_buffer.push_back({current_time, std::move(current_packet)});
        }

        while (!delay_buffer.empty() &&
               (current_time - delay_buffer.front().first >=
                milliseconds(ARTIFICIAL_DELAY_MS))) {
            engine.submit_incoming_packet(delay_buffer.front().second);
            delay_buffer.pop_front();
        }

        std::this_thread::sleep_for(milliseconds(1));
    }
    engine.stop();
    return 0;
}