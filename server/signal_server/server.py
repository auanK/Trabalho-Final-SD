import asyncio
import logging
from client_handler import handle_client

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

async def main():
    
    # 0.0.0.0 é um endereço IP especial. é uma instrução que significa: "Escute em TODAS as interfaces de rede que este computador possui."
    server_host = '0.0.0.0'
    server_port = 8888      
    
    # Servidor é criado e preparado aqui(n iniciado)
    # 'Server' não é o socket; é um gerenciador de sockets. Ele armazena a função 
    # handle_client como o callback a ser usado quando uma nova conexão for aceita.
    server = await asyncio.start_server(
        handle_client, server_host, server_port
    )
    
    addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)
    logging.info(f"Servidor de Sinalização iniciado em {addrs}")
    
    # server.serve_forever() é um método do objeto asyncio.Server. Ele diz ao loop de eventos do asyncio
    # para começar a monitorar os sockets que foram criados e vinculados para conexões de entrada.
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Servidor desligado manualmente.")


# O asyncio pega a função handle_client e a armazena.
# Um Evento Ocorre: Um cliente se conecta à porta 8888. asyncio eeage ao Evento aceitando a conexão 
# Ele cria dois objetos de baixo nível para aquela conexão específica: o reader (para ler dados) e o writer (para escrever dados).
# O asyncio executa a função  handle_client passando os argumentos que ele acabou de criar