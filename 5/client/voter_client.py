import asyncio
import json
import logging
import socket
import struct
import sys
from client import client_config as config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - VOTER - %(message)s')

class MulticastListenerProtocol(asyncio.DatagramProtocol):
    def connection_made(self, transport):
        logging.info("Multicast listener iniciado.")
        self.transport = transport

    def datagram_received(self, data, addr):
        message = data.decode('utf-8')
        logging.info(f"Nota recebida: {message}") 
        print(f"\n<<< NOTA: {message} >>>\nEnter command: ", end='', flush=True)

    def error_received(self, exc):
        logging.error(f'Multicast listener erro: {exc}')

    def connection_lost(self, exc):
        logging.info('Multicast listener encerrado.')

async def start_multicast_listener():
    loop = asyncio.get_running_loop()
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    bind_addr = '0.0.0.0' if sys.platform == "win32" else ''
    sock.bind((bind_addr, config.MULTICAST_PORT)) 

    group = socket.inet_aton(config.MULTICAST_GROUP)
    mreq = struct.pack('4sL', group, socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    
    logging.info(f"Ouvindo grupo multicast {config.MULTICAST_GROUP} na porta {config.MULTICAST_PORT}")

async def send_tcp_request(reader, writer, command, payload=None):
    request = {"command": command, "payload": payload or {}}
    message = json.dumps(request) + '\n'
    writer.write(message.encode('utf-8'))
    await writer.drain()
    
    try:
        response_data = await reader.readuntil(b'\n')
        response = json.loads(response_data.decode('utf-8').strip())
        return response
    except asyncio.IncompleteReadError:
        logging.error("Conexão fechada pelo servidor.")
        return None
    except json.JSONDecodeError:
        logging.error("Recebido JSON inválido do servidor.")
        return None

async def voter_main():
    reader, writer = None, None
    try:
        reader, writer = await asyncio.open_connection(config.SERVER_HOST, config.TCP_PORT)
        logging.info(f"Conectado ao servidor {config.SERVER_HOST}:{config.TCP_PORT}")

        while True:
            username = await asyncio.to_thread(input, "Enter username: ")
            password = await asyncio.to_thread(input, "Enter password: ")
            response = await send_tcp_request(reader, writer, "LOGIN", {"username": username, "password": password})
            logging.info(f"Server response: {response}")
            if response and response.get("status") == "OK":
                if response.get("role") == "voter":
                    logging.info("Login successful as voter.")
                    break
                else:
                    logging.error("Login successful, but you are not a voter. Exiting.")
                    return 
            else:
                logging.error(f"Login failed: {response.get('message', 'Unknown error')}")
                try_again = await asyncio.to_thread(input, "Try again? (y/n): ")
                if try_again.lower() != 'y':
                    return 

        multicast_task = asyncio.create_task(start_multicast_listener())

        while True:
            print("\nAvailable commands: list, vote [candidate_name], results, quit")
            try:
                action_input = await asyncio.to_thread(input, "Enter command: ") 
                parts = action_input.strip().split(maxsplit=1)
                command = parts[0].lower() if parts else ""
                
                if command == "list":
                    response = await send_tcp_request(reader, writer, "GET_CANDIDATES")
                    if response and response.get("status") == "OK":
                        print("\n--- Candidates ---")
                        for i, candidate in enumerate(response.get("candidates", [])):
                            print(f"{i+1}. {candidate}")
                        print(f"Voting Active: {'Yes' if response.get('voting_active') else 'No'}")
                        print("--------------------")
                    else:
                        logging.error(f"Failed to get candidates: {response.get('message', 'Unknown error')}")

                elif command == "vote":
                    if len(parts) > 1:
                        candidate_name = parts[1]
                        response = await send_tcp_request(reader, writer, "VOTE", {"candidate": candidate_name})
                        print(f"Server: {response.get('message', 'No message')}")
                    else:
                        print("Usage: vote <candidate_name>")
                
                elif command == "results":
                    response = await send_tcp_request(reader, writer, "GET_RESULTS")
                    if response and response.get("status") == "OK":
                        print("\n--- Resultados da Última Votação ---")
                        print(json.dumps(response.get("results", {}), indent=2))
                        print("---------------------------------")
                    else:
                        print(f"Server: {response.get('message', 'Erro desconhecido')}")

                elif command == "quit":
                    logging.info("Disconnecting...")
                    break 

                else:
                    print(f"Unknown command: '{command}'")

            except EOFError: 
                logging.info("Disconnecting...")
                break
            except KeyboardInterrupt: 
                logging.info("Disconnecting...")
                break

    except ConnectionRefusedError:
        logging.error(f"Connection refused. Is the server running at {config.SERVER_HOST}:{config.TCP_PORT}?")
    except Exception as e:
        logging.error(f"An error occurred: {e}")
    finally:
        if 'multicast_task' in locals():
            multicast_task.cancel() 
        if writer:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception: pass
        logging.info("Voter client finished.")

if __name__ == "__main__":
    try:
        asyncio.run(voter_main())
    except KeyboardInterrupt:
        pass