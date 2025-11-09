#include "udp_relay_server.h"

#include <cstring>
#include <iostream>

namespace relay {

// Token mágico estático de 8 bytes, os pacotes que não corresponderem a este
// token serão descartados
const std::vector<char> STATIC_MAGIC_TOKEN = {
    (char)0xDE, (char)0xAD, (char)0xBE, (char)0xEF,
    (char)0xCA, (char)0xFE, (char)0xBA, (char)0xBE};

// Construtor
udp_relay_server::udp_relay_server(uint16_t port)
    : _port(port), _socket(INVALID_SOCKET), _magic_token(STATIC_MAGIC_TOKEN) {}

// Destrutor
udp_relay_server::~udp_relay_server() {
    stop();
    cleanup();
}

// Inicia o servidor, este método é bloqueante e contém o loop principal que
// chama recvfrom() e encaminha os pacotes, só sai quando stop() é chamado
bool udp_relay_server::run() {
    if (!init_winsock()) {
        return false;
    }
    if (!create_and_bind_socket()) {
        WSACleanup();
        return false;
    }

    std::cout << "Servidor de Relay escutando na porta " << _port << "..."
              << std::endl;

    // Buffer para receber pacotes
    char recv_buffer[MAX_PACKET_SIZE];

    // Endereço do remetente
    sockaddr_in sender_addr;
    int sender_addr_len = sizeof(sender_addr);

    _is_running.store(true);

    // Loop principal
    while (_is_running.load()) {
        // Espere por um pacote UDP, bloqueante
        int bytes_recvd = recvfrom(_socket, recv_buffer, MAX_PACKET_SIZE, 0,
                                   (SOCKADDR*)&sender_addr, &sender_addr_len);

        // Limpeza periódica de sessões
        _packet_counter++;
        if (_packet_counter > CLEANUP_PACKET_INTERVAL) {
            cleanup_inactive_sessions();
            _packet_counter = 0;
        }

        // Tratar erros de recvfrom
        if (bytes_recvd == SOCKET_ERROR) {
            if (!_is_running.load()) {
                break;
            }
            std::cerr << "AVISO: recvfrom() falhou (erro: " << WSAGetLastError()
                      << "), continuando..." << std::endl;
            continue;
        }

        // Validação de pacotes
        if (bytes_recvd <= HEADER_LEN || (!is_token_valid(recv_buffer))) {
            continue;
        }

        // Extrair ID da sessão do cabeçalho do pacote (Primeiros 16 bytes)
        std::string session_id(recv_buffer, recv_buffer + SESSION_ID_LEN);

        // Encontra a sessão, adiciona o remetente se necessário, e obtém a
        // lista de participantes para encaminhar
        std::vector<sockaddr_in> peers =
            register_and_get_peers(session_id, sender_addr);

        // Encaminha o pacote para todos os participantes, exceto o remetente
        for (const auto& peer_addr : peers) {
            sendto(_socket, recv_buffer, bytes_recvd, 0,
                   (const SOCKADDR*)&peer_addr, sizeof(peer_addr));
        }
    }

    // O loop terminou
    cleanup();
    return true;
}

// Sinaliza o servidor para parar
void udp_relay_server::stop() {
    // Usa compare_exchange para garantir que a parada só ocorra uma vez
    bool expected = true;
    if (_is_running.compare_exchange_strong(expected, false)) {
        if (_socket != INVALID_SOCKET) {
            closesocket(_socket);
            _socket = INVALID_SOCKET;
        }
    }
}

// Verifica se o servidor está em execução
bool udp_relay_server::is_running() const {
    return _is_running.load(std::memory_order_relaxed);
}

// Inicializa o Winsock
bool udp_relay_server::init_winsock() {
    WSADATA wsa_data;
    int result = WSAStartup(MAKEWORD(2, 2), &wsa_data);
    if (result != 0) {
        std::cerr << "ERRO: WSAStartup falhou: " << result << std::endl;
        return false;
    }
    return true;
}

// Cria o socket UDP, aplica o SIO_UDP_CONNRESET e vincula à porta
bool udp_relay_server::create_and_bind_socket() {
    _socket = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (_socket == INVALID_SOCKET) {
        std::cerr << "ERRO: socket() falhou: " << WSAGetLastError()
                  << std::endl;
        return false;
    }

    // Desabilita o erro WSAECONNRESET para sockets UDP
    DWORD dwBytesReturned = 0;
    BOOL bNewBehavior = FALSE;
    WSAIoctl(_socket, SIO_UDP_CONNRESET, &bNewBehavior, sizeof(bNewBehavior),
             NULL, 0, &dwBytesReturned, NULL, NULL);

    // Configura o endereço para bind
    sockaddr_in server_addr{};
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = INADDR_ANY;
    server_addr.sin_port = htons(_port);

    // Vincula o socket à porta
    if (bind(_socket, (SOCKADDR*)&server_addr, sizeof(server_addr)) ==
        SOCKET_ERROR) {
        std::cerr << "ERRO: bind() falhou: " << WSAGetLastError() << std::endl;
        closesocket(_socket);
        _socket = INVALID_SOCKET;
        return false;
    }
    return true;
}

// Fecha o socket e limpa o Winsock
void udp_relay_server::cleanup() {
    if (_socket != INVALID_SOCKET) {
        closesocket(_socket);
        _socket = INVALID_SOCKET;
    }
    WSACleanup();
}

// Converte um endereço de socket em uma string única.
std::string udp_relay_server::endpoint_to_string(const sockaddr_in& addr) {
    char ip_str[INET_ADDRSTRLEN];
    inet_ntop(AF_INET, &(addr.sin_addr), ip_str, INET_ADDRSTRLEN);
    return std::string(ip_str) + ":" + std::to_string(ntohs(addr.sin_port));
}

// Registra o remetente na sessão e retorna a lista de peers
std::vector<sockaddr_in> udp_relay_server::register_and_get_peers(
    const std::string& session_id, const sockaddr_in& sender_addr) {
    // Converte o endpoint do remetente para string
    std::string sender_key = endpoint_to_string(sender_addr);

    // Obtém ou cria a sessão caso não exista
    Session& session = _sessions[session_id];

    // Atualiza o timestamp da última atividade
    session.last_seen = std::chrono::steady_clock::now();

    // Adiciona o remetente à lista de participantes se ainda não estiver
    session.participants.try_emplace(sender_key, sender_addr);

    // Monta a lista de todos os outros participantes para encaminhar o pacote
    std::vector<sockaddr_in> peers;
    for (const auto& [key, participant_addr] : session.participants) {
        if (key != sender_key) {
            peers.push_back(participant_addr);
        }
    }
    return peers;
}

// Verifica se os 8 bytes do token no pacote correspondem ao token mágico
bool udp_relay_server::is_token_valid(const char* buffer) const {
    return memcmp(buffer + SESSION_ID_LEN, _magic_token.data(), TOKEN_LEN) == 0;
}

// Itera por todas as sessÕes e remove as que expiraram
void udp_relay_server::cleanup_inactive_sessions() {
    auto now = std::chrono::steady_clock::now();
    int cleaned_count = 0;

    for (auto it = _sessions.begin(); it != _sessions.end();) {
        auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(
                           now - it->second.last_seen)
                           .count();

        if (elapsed > SESSION_TIMEOUT_SECONDS) {
            it = _sessions.erase(it);
            cleaned_count++;
        } else {
            ++it;
        }
    }

    if (cleaned_count > 0) {
        std::cout << "[Limpeza]: Removidas " << cleaned_count
                  << " sessoes inativas."
                  << " Sessoes ativas: " << _sessions.size() << std::endl;
    }
}

}  // namespace relay