import socket
import json
import logging
import threading
from typing import Optional
import server.data_manager as dm
from server.multicast_utils import send_multicast_message

def send_json_response(conn: socket.socket, data: dict):
    try:
        response = json.dumps(data) + '\n'
        conn.sendall(response.encode('utf-8'))
    except (BrokenPipeError, ConnectionResetError):
        pass
    except Exception as e:
        logging.warning(f"Falha ao enviar msg: {e}")

def handle_tcp_client(conn: socket.socket, addr):
    import server.main 
    
    thread_name = threading.current_thread().name
    logging.info(f"Conexão TCP de {addr} (Thread: {thread_name})")
    
    authenticated_user: Optional[str] = None
    user_role: Optional[str] = None

    try:
        client_file = conn.makefile('rb') 

        while True:
            data = client_file.readline() 
            if not data:
                logging.info(f"Cliente {addr} desconectou.")
                break 
            
            message = data.decode('utf-8').strip()
            if not message: 
                continue
                
            logging.debug(f"Recebido de {addr}: {message}")
            
            try:
                request = json.loads(message)
                command = request.get("command")
                payload = request.get("payload", {})

                response = {"status": "ERROR", "message": "Invalid command or payload."}

                # --- Lógica de Comandos ---

                if command == "LOGIN":
                    username = payload.get("username")
                    password = payload.get("password")
                    role = dm.authenticate_user(username, password) 
                    if role:
                        authenticated_user = username
                        user_role = role
                        response = {"status": "OK", "message": "Login successful.", "role": role}
                        logging.info(f"User '{username}' ({role}) logado de {addr}")
                    else:
                        response = {"status": "ERROR", "message": "Invalid credentials."}
                        logging.warning(f"Login falhou '{username}' {addr}")
                    
                    send_json_response(conn, response)
                    if not authenticated_user: continue 

                elif not authenticated_user:
                    response = {"status": "ERROR", "message": "Authentication required."}
                    send_json_response(conn, response)
                    continue 

                elif command == "GET_CANDIDATES":
                    candidates = dm.get_candidates()
                    voting_active = dm.is_voting_active()
                    response = {"status": "OK", "candidates": candidates, "voting_active": voting_active}
                    send_json_response(conn, response)

                elif command == "VOTE":
                    if user_role == "voter":
                        candidate = payload.get("candidate")
                        success, msg = dm.register_vote(authenticated_user, candidate)
                        response = {"status": "OK" if success else "ERROR", "message": msg}
                    else:
                        response = {"status": "ERROR", "message": "Only voters can vote."}
                    send_json_response(conn, response)
                
                # === NOVO COMANDO ===
                elif command == "GET_RESULTS":
                    # Qualquer utilizador logado pode ver os resultados
                    response_data = dm.get_latest_results()
                    send_json_response(conn, response_data)

                # --- Comandos do Admin ---
                elif user_role != "admin":
                    response = {"status": "ERROR", "message": "Admin privileges required."}
                    send_json_response(conn, response)

                elif command == "ADD_CANDIDATE":
                    candidate_name = payload.get("candidate_name")
                    success, msg = dm.add_candidate(candidate_name)
                    response = {"status": "OK" if success else "ERROR", "message": msg}
                    send_json_response(conn, response)
                    if success:
                        send_multicast_message(f"Candidate '{candidate_name}' added by admin.")

                elif command == "REMOVE_CANDIDATE":
                    candidate_name = payload.get("candidate_name")
                    success, msg = dm.remove_candidate(candidate_name)
                    response = {"status": "OK" if success else "ERROR", "message": msg}
                    send_json_response(conn, response)
                    if success:
                        send_multicast_message(f"Candidate '{candidate_name}' removed by admin.")
                        
                elif command == "SEND_NOTE":
                    note = payload.get("note")
                    if note:
                        send_multicast_message(f"ADMIN NOTE: {note}")
                        response = {"status": "OK", "message": "Note sent via multicast."}
                    else:
                        response = {"status": "ERROR", "message": "Note content is missing."}
                    send_json_response(conn, response)

                elif command == "START_VOTING":
                    if dm.is_voting_active():
                        response = {"status": "ERROR", "message": "A votação já está em andamento."}
                    else:
                        if server.main.G_PREPARATION_TIMER:
                            server.main.G_PREPARATION_TIMER.cancel()
                            logging.info("Timer de preparação cancelado pelo admin.")
                        
                        timer_thread = threading.Thread(target=server.main.voting_timer, daemon=True)
                        timer_thread.start()
                        
                        response = {"status": "OK", "message": f"Votação iniciada manually. Duração: {server.main.VOTING_DURATION_SECONDS}s"}
                        logging.info(f"Admin '{authenticated_user}' iniciou a votação.")
                    send_json_response(conn, response)

                else:
                    response = {"status": "ERROR", "message": f"Unknown command '{command}'."}
                    send_json_response(conn, response)

            except json.JSONDecodeError:
                logging.warning(f"JSON inválido recebido de {addr}: {message}")
                send_json_response(conn, {"status": "ERROR", "message": "Invalid JSON format."})
            except Exception as e:
                logging.error(f"Erro ao processar comando de {addr}: {e}")
                send_json_response(conn, {"status": "ERROR", "message": "Internal server error."})
                break 

    except (ConnectionResetError, BrokenPipeError):
        logging.info(f"Conexão resetada por {addr} (Thread: {thread_name}).")
    except Exception as e:
        logging.error(f"Erro inesperado no handler de {addr}: {e} (Thread: {thread_name})")
    finally:
        logging.info(f"Conexão TCP de {addr} fechada (Thread: {thread_name}).")
        if 'client_file' in locals():
            client_file.close()
        conn.close()