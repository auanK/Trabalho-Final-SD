import asyncio
import logging
import struct 
from models import state_manager, UserStatus 
from db_manager import get_friends_list_db
import command_router 
from protocol import CommandCode, deserialize_payload, create_message, serialize_payload, CODE_TO_COMMAND_NAME

# Serializa o payload e envia a mensagem binária completa para uma pessoa em especifico
async def send_binary_message(writer: asyncio.StreamWriter, command_code: CommandCode, payload: dict):
    try:
        # 1. Serializa o payload específico do comando
        payload_bytes = serialize_payload(command_code, payload)
        # 2. Cria a mensagem completa com cabeçalho
        message_bytes = create_message(command_code, payload_bytes)
        # 3. Envia os bytes
        writer.write(message_bytes)
        await writer.drain()
    except Exception as e:
        logging.warning(f"Nao foi possivel enviar mensagem binaria para {writer.get_extra_info('peername')}: {e}")


# Informa a TODOS OS AMIGOS de um usuário sobre a mudança de status.
async def broadcast_status_update(changed_user_nickname: str, new_status_str: str):
    logging.info(f"Broadcast: {changed_user_nickname} está agora {new_status_str}")
    payload = {'nickname': changed_user_nickname, 'status': new_status_str}
    
    friends_of_changed_user = get_friends_list_db(changed_user_nickname)
    
    for nickname, user_obj in state_manager.get_all_users_items():
        if nickname in friends_of_changed_user:
             await send_binary_message(user_obj.writer, CommandCode.STATUS_UPDATE, payload)


# Função executada para cada cliente que se conecta
async def handle_client(reader: asyncio.StreamWriter, writer: asyncio.StreamWriter):
    addr = writer.get_extra_info('peername')
    logging.info(f"Nova conexao binaria de {addr}")
    
    context = {
        'reader': reader,
        'writer': writer,
        'addr': addr,
        'current_user': None 
    }

    try:
        while True:
            # 1. Ler o cabeçalho (1 byte comando + 2 bytes tamanho = 3 bytes)
            try:
                header = await reader.readexactly(3)
            except asyncio.IncompleteReadError:
                logging.info(f"Cliente {addr} desconectou (cabeçalho incompleto).")
                break # Conexão fechada
            
            # 2. Desempacotar o cabeçalho
            # !BH = Network order, 1 byte Unsigned Char (comando), 2 bytes Unsigned Short (tamanho)
            command_value, payload_length = struct.unpack('!BH', header)

            # 3. Ler o payload
            payload_bytes = b''
            if payload_length > 0:
                try:
                    payload_bytes = await reader.readexactly(payload_length)
                except asyncio.IncompleteReadError:
                    logging.warning(f"Cliente {addr} desconectou (payload incompleto para comando {command_value}).")
                    break # Conexão fechada

            # 4. Desserializar e Roteamento
            try:
                # Converte o valor numérico de volta para o Enum CommandCode
                command_code = CommandCode(command_value) 
                
                # Log com o nome do comando, se possível
                command_name = CODE_TO_COMMAND_NAME.get(command_code, f"UNKNOWN(0x{command_value:02X})")
                logging.info(f"Recebido Binário de {context['current_user'] or addr}: Cmd={command_name}, Len={payload_length}")

                # Desserializa o payload (manual ou JSON fallback)
                payload = deserialize_payload(command_code, payload_bytes)
                
                # Delega para o command_router (passa o CommandCode Enum e o payload dict)
                await command_router.route_command(context, command_code, payload)
                
            except ValueError:
                 logging.warning(f"Recebido código de comando inválido: {command_value} de {addr}")
                 # Opcional: Enviar mensagem de erro binária?
            except Exception as e:
                logging.error(f"Erro ao processar comando binário {command_value} de {addr}: {e}", exc_info=True)
                # Opcional: Enviar mensagem de erro binária?

    except asyncio.CancelledError:
        logging.info("Task do cliente cancelada.")
    except ConnectionResetError:
         logging.info(f"Conexão resetada pelo peer {addr}.")
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
                        await send_binary_message(partner_obj.writer, CommandCode.CALL_ENDED, {'from_nickname': current_user_nickname})
                        await broadcast_status_update(partner_nickname, UserStatus.ONLINE.value) 

                # Notifica amigos que ficou offline
                await broadcast_status_update(current_user_nickname, 'Offline')
                logging.info(f"Usuário '{current_user_nickname}' desconectado. Estado limpo.")
        # --- FIM DA MODIFICAÇÃO ---
        
        if not writer.is_closing():
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                 pass # Ignora erros no fechamento final