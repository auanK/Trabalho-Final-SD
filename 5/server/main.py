import socket
import threading
import logging
import time
import server.data_manager as dm
from server.tcp_handler import handle_tcp_client
from typing import Optional

SERVER_HOST = '0.0.0.0'
TCP_PORT = 8888

MAX_PREPARATION_TIME_SECONDS = 300
VOTING_DURATION_SECONDS = 15

G_PREPARATION_TIMER: Optional[threading.Timer] = None

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def voting_timer():
    logging.info(f"Iniciando o período de votação: {VOTING_DURATION_SECONDS} segundos.")
    if dm.start_voting():
        logging.info("Votação INICIADA.")
        
        time.sleep(VOTING_DURATION_SECONDS)
        
        if dm.stop_voting():
            logging.info("Votação encerrada.")
            results = dm.tally_votes()
            logging.info(f"Resultados finais: {results}")
        else:
            logging.warning("Falha ao parar votação")
    else:
        logging.warning("Falha ao iniciar votação. Já está ativa?")

def auto_start_voting():
    logging.info(f"Tempo de preparação ({MAX_PREPARATION_TIME_SECONDS}s) esgotado.")
    if not dm.is_voting_active():
        logging.info("Iniciando votação automaticamente...")
        timer_thread = threading.Thread(target=voting_timer, daemon=True)
        timer_thread.start()
    else:
        logging.info("Votação já foi iniciada manualmente. Timer automático ignorado.")


def main():
    global G_PREPARATION_TIMER
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind((SERVER_HOST, TCP_PORT))
        server_socket.listen(5) 
        logging.info(f"TCP Server (Multi-threaded) escutando em {SERVER_HOST}:{TCP_PORT}")
        
        logging.info(f"Servidor em modo PREPARAÇÃO. Votação iniciará automaticamente em {MAX_PREPARATION_TIME_SECONDS} segundos.")
        G_PREPARATION_TIMER = threading.Timer(MAX_PREPARATION_TIME_SECONDS, auto_start_voting)
        G_PREPARATION_TIMER.start()

        while True:
            conn, addr = server_socket.accept()
            
            client_thread = threading.Thread(
                target=handle_tcp_client, 
                args=(conn, addr),
                daemon=True
            )
            client_thread.start()

    except OSError as e:
        logging.error(f"Falha ao iniciar o TCP Server {TCP_PORT}: {e}")
    except KeyboardInterrupt:
        logging.info("Servidor encerrando (Ctrl+C)...")
    finally:
        if G_PREPARATION_TIMER:
            G_PREPARATION_TIMER.cancel()
        server_socket.close()
        logging.info("Socket do servidor fechado.")

if __name__ == "__main__":
    main()