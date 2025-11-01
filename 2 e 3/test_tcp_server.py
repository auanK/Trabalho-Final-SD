# Teste Q3.d
import socket
from stream_classes import UserRecordInputStream

HOST = '127.0.0.1'
PORT = 9999

# Teste Q3.d: Inicia um servidor TCP que lê objetos de um UserRecordInputStream.
def start_server():
    print(f"Teste 3.d: Servidor (Leitor TCP)")
    print(f"Iniciando servidor em {HOST}:{PORT}...")
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        
        print("Aguardando conexão do cliente...")
        conn, addr = s.accept()
        
        with conn:
            print(f"[Servidor] Cliente conectado: {addr}")
            
            source_stream = conn.makefile('rb')
            in_stream = UserRecordInputStream(source_stream=source_stream)
            
            print("[Servidor] Lendo todos os registros do cliente...")
            records_read = in_stream.read_all_records()
            
            print(f"\n[Servidor] Registros lidos ({len(records_read)}):")
            for rec in records_read:
                print(f"  -> {rec}")
            
            if len(records_read) == 2 and records_read[0].nickname == "user1":
                print("[Servidor] Verificação: Sucesso!")
            else:
                print("[Servidor] Verificação: Falhou!")
                
    print("[Servidor] Conexão fechada. Servidor desligado.")

if __name__ == "__main__":
    start_server()