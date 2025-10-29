import logging
import client_handler 
from services import auth_service, friend_service
from models import state_manager, UserStatus 
from protocol import CODE_TO_COMMAND_NAME, CommandCode

def handle_register(context, payload):
    nickname = payload.get('nickname')
    name = payload.get('name')
    password = payload.get('password')
    success, message = auth_service.register_user(nickname, name, password)
    
    client_handler.send_binary_message(context['conn'], CommandCode.REGISTER_RESPONSE, {
        'success': success, 'message': message
    })
    
def handle_login(context, payload):
    nickname = payload.get('nickname')
    password = payload.get('password')
    
    success, message = auth_service.login_user(nickname, password, context['conn'])

    response_payload = {'success': success, 'message': message}
    if success:
        response_payload['nickname'] = nickname
        context['current_user'] = nickname 

        client_handler.broadcast_status_update(nickname, UserStatus.ONLINE.value)

    elif message == "Usuario ja conectado.":
        context['conn'].close() 
        return 

    client_handler.send_binary_message(context['conn'], CommandCode.LOGIN_RESPONSE, response_payload)

def handle_get_initial_data(context, payload):
    current_user = context['current_user']
    friends_with_status = friend_service.get_friends_with_status(current_user)
    pending_requests = friend_service.get_pending_requests(current_user)
    
    client_handler.send_binary_message(context['conn'], CommandCode.FRIEND_LIST, {'friends': friends_with_status})
    if pending_requests:
        logging.info(f"Roteador: Enviando {len(pending_requests)} pedidos pendentes para {current_user}")
        client_handler.send_binary_message(context['conn'], CommandCode.PENDING_FRIEND_REQUESTS, {
            'requests_from': pending_requests
        })

def handle_search_user(context, payload):
    query = payload.get('nickname_query', '')
    if not query: return
    results_profiles = friend_service.search_users(query, context['current_user'])
    results_dicts = [{'nickname': p.nickname, 'name': p.name} for p in results_profiles]
    client_handler.send_binary_message(context['conn'], CommandCode.SEARCH_RESPONSE, {
        'success': True, 'results': results_dicts
    })

def handle_add_friend(context, payload):
    current_user = context['current_user']
    target_nickname = payload.get('target_nickname')
    if not target_nickname: return

    success, message = friend_service.send_request(current_user, target_nickname)

    client_handler.send_binary_message(context['conn'], CommandCode.ADD_FRIEND_RESPONSE, {
        'success': success, 'message': message
    })

    if success:
        target_user_obj = state_manager.get_user(target_nickname)
        if target_user_obj:
            logging.info(f"Roteador: Notificando {target_nickname} sobre pedido de {current_user}")
            client_handler.send_binary_message(
                target_user_obj.conn,
                CommandCode.INCOMING_FRIEND_REQUEST,
                {'from_nickname': current_user}
            )

def handle_accept_friend(context, payload):
    current_user = context['current_user'] # Quem aceitou
    requester_nickname = payload.get('requester_nickname')
    if not requester_nickname: return

    success, requester_status, acceptor_status = friend_service.accept_request(requester_nickname, current_user)

    if success:
        acceptor_obj = state_manager.get_user(current_user)
        requester_obj = state_manager.get_user(requester_nickname)

        if requester_obj:
            logging.info(f"Roteador: Notificando {requester_nickname} que {current_user} aceitou")
            client_handler.send_binary_message(
                requester_obj.conn, CommandCode.FRIEND_REQUEST_ACCEPTED,
                {'by_nickname': current_user, 'status': acceptor_status} 
            )
        if acceptor_obj:
            logging.info(f"Roteador: Notificando {current_user} sobre aceitação de {requester_nickname}")
            client_handler.send_binary_message(
                acceptor_obj.conn, CommandCode.FRIEND_REQUEST_ACCEPTED,
                {'by_nickname': requester_nickname, 'status': requester_status}
            )
    else:
         client_handler.send_binary_message(context['conn'], CommandCode.ERROR, {
             'message': 'Falha ao aceitar pedido (talvez não exista mais).'
         })


def handle_reject_friend(context, payload):
    requester_nickname = payload.get('requester_nickname')
    if not requester_nickname: return
    friend_service.reject_request(requester_nickname, context['current_user'])

def handle_invite(context, payload):
    current_user = context['current_user']
    target_nickname = payload.get('target_nickname')
    target_user_obj = state_manager.get_user(target_nickname)
    
    if target_user_obj and target_user_obj.status == UserStatus.ONLINE:
        client_handler.send_binary_message(target_user_obj.conn, CommandCode.INCOMING_CALL,{'from_nickname': current_user})
        client_handler.send_binary_message(context['conn'], CommandCode.INVITE_RESPONSE, {'success': True, 'message': f'A chamar {target_nickname}...' })
    else:
        client_handler.send_binary_message(context['conn'], CommandCode.INVITE_RESPONSE, {'success': False, 'message': f'Utilizador {target_nickname} está offline ou ocupado.'})

def handle_accept(context, payload):
    current_user_obj = state_manager.get_user(context['current_user'])
    original_caller_nickname = payload.get('caller_nickname')
    original_caller_obj = state_manager.get_user(original_caller_nickname)
    if current_user_obj and original_caller_obj and original_caller_obj.status == UserStatus.ONLINE:
        current_user_obj.start_call(original_caller_nickname)
        original_caller_obj.start_call(current_user_obj.nickname)
        payload_data = { 'relay_ip': '127.0.0.1', 'relay_port': 9000, 'token': 'token_de_sessao' }
        client_handler.send_binary_message(original_caller_obj.conn, CommandCode.CALL_ACCEPTED, {'callee_nickname': current_user_obj.nickname, **payload_data})
        client_handler.send_binary_message(current_user_obj.conn, CommandCode.CALL_ACCEPTED, {'callee_nickname': current_user_obj.nickname, **payload_data})
        client_handler.broadcast_status_update(current_user_obj.nickname, UserStatus.IN_CALL.value)
        client_handler.broadcast_status_update(original_caller_obj.nickname, UserStatus.IN_CALL.value)

def handle_reject(context, payload):
    caller_nickname = payload.get('caller_nickname')
    caller_obj = state_manager.get_user(caller_nickname)
    if caller_obj:
        client_handler.send_binary_message(caller_obj.conn, CommandCode.CALL_REJECTED, {'callee_nickname': context['current_user']})

def handle_bye(context, payload):
    current_user_obj = state_manager.get_user(context['current_user'])
    if not current_user_obj or current_user_obj.status != UserStatus.IN_CALL: return
    partner_nickname = current_user_obj.in_call_with
    current_user_obj.end_call()
    client_handler.broadcast_status_update(current_user_obj.nickname, UserStatus.ONLINE.value)
    partner_obj = state_manager.get_user(partner_nickname)
    if partner_obj:
        partner_obj.end_call()
        client_handler.send_binary_message(partner_obj.conn, CommandCode.CALL_ENDED, {'from_nickname': current_user_obj.nickname})
        client_handler.broadcast_status_update(partner_obj.nickname, UserStatus.ONLINE.value)

#====================================================================

# Mapeia CommandCode (enum) para a função handler
COMMAND_MAP = {
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

def route_command(context, cmd_code: CommandCode, payload: dict):
    if cmd_code not in (CommandCode.REGISTER, CommandCode.LOGIN) and not context.get('current_user'):
        client_handler.send_binary_message(context['conn'], CommandCode.ERROR, 
                                                 {'error': 'Autenticacao necessaria.'})
        return

    handler_function = COMMAND_MAP.get(cmd_code)
    
    # executa a função
    if handler_function:
        handler_function(context, payload) 

    else:
        command_name = CODE_TO_COMMAND_NAME.get(cmd_code, f"UNKNOWN(0x{cmd_code.value:02X})")
        logging.warning(f"Comando binário desconhecido recebido: {command_name}")