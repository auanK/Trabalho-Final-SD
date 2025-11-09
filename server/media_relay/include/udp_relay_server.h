#ifndef UDP_RELAY_SERVER_H
#define UDP_RELAY_SERVER_H

#include <atomic>
#include <chrono>
#include <cstdint>
#include <map>
#include <string>
#include <vector>

// Includes específicos do Windows, devem ser incluídos nesta ordem
// 1
#include <WinSock2.h>
// 2
#include <Windows.h>
// 3.
#include <WS2tcpip.h>
// 4
#include <Mstcpip.h>

// Definição de SIO_UDP_CONNRESET, configuração específica do Windows para
// sockets UDP, onde ela impede que o socket falhe quando recebe um pacote ICMP
// "Port Unreachable".
#ifndef SIO_UDP_CONNRESET
#define SIO_UDP_CONNRESET _WSAIOW(IOC_VENDOR, 12)
#endif

namespace relay {

// Tempo máximo de inatividade de uma sessão em segundos
constexpr int SESSION_TIMEOUT_SECONDS = 300;

// Frequência de limpeza de sessões inativas a cada N pacotes recebidos
constexpr int CLEANUP_PACKET_INTERVAL = 1000;

// Struct para armazenar informações da sessão
struct Session {
    std::map<std::string, sockaddr_in> participants;
    std::chrono::steady_clock::time_point last_seen;
};

// Tamanho máximo do pacote UDP (evitando fragmentação)
constexpr int MAX_PACKET_SIZE = 1500;

// Tamanhos dos campos no cabeçalho do pacote
constexpr int SESSION_ID_LEN = 16;
constexpr int TOKEN_LEN = 8;
constexpr int HEADER_LEN = SESSION_ID_LEN + TOKEN_LEN;

// Gerencia o único socket UDP para encaminhar os pacotes de áudio entre os
// usuários
class udp_relay_server {
   private:
    uint16_t _port;                            // Porta onde o servidor escuta
    std::atomic<bool> _is_running{false};      // Estado do servidor
    SOCKET _socket;                            // Socket UDP
    std::map<std::string, Session> _sessions;  // Sessões ativas
    std::vector<char> _magic_token;            // Token mágico para validação
    int _packet_counter{0};  // Contador de pacotes para limpeza

    // Inicializa o Winsock
    bool init_winsock();

    // Cria e vincula o socket UDP
    bool create_and_bind_socket();

    // Fecha o socket e limpa o Winsock
    void cleanup();

    // Encontra/cria uma sessão, atualiza o timestamp e retorna uma lista de
    // todos os participantes para quem o pacote deve ser encaminhado
    std::vector<sockaddr_in> register_and_get_peers(
        const std::string& session_id, const sockaddr_in& sender_addr);

    // Converte um endpoint (sockaddr_in) para string
    std::string endpoint_to_string(const sockaddr_in& addr);

    // Verifica se os 8 bytes do token no pacote correspondem ao token mágico
    bool is_token_valid(const char* buffer) const;

    // Itera por `_sessions` e remove qualquer sessão que esteja inativa há mais
    // de SESSION_TIMEOUT_SECONDS
    void cleanup_inactive_sessions();

   public:
    // Construtor
    explicit udp_relay_server(uint16_t port);

    // Destrutor
    ~udp_relay_server();

    // Desabilita operações de cópia e movimentação
    udp_relay_server(const udp_relay_server&) = delete;
    udp_relay_server& operator=(const udp_relay_server&) = delete;
    udp_relay_server(udp_relay_server&&) = delete;
    udp_relay_server& operator=(udp_relay_server&&) = delete;

    // Inicia o servidor, este método é bloqueante e contém o loop principal que
    // chama recvfrom() e encaminha os pacotes
    bool run();

    // Para o servidor
    void stop();

    // Verifica se o servidor está em execução
    bool is_running() const;
};

}  // namespace relay

#endif