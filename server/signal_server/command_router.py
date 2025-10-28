import logging
import client_handler 
from services import auth_service, friend_service
from models import state_manager, UserStatus
from protocol import CODE_TO_COMMAND_NAME, CommandCode
import asyncio 


async def handle_register(context, payload):
    # ... (sem mudanças)
    nickname = payload.get('nickname')
    name = payload.get('name')
    password = payload.get('password')
    success, message = auth_service.register_user(nickname, name, password)
    await client_handler.send_binary_message(context['writer'], CommandCode.REGISTER_RESPONSE, {
        'success': success, 'message': message
    })
    
async def handle_login(context, payload):
    nickname = payload.get('nickname')
    password = payload.get('password')
    # Chama login_user que retorna (success, message)
    success, message = auth_service.login_user(nickname, password, context['writer'])

    response_payload = {'success': success, 'message': message}
    if success:
        response_payload['nickname'] = nickname
        context['current_user'] = nickname # Define usuário no contexto

        # Informa aos amigos que está online
        asyncio.create_task(client_handler.broadcast_status_update(nickname, UserStatus.ONLINE.value))

    # Fecha conexão duplicada aqui se necessário
    elif message == "Usuario ja conectado.":
         context['writer'].close(); await context['writer'].wait_closed()
         return 

    await client_handler.send_binary_message(context['writer'], CommandCode.LOGIN_RESPONSE, response_payload)


async def handle_get_initial_data(context, payload):
    # ... (sem mudanças)
    current_user = context['current_user']
    friends_with_status = friend_service.get_friends_with_status(current_user)
    pending_requests = friend_service.get_pending_requests(current_user)
    await client_handler.send_binary_message(context['writer'], CommandCode.FRIEND_LIST, {'friends': friends_with_status})
    if pending_requests:
        logging.info(f"Roteador: Enviando {len(pending_requests)} pedidos pendentes para {current_user}")
        await client_handler.send_binary_message(context['writer'], CommandCode.PENDING_FRIEND_REQUESTS, {
            'requests_from': pending_requests
        })

async def handle_search_user(context, payload):
    # ... (sem mudanças)
    query = payload.get('nickname_query', '')
    if not query: return
    results_profiles = friend_service.search_users(query, context['current_user'])
    results_dicts = [{'nickname': p.nickname, 'name': p.name} for p in results_profiles]
    await client_handler.send_binary_message(context['writer'], CommandCode.SEARCH_RESPONSE, {
        'success': True, 'results': results_dicts
    })

async def handle_add_friend(context, payload):
    current_user = context['current_user']
    target_nickname = payload.get('target_nickname')
    if not target_nickname: return

    success, message = friend_service.send_request(current_user, target_nickname)

    await client_handler.send_binary_message(context['writer'], CommandCode.ADD_FRIEND_RESPONSE, {
        'success': success, 'message': message
    })

    # --- ADICIONADO: Notificação movida para cá ---
    if success:
        target_user_obj = state_manager.get_user(target_nickname)
        if target_user_obj:
            logging.info(f"Roteador: Notificando {target_nickname} sobre pedido de {current_user}")
            asyncio.create_task(
                client_handler.send_binary_message(
                    target_user_obj.writer,
                    CommandCode.INCOMING_FRIEND_REQUEST,
                    {'from_nickname': current_user}
                )
            )
    # ------------------------------------------

async def handle_accept_friend(context, payload):
    current_user = context['current_user'] # Quem aceitou
    requester_nickname = payload.get('requester_nickname')
    if not requester_nickname: return

    success, requester_status, acceptor_status = friend_service.accept_request(requester_nickname, current_user)

    if success:
        # --- ADICIONADO: Notificações movidas para cá ---
        acceptor_obj = state_manager.get_user(current_user)
        requester_obj = state_manager.get_user(requester_nickname)

        # Notifica o requisitante (se online)
        if requester_obj:
            logging.info(f"Roteador: Notificando {requester_nickname} que {current_user} aceitou")
            asyncio.create_task(
                client_handler.send_binary_message(
                    requester_obj.writer, CommandCode.FRIEND_REQUEST_ACCEPTED,
                    {'by_nickname': current_user, 'status': acceptor_status} # acceptor_status vem do serviço
                )
            )
        # Notifica o aceitante (para atualizar a UI)
        if acceptor_obj:
            logging.info(f"Roteador: Notificando {current_user} sobre aceitação de {requester_nickname}")
            asyncio.create_task(
                 client_handler.send_binary_message(
                    acceptor_obj.writer, CommandCode.FRIEND_REQUEST_ACCEPTED,
                    {'by_nickname': requester_nickname, 'status': requester_status} # requester_status vem do serviço
                 )
             )
        # ------------------------------------------
    else:
         await client_handler.send_binary_message(context['writer'], CommandCode.ERROR, {
             'message': 'Falha ao aceitar pedido (talvez não exista mais).'
         })


async def handle_reject_friend(context, payload):
    # ... (sem mudanças, continua silencioso)
    requester_nickname = payload.get('requester_nickname')
    if not requester_nickname: return
    friend_service.reject_request(requester_nickname, context['current_user'])

# --- Handlers de Chamada (Não foram movidos para serviços, sem mudanças aqui) ---
async def handle_invite(context, payload):
    # ... (código existente) ...
    current_user = context['current_user']
    target_nickname = payload.get('target_nickname')
    target_user_obj = state_manager.get_user(target_nickname)
    if target_user_obj and target_user_obj.status == UserStatus.ONLINE:
        await client_handler.send_binary_message(target_user_obj.writer, CommandCode.INCOMING_CALL,{'from_nickname': current_user})
        await client_handler.send_binary_message(context['writer'], CommandCode.INVITE_RESPONSE, {'success': True, 'message': f'A chamar {target_nickname}...' })
    else:
        await client_handler.send_binary_message(context['writer'], CommandCode.INVITE_RESPONSE, {'success': False, 'message': f'Utilizador {target_nickname} está offline ou ocupado.'})

async def handle_accept(context, payload):
    # ... (código existente) ...
    current_user_obj = state_manager.get_user(context['current_user'])
    original_caller_nickname = payload.get('caller_nickname')
    original_caller_obj = state_manager.get_user(original_caller_nickname)
    if current_user_obj and original_caller_obj and original_caller_obj.status == UserStatus.ONLINE:
        current_user_obj.start_call(original_caller_nickname)
        original_caller_obj.start_call(current_user_obj.nickname)
        payload_data = { 'relay_ip': '127.0.0.1', 'relay_port': 9000, 'token': 'token_de_sessao' }
        await client_handler.send_binary_message(original_caller_obj.writer, CommandCode.CALL_ACCEPTED, {'callee_nickname': current_user_obj.nickname, **payload_data})
        await client_handler.send_binary_message(current_user_obj.writer, CommandCode.CALL_ACCEPTED, {'callee_nickname': current_user_obj.nickname, **payload_data})
        await client_handler.broadcast_status_update(current_user_obj.nickname, UserStatus.IN_CALL.value)
        await client_handler.broadcast_status_update(original_caller_obj.nickname, UserStatus.IN_CALL.value)

async def handle_reject(context, payload):
    # ... (código existente) ...
    caller_nickname = payload.get('caller_nickname')
    caller_obj = state_manager.get_user(caller_nickname)
    if caller_obj:
        await client_handler.send_binary_message(caller_obj.writer, CommandCode.CALL_REJECTED, {'callee_nickname': context['current_user']})

async def handle_bye(context, payload):
    # ... (código existente) ...
    current_user_obj = state_manager.get_user(context['current_user'])
    if not current_user_obj or current_user_obj.status != UserStatus.IN_CALL: return
    partner_nickname = current_user_obj.in_call_with
    current_user_obj.end_call()
    await client_handler.broadcast_status_update(current_user_obj.nickname, UserStatus.ONLINE.value)
    partner_obj = state_manager.get_user(partner_nickname)
    if partner_obj:
        partner_obj.end_call()
        await client_handler.send_binary_message(partner_obj.writer, CommandCode.CALL_ENDED, {'from_nickname': current_user_obj.nickname})
        await client_handler.broadcast_status_update(partner_obj.nickname, UserStatus.ONLINE.value)

#====================================================================

COMMAND_MAP = {
    # Mapeia CommandCode (Enum) para a função handler
    CommandCode.REGISTER: handle_register,
    CommandCode.LOGIN: handle_login,
    CommandCode.GET_INITIAL_DATA: handle_get_initial_data,
    CommandCode.SEARCH_USER: handle_search_user,
    CommandCode.ADD_FRIEND: handle_add_friend,
    CommandCode.ACCEPT_FRIEND: handle_accept_friend,
    CommandCode.REJECT_FRIEND: handle_reject_friend,
    CommandCode.INVITE: handle_invite,
    CommandCode.ACCEPT: handle_accept,
    CommandCode.REJECT: handle_reject,
    CommandCode.BYE: handle_bye,
}

# --- MODIFICADO: Recebe CommandCode em vez de string 'cmd' ---
async def route_command(context, cmd_code: CommandCode, payload: dict):
    # Verifica autenticação (usa o Enum CommandCode)
    if cmd_code not in (CommandCode.REGISTER, CommandCode.LOGIN) and not context.get('current_user'):
        await client_handler.send_binary_message(context['writer'], CommandCode.ERROR, 
                                                 {'error': 'Autenticacao necessaria.'})
        return

    # Encontra a função no mapa usando o Enum
    handler_function = COMMAND_MAP.get(cmd_code)
    
    if handler_function:
        await handler_function(context, payload)
    else:
        command_name = CODE_TO_COMMAND_NAME.get(cmd_code, f"UNKNOWN(0x{cmd_code.value:02X})")
        logging.warning(f"Comando binário desconhecido recebido: {command_name}")
        # Opcional: Enviar erro binário
        # await client_handler.send_binary_message(context['writer'], CommandCode.ERROR, 
        #                                          {'error': f'Comando desconhecido: {command_name}'})
