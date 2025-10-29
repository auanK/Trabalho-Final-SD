import logging
import socket
import threading
from client_handler import handle_client 

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(threadName)s - %(message)s')

def main():
    server_host = '0.0.0.0'
    server_port = 8888      
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # Criando socket TCP/IP
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Permite reiniciar o server com a mesma porta 

    try:
        server_socket.bind((server_host, server_port)) # ligando o socket a porta e ip
        
        server_socket.listen() # modo de escuta

        logging.info(f"Servidor de Sinalização iniciado em {server_host}:{server_port}")

        while True: # loop para aceitar conexões
            socket_cli, addr = server_socket.accept() # accept é bloqueante, só continua quando um novo cliente se conecta.
            # socket_cli = Este é o novo socket do cliente atual. 
            # socket_cli = É o endereço do cliente 
            
            # a thread principal chama outra thread pra lidar com o cliente (client_handle)
            client_thread = threading.Thread(
                target=handle_client, 
                args=(socket_cli, addr), 
                daemon=True,
                name=f"Client-{addr[0]}:{addr[1]}" # da um nome a tread
            )
            client_thread.start()

    except KeyboardInterrupt:
        logging.info("Servidor desligado manualmente.")
    except Exception as e:
        logging.error(f"Erro fatal no servidor: {e}", exc_info=True)
    finally:
        logging.info("Fechando socket do servidor.")
        server_socket.close()

if __name__ == "__main__":
    main()