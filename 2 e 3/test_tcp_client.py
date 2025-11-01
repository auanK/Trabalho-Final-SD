# Teste Q2.b.iii
import socket
import time
from user_record import UserRecord
from stream_classes import UserRecordOutputStream

HOST = '127.0.0.1'
PORT = 9999

# Dados de exemplo
records_to_write = [
    UserRecord(nickname="user1", name="Mirelle", description="Cliente 1"),
    UserRecord(nickname="user2", name="Kauan", description="Cliente 2"),
]

# Teste 2.b.iii: Inicia um cliente TCP que usa UserRecordOutputStream para enviar dados para um servidor remoto.
def start_client():
    print(f"Teste 2.b.iii: Cliente (Escritor TCP) ")
    time.sleep(1)
    
    print(f"[Cliente] Conectando ao servidor em {HOST}:{PORT}...")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            dest_stream = s.makefile('wb')
            
            num_to_send = len(records_to_write)
            print(f"[Cliente] Enviando {num_to_send} registros para o servidor...")
            
            out_stream = UserRecordOutputStream(
                records_array=records_to_write,
                num_objects_to_send=num_to_send,
                dest_stream=dest_stream
            )
            
            bytes_written = out_stream.write()
            print(f"[Cliente] Total de bytes enviados: {bytes_written}")
            
    except ConnectionRefusedError:
        print(f"[Cliente] Erro: Conexão recusada. Você iniciou o 'test_tcp_server.py'?")
    except Exception as e:
        print(f"[Cliente] Erro: {e}")
    
    print("[Cliente] Conexão fechada.")

if __name__ == "__main__":
    start_client()