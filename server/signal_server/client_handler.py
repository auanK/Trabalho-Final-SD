import asyncio
import json
import logging
from state_manager import state_manager, UserStatus 
from db_manager import get_friends_list_db
import command_router 

# Envia uma mensagem JSON formatada para um cliente
async def send_message(writer, command, payload):
    try:
        msg = {'command': command, 'payload': payload}
        writer.write(json.dumps(msg).encode('utf-8') + b'\n') # \n é o delimitador
        await writer.drain()
    except Exception as e:
        logging.warning(f"Nao foi possivel enviar mensagem para {writer.get_extra_info('peername')}: {e}")

# Informa a TODOS OS AMIGOS de um usuário sobre a mudança de status.
async def broadcast_status_update(changed_user_nickname: str, new_status_str: str):
    logging.info(f"Broadcast: {changed_user_nickname} está agora {new_status_str}")
    payload = {'nickname': changed_user_nickname, 'status': new_status_str}
    
    friends_of_changed_user = get_friends_list_db(changed_user_nickname)
    
    # Usa o novo state_manager para iterar sobre os usuários online
    for nickname, user_obj in state_manager.get_all_users_items():
        if nickname in friends_of_changed_user:
            await send_message(user_obj.writer, 'STATUS_UPDATE', payload)

# Função executada para cada cliente que se conecta
async def handle_client(reader, writer):
    addr = writer.get_extra_info('peername')
    logging.info(f"Nova conexao de {addr}")
    
    context = {
        'reader': reader,
        'writer': writer,
        'addr': addr,
        'current_user': None 
    }

    try:
        while True:
            # read espera por uma mensagem desse cliente específico. (4096 bytes de dados)
            data = await reader.read(4096)

            # data = b'' significa que o cliente fechou a conexão
            if not data:
                logging.info(f"Cliente {addr} (Usuario: {context['current_user']}) desconectou.")
                break
            
            messages = data.decode('utf-8').strip().split('\n')
            for msg in messages:
                if not msg:
                    continue
                
                try:
                    command_json = json.loads(msg) # converte pra dicionario
                    logging.info(f"Recebido de {context['current_user'] if context['current_user'] else addr}: {command_json}")
   
                    cmd = command_json.get('command')
                    payload = command_json.get('payload')
                    
                    # delegando os comandos para outra classe
                    await command_router.route_command(context, cmd, payload)
                    
                except json.JSONDecodeError:
                    logging.warning(f"Recebida mensagem mal formatada de {addr}")
                except Exception as e:
                    logging.error(f"Erro ao processar comando: {e}")

    except asyncio.CancelledError:
        logging.info("Task do cliente cancelada.")
    except Exception as e:
        logging.error(f"Erro inesperado na conexão {addr}: {e}")
    finally:
        # --- Lógica de Limpeza ao Desconectar---
        current_user_nickname = context.get('current_user')
        if current_user_nickname:
            # Usa o state_manager para remover o usuário.
            # Isso retorna o objeto ConnectedUser se ele existia.
            removed_user_obj = state_manager.remove_user(current_user_nickname) 
            
            if removed_user_obj:
                # Se o usuário estava em chamada, notifica o outro
                if removed_user_obj.status == UserStatus.IN_CALL:
                    partner_nickname = removed_user_obj.in_call_with
                    # Usa o state_manager para pegar o objeto do parceiro
                    partner_obj = state_manager.get_user(partner_nickname) 
                    
                    if partner_obj: 
                        partner_obj.end_call() 
                        await send_message(partner_obj.writer, 'CALL_ENDED', {'from_nickname': current_user_nickname})
                        await broadcast_status_update(partner_nickname, UserStatus.ONLINE.value) 

                await broadcast_status_update(current_user_nickname, 'Offline')
                logging.info(f"Usuário '{current_user_nickname}' desconectado. Estado limpo.")
        
        if not writer.is_closing():
            writer.close()
            await writer.wait_closed()