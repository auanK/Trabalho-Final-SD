#include <atomic>
#include <chrono>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <limits>
#include <string>
#include <thread>
#include <vector>

#include "audio_constants.h"
#include "audio_engine.h"
#include "platform_includes.h"

enum class PacketType : uint8_t { AUDIO_OPUS = 0x01, CONTROL_JSON = 0x02 };
const std::vector<char> STATIC_MAGIC_TOKEN = {
    (char)0xDE, (char)0xAD, (char)0xBE, (char)0xEF,
    (char)0xCA, (char)0xFE, (char)0xBA, (char)0xBE};
constexpr int SESSION_ID_LEN = 16;
constexpr int TOKEN_LEN = 8;
constexpr int PACKET_TYPE_LEN = sizeof(PacketType);
constexpr int HEADER_LEN = SESSION_ID_LEN + TOKEN_LEN;
constexpr int PACKET_HEADER_LEN_FULL = HEADER_LEN + PACKET_TYPE_LEN;
constexpr int MAX_PACKET_SIZE = 1500;
constexpr int SEND_LOOP_SLEEP_MS = 10;

std::vector<char> pad_session_id(const std::string& id_str) {
    std::vector<char> session_id(SESSION_ID_LEN, 0);
    std::copy(id_str.begin(),
              id_str.begin() + std::min(id_str.size(), (size_t)SESSION_ID_LEN),
              session_id.begin());
    return session_id;
}

void send_thread_func(SOCKET client_socket, sockaddr_in server_addr,
                      audio::audio_engine& engine,
                      const std::vector<char>& session_id_bytes,
                      const std::vector<char>& magic_token_bytes,
                      std::atomic<bool>& stop_signal) {
    std::vector<char> send_buffer;
    send_buffer.reserve(MAX_PACKET_SIZE);
    while (!stop_signal.load()) {
        audio::Packet packet_out;
        if (engine.get_next_outgoing_packet(packet_out)) {
            send_buffer.clear();
            send_buffer.insert(send_buffer.end(), session_id_bytes.begin(),
                               session_id_bytes.end());
            send_buffer.insert(send_buffer.end(), magic_token_bytes.begin(),
                               magic_token_bytes.end());
            send_buffer.push_back(static_cast<char>(PacketType::AUDIO_OPUS));
            send_buffer.insert(send_buffer.end(), packet_out.data.begin(),
                               packet_out.data.end());
            sendto(client_socket, send_buffer.data(), send_buffer.size(), 0,
                   (SOCKADDR*)&server_addr, sizeof(server_addr));
        }
        std::this_thread::sleep_for(
            std::chrono::milliseconds(SEND_LOOP_SLEEP_MS));
    }
}

void recv_thread_func(SOCKET client_socket, sockaddr_in server_addr,
                      audio::audio_engine& engine,
                      const std::vector<char>& magic_token_bytes,
                      std::atomic<bool>& stop_signal) {
    char recv_buffer[MAX_PACKET_SIZE];
    sockaddr_in sender_addr;
    int sender_addr_len = sizeof(sender_addr);
    while (!stop_signal.load()) {
        int bytes_recvd =
            recvfrom(client_socket, recv_buffer, MAX_PACKET_SIZE, 0,
                     (SOCKADDR*)&sender_addr, &sender_addr_len);
        if (bytes_recvd == SOCKET_ERROR) {
            if (stop_signal.load()) break;
            std::cerr << "ERRO: recvfrom() falhou: " << WSAGetLastError()
                      << std::endl;
            break;
        }

        if (sender_addr.sin_addr.s_addr != server_addr.sin_addr.s_addr ||
            sender_addr.sin_port != server_addr.sin_port ||
            bytes_recvd <= PACKET_HEADER_LEN_FULL ||
            memcmp(recv_buffer + SESSION_ID_LEN, magic_token_bytes.data(),
                   TOKEN_LEN) != 0) {
            continue;
        }

        PacketType packet_type =
            static_cast<PacketType>(recv_buffer[HEADER_LEN]);
        char* payload_start = recv_buffer + PACKET_HEADER_LEN_FULL;
        int payload_size = bytes_recvd - PACKET_HEADER_LEN_FULL;

        if (payload_size > 0 && packet_type == PacketType::AUDIO_OPUS) {
            engine.submit_incoming_packet({std::vector<unsigned char>(
                payload_start, payload_start + payload_size)});
        }
    }
}

int main() {
    const char* server_ip_str = "127.0.0.1";
    int server_port = 9000;
    std::string session_id_str = "teste2";
    std::string my_info_json = "{\"type\":\"join\"}";

    std::vector<char> session_id_bytes = pad_session_id(session_id_str);
    std::vector<char> magic_token_bytes = STATIC_MAGIC_TOKEN;

    WSADATA wsa_data;
    if (WSAStartup(MAKEWORD(2, 2), &wsa_data) != 0) {
        std::cerr << "ERRO: WSAStartup" << std::endl;
        return 1;
    }

    SOCKET client_socket = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (client_socket == INVALID_SOCKET) {
        std::cerr << "ERRO: socket()" << std::endl;
        WSACleanup();
        return 1;
    }
    DWORD dwBytesReturned = 0;
    BOOL bNewBehavior = FALSE;
    WSAIoctl(client_socket, SIO_UDP_CONNRESET, &bNewBehavior,
             sizeof(bNewBehavior), NULL, 0, &dwBytesReturned, NULL, NULL);

    sockaddr_in server_addr{};
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(server_port);
    inet_pton(AF_INET, server_ip_str, &server_addr.sin_addr);

    std::vector<char> registration_packet;
    registration_packet.insert(registration_packet.end(),
                               session_id_bytes.begin(),
                               session_id_bytes.end());
    registration_packet.insert(registration_packet.end(),
                               magic_token_bytes.begin(),
                               magic_token_bytes.end());
    registration_packet.push_back(static_cast<char>(PacketType::CONTROL_JSON));
    registration_packet.insert(registration_packet.end(), my_info_json.begin(),
                               my_info_json.end());
    sendto(client_socket, registration_packet.data(),
           registration_packet.size(), 0, (SOCKADDR*)&server_addr,
           sizeof(server_addr));

    audio::audio_engine engine;
    if (!engine.start()) {
        std::cerr << "ERRO: audio_engine.start()" << std::endl;
        closesocket(client_socket);
        WSACleanup();
        return 1;
    }

    std::atomic<bool> stop_signal(false);
    std::thread sender_thread(send_thread_func, client_socket, server_addr,
                              std::ref(engine), std::ref(session_id_bytes),
                              std::ref(magic_token_bytes),
                              std::ref(stop_signal));
    std::thread receiver_thread(recv_thread_func, client_socket, server_addr,
                                std::ref(engine), std::ref(magic_token_bytes),
                                std::ref(stop_signal));

    std::cout << "Sessao: " << session_id_str << ". Pressione ENTER para parar."
              << std::endl;
    std::cin.get();

    std::cout << "Parando..." << std::endl;
    stop_signal.store(true);
    engine.stop();
    closesocket(client_socket);

    sender_thread.join();
    receiver_thread.join();
    WSACleanup();

    return 0;
}