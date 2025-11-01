import asyncio
import json
import logging
from client import client_config as config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - ADMIN - %(message)s')

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
        logging.error("Connection closed by server unexpectedly.")
        return None
    except json.JSONDecodeError:
        logging.error("Received invalid JSON from server.")
        return None

async def admin_main():
    reader, writer = None, None
    try:
        reader, writer = await asyncio.open_connection(config.SERVER_HOST, config.TCP_PORT)
        logging.info(f"Connected to server {config.SERVER_HOST}:{config.TCP_PORT}")

        while True:
            username = await asyncio.to_thread(input, "Enter admin username: ")
            password = await asyncio.to_thread(input, "Enter admin password: ")
            response = await send_tcp_request(reader, writer, "LOGIN", {"username": username, "password": password})
            logging.info(f"Server response: {response}")
            if response and response.get("status") == "OK":
                if response.get("role") == "admin":
                    logging.info("Login successful as admin.")
                    break
                else:
                    logging.error("Login successful, but you are not an admin. Exiting.")
                    return 
            else:
                logging.error(f"Login failed: {response.get('message', 'Unknown error')}")
                try_again = await asyncio.to_thread(input, "Try again? (y/n): ")
                if try_again.lower() != 'y':
                    return 

        while True:
            print("\nAdmin commands: list, add [name], remove [name], note [message], start, results, quit")
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

                elif command == "add":
                    if len(parts) > 1:
                        candidate_name = parts[1]
                        response = await send_tcp_request(reader, writer, "ADD_CANDIDATE", {"candidate_name": candidate_name})
                        print(f"Server: {response.get('message', 'No message')}")
                    else:
                        print("Usage: add <candidate_name>")

                elif command == "remove":
                    if len(parts) > 1:
                        candidate_name = parts[1]
                        response = await send_tcp_request(reader, writer, "REMOVE_CANDIDATE", {"candidate_name": candidate_name})
                        print(f"Server: {response.get('message', 'No message')}")
                    else:
                        print("Usage: remove <candidate_name>")

                elif command == "note":
                    if len(parts) > 1:
                        note_message = parts[1]
                        response = await send_tcp_request(reader, writer, "SEND_NOTE", {"note": note_message})
                        print(f"Server: {response.get('message', 'No message')}")
                    else:
                        print("Usage: note <message_content>")

                elif command == "start":
                    confirm = await asyncio.to_thread(input, "Tem certeza que deseja iniciar a votação? (y/n): ")
                    if confirm.lower() == 'y':
                        response = await send_tcp_request(reader, writer, "START_VOTING")
                        print(f"Server: {response.get('message', 'No message')}")
                    else:
                        print("Início da votação cancelado.")
                
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
        if writer:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception: pass
        logging.info("Admin client finished.")

if __name__ == "__main__":
    try:
        asyncio.run(admin_main())
    except KeyboardInterrupt:
        pass