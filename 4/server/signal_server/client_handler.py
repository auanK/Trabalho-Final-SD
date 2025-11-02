import socket
import logging
import struct 
from models import state_manager, UserStatus 
from db_manager import get_friends_list_db
import command_router 
from protocol import CommandCode, CODE_TO_COMMAND_NAME, protocol
from typing import Optional 

# Função para garantir a leitura completa de n_bytes do socket
def recvall(conn: socket.socket, n_bytes: int) -> Optional[bytes]:
    data_chunks = []
    bytes_read = 0
    try:
        while bytes_read < n_bytes:
            chunk = conn.recv(n_bytes - bytes_read) 

            if not chunk:
                logging.warning(f"Conexão fechada por {conn.getpeername()} durante a leitura.")
                return None
            
            data_chunks.append(chunk)
            bytes_read += len(chunk)
        return b''.join(data_chunks)
    
    except (ConnectionResetError, BrokenPipeError, socket.timeout) as e:
        logging.warning(f"Erro de socket ao ler de {conn.getpeername()}: {e}")
        return None

# Pega um comando e o payload, converte para bytes e envia a msg para o cli
def send_binary_message(conn: socket.socket, command_code: CommandCode, payload: dict):
    try:
        message_bytes = protocol.create_message(command_code, payload)
        conn.sendall(message_bytes)
        
    except (ConnectionResetError, BrokenPipeError, socket.timeout) as e:
        logging.warning(f"Nao foi possivel enviar mensagem binaria para {conn.getpeername()}: {e}")
    except Exception as e:
        logging.warning(f"Erro ao preparar/enviar msg para {conn.getpeername()}: {e}", exc_info=True)

# Informa a todos os amigos de um usuário sobre a mudança de status.
def broadcast_status_update(changed_user_nickname: str, new_status_str: str):
    payload = {'nickname': changed_user_nickname, 'status': new_status_str}
    friends_of_changed_user = get_friends_list_db(changed_user_nickname)
    for nickname, user_obj in state_manager.get_all_users_items():
        if nickname in friends_of_changed_user:
            send_binary_message(user_obj.conn, CommandCode.STATUS_UPDATE, payload)

# Função executada para cada cliente em sua própria thread
def handle_client(conn: socket.socket, addr):
    context = {
        'conn': conn, 
        'addr': addr,
        'current_user': None 
    }

    try:
        while True:
            header = recvall(conn, 3) 

            if not header:
                logging.info(f"Cliente {addr} desconectou (cabeçalho).")
                break 
            
            command_value, payload_length = struct.unpack('!BH', header)

            payload_bytes = b''
            if payload_length > 0:
                payload_bytes = recvall(conn, payload_length) 
                if not payload_bytes:
                    logging.warning(f"Cliente {addr} desconectou (payload).")
                    break

            try:
                command_code = CommandCode(command_value) 
                command_name = CODE_TO_COMMAND_NAME.get(command_code, f"UNKNOWN(0x{command_value:02X})")
                
                logging.info(f"Recebido Binário de {context['current_user'] or addr}: Cmd={command_name}, Len={payload_length}")

                payload = protocol.deserialize_payload(command_code, payload_bytes)
                
                command_router.route_command(context, command_code, payload)
                
            except ValueError:
                 logging.warning(f"Recebido código de comando inválido: {command_value} de {addr}")
            except Exception as e:
                logging.error(f"Erro ao processar comando {command_value} de {addr}: {e}", exc_info=True)

    except (ConnectionResetError, socket.timeout, BrokenPipeError):
         logging.info(f"Conexão perdida para {addr}.")
    except Exception as e:
        logging.error(f"Erro inesperado na conexão {addr}: {e}", exc_info=True)
    finally:
        current_user_nickname = context.get('current_user')
        if current_user_nickname:
            removed_user_obj = state_manager.remove_user(current_user_nickname) 
            if removed_user_obj:
                if removed_user_obj.status == UserStatus.IN_CALL:
                    partner_nickname = removed_user_obj.in_call_with
                    partner_obj = state_manager.get_user(partner_nickname) 
                    if partner_obj: 
                        partner_obj.end_call() 
                        send_binary_message(partner_obj.conn, CommandCode.CALL_ENDED, {'from_nickname': current_user_nickname})
                        broadcast_status_update(partner_nickname, UserStatus.ONLINE.value) 

                broadcast_status_update(current_user_nickname, 'Offline')
                logging.info(f"Usuário '{current_user_nickname}' desconectado. Estado limpo.")
        
        logging.info(f"Fechando conexão com {addr}")
        conn.close()