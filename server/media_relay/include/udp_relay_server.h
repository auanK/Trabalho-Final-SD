#ifndef UDP_RELAY_SERVER_H
#define UDP_RELAY_SERVER_H

#include <atomic>
#include <chrono>
#include <cstdint>
#include <map>
#include <string>
#include <vector>

#include "platform_includes.h"

namespace relay {

constexpr int SESSION_TIMEOUT_SECONDS = 300;
constexpr int CLEANUP_PACKET_INTERVAL = 1000;

struct Session {
    std::map<std::string, sockaddr_in> participants;
    std::chrono::steady_clock::time_point last_seen;
};

constexpr int MAX_PACKET_SIZE = 1500;
constexpr int SESSION_ID_LEN = 16;
constexpr int TOKEN_LEN = 8;
constexpr int HEADER_LEN = SESSION_ID_LEN + TOKEN_LEN;

class udp_relay_server {
   private:
    uint16_t _port;
    std::atomic<bool> _is_running{false};
    SOCKET _socket;
    std::map<std::string, Session> _sessions;
    std::vector<char> _magic_token;
    int _packet_counter{0};

    bool init_winsock();
    bool create_and_bind_socket();
    void cleanup();

    std::vector<sockaddr_in> register_and_get_peers(
        const std::string& session_id, const sockaddr_in& sender_addr);
    std::string endpoint_to_string(const sockaddr_in& addr);
    bool is_token_valid(const char* buffer) const;
    void cleanup_inactive_sessions();

   public:
    explicit udp_relay_server(uint16_t port);
    ~udp_relay_server();

    udp_relay_server(const udp_relay_server&) = delete;
    udp_relay_server& operator=(const udp_relay_server&) = delete;
    udp_relay_server(udp_relay_server&&) = delete;
    udp_relay_server& operator=(udp_relay_server&&) = delete;

    bool run();
    void stop();
    bool is_running() const;
};

}  // namespace relay

#endif