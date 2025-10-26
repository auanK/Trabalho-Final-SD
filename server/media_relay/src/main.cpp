#include <iostream>

#include "udp_relay_server.h"

relay::udp_relay_server* g_server = nullptr;

BOOL WINAPI console_handler(DWORD ctrl_type) {
    if (ctrl_type == CTRL_C_EVENT) {
        if (g_server && g_server->is_running()) {
            std::cout << "\nRecebido Ctrl+C, parando o servidor..."
                      << std::endl;
            g_server->stop();
        }
        return TRUE;
    }
    return FALSE;
}

int main() {
    constexpr uint16_t RELAY_PORT = 9000;

    relay::udp_relay_server server(RELAY_PORT);
    g_server = &server;

    if (!SetConsoleCtrlHandler(console_handler, TRUE)) {
        std::cerr << "ERRO: Nao foi possivel registrar o handler do console."
                  << std::endl;
        return 1;
    }

    std::cout << "Pressione Ctrl+C para parar." << std::endl;

    if (!server.run()) {
        std::cerr << "ERRO: Falha ao iniciar o servidor." << std::endl;
        return 1;
    }

    std::cout << "Servidor parado." << std::endl;
    return 0;
}