import socket
import threading
from typing import BinaryIO

from ..models.UserRecord import UserRecord 
from .custom_streams import UserRecordInputStream, UserRecordOutputStream

# Dados de Exemplo
records_to_send = [
    UserRecord(nickname="tcp_client", name="Cliente TCP", description="Enviando via Socket"),
    UserRecord(nickname="net_stream", name="Network Stream", description="Objeto de teste"),
]
num_to_send = len(records_to_send)
HOST = '127.0.0.1'
PORT = 9998 # Porta diferente do servidor principal
server_ready = threading.Event() # Para sincronizar cliente e servidor

def server_logic():
    read_records = []
    print("[Servidor TCP] Iniciando...")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((HOST, PORT))
            s.listen(1)
            print(f"[Servidor TCP] Escutando em {HOST}:{PORT}")
            server_ready.set() # Sinaliza que o servidor está pronto
            conn, addr = s.accept() # Espera conexão
            with conn:
                print(f"[Servidor TCP] Cliente conectado: {addr}")
                # Usa makefile para obter um stream binário do socket
                conn_stream: BinaryIO = conn.makefile('rb')
                input_stream = UserRecordInputStream(conn_stream) # Passa o stream binário
                print("[Servidor TCP] Lendo registros do cliente...")
                read_records = input_stream.read_all_records()
                print("[Servidor TCP] Leitura concluída.")
    except Exception as e:
        print(f"[Servidor TCP] Erro: {e}")
    finally:
        print("\n[Servidor TCP] Registros Recebidos:")
        if read_records:
            for i, record in enumerate(read_records): print(f"  {i+1}: {record}")
        else: print("  Nenhum registro recebido.")
        print("[Servidor TCP] Encerrado.")

def client_logic():
    print("[Cliente TCP] Iniciando...")
    server_ready.wait(timeout=5) # Espera o servidor sinalizar que está pronto
    if not server_ready.is_set():
         print("[Cliente TCP] Erro: Timeout esperando o servidor iniciar.")
         return
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            print(f"[Cliente TCP] Conectando a {HOST}:{PORT}...")
            s.connect((HOST, PORT))
            print("[Cliente TCP] Conectado.")
            conn_stream: BinaryIO = s.makefile('wb')
            output_stream = UserRecordOutputStream(records_to_send, num_to_send, conn_stream) # Passa o stream binário
            print(f"[Cliente TCP] Enviando {num_to_send} registros...")
            bytes_written = output_stream.write()
            print(f"[Cliente TCP] Envio concluído: {bytes_written} bytes.")
            conn_stream.close() # Fecha o stream para sinalizar fim para o servidor
            print("[Cliente TCP] Conexão fechada.")
    except Exception as e:
        print(f"[Cliente TCP] Erro: {e}")
    finally:
        print("[Cliente TCP] Encerrado.")

print("--- Teste TCP ---")
server_thread = threading.Thread(target=server_logic, daemon=True)
server_thread.start()

client_logic()

print("\n--- Fim do Teste TCP ---")