#include <iostream>

#include "udp_relay_server.h"

// Ponteiro global para o servidor UDP Relay
relay::udp_relay_server* g_server = nullptr;

int main() {
    constexpr uint16_t RELAY_PORT = 9000;

    // Cria a instância do servidor UDP e atribui ao ponteiro global
    relay::udp_relay_server server(RELAY_PORT);
    g_server = &server;
    
    std::cout << "Pressione Ctrl+C para parar." << std::endl;

    // Inicia o servidor UDP Relay, essa função bloqueia até o servidor ser parado
    if (!server.run()) {
        std::cerr << "ERRO: Falha ao iniciar o servidor." << std::endl;
        return 1;
    }
    std::cout << "Servidor parado." << std::endl;
    return 0;
}