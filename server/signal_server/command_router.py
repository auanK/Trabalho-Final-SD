import logging
import db_manager as db
from state_manager import state_manager, UserStatus 
import client_handler


# Recebe o comando e registra o user
async def handle_register(context, payload):
    nickname = payload.get('nickname')
    name = payload.get('name')
    password = payload.get('password')

    # Delega o registro para o modulo de db
    success, message = db.register_user(nickname, name, password)

    await client_handler.send_message(context['writer'], 'REGISTER_RESPONSE', {
        'success': success, 'message': message
    })

# Autenticar um usuário, verificar se ele já está online e, se o login for bem-sucedido, 
# atualizar o estado do servidor e notificar os amigos.
async def handle_login(context, payload):
    nickname = payload.get('nickname')
    password = payload.get('password')
    
    if db.check_login(nickname, password):
        # Tenta adicionar o usuário ao state_manager
        success_add = state_manager.add_user(nickname, context['writer'])
        
        if not success_add:
            # Falhou, significa que o usuário já estava no dicionário
            await client_handler.send_message(context['writer'], 'LOGIN_RESPONSE', {
                'success': False, 'message': 'Usuario ja conectado.'
            })
            context['writer'].close(); await context['writer'].wait_closed(); return
        
        context['current_user'] = nickname 
        
        # Mensagem de sucesso
        await client_handler.send_message(context['writer'], 'LOGIN_RESPONSE', {
            'success': True, 'message': 'Login bem-sucedido!',
            'nickname': nickname 
        })
        
        # Informa aos amigos que está online
        await client_handler.broadcast_status_update(nickname, UserStatus.ONLINE.value) 
        logging.info(f"Usuario '{nickname}' autenticado.")
    else:
        # Mensagem de credenciais inválidas (sem alteração)
        await client_handler.send_message(context['writer'], 'LOGIN_RESPONSE', {
            'success': False, 'message': 'Credenciais invalidas.'
        })

# Função é chamada pelo cliente logo após um login bem-sucedido 
# para carregar os dados necessários para construir a interface principal.
# Essa função coleta e enviar a lista de amigos do usuário (com seus status) e quaisquer pedidos de amizade pendentes.
async def handle_get_initial_data(context, payload):
    current_user = context['current_user']

    # 1. Envia a lista de amigos
    friends_list = db.get_friends_list_db(current_user)
    friends_with_status = []
    for friend_nickname in friends_list:
        # Usa o método do state_manager para pegar o status (retorna 'Offline' se não encontrado)
        status_str = state_manager.get_user_status_str(friend_nickname)
        friends_with_status.append({'nickname': friend_nickname, 'status': status_str})
    
    await client_handler.send_message(context['writer'], 'FRIEND_LIST', {'friends': friends_with_status})
    
    # 2. Envia Pedidos Pendentes (Sem alteração na lógica)
    pending_requests = db.get_pending_friend_requests_db(current_user)
    if pending_requests:
        logging.info(f"Enviando {len(pending_requests)} pedidos pendentes para {current_user}")
        await client_handler.send_message(context['writer'], 'PENDING_FRIEND_REQUESTS', {
            'requests_from': pending_requests
        })

# Tenta encontrar um user no db
async def handle_search_user(context, payload):
    query = payload.get('nickname_query', '')
    if not query: return
    results = db.search_users_db(query, context['current_user'])
    await client_handler.send_message(context['writer'], 'SEARCH_RESPONSE', {
        'success': True, 'results': results
    })

# Criar um registro de pedido de amizade pendente no banco de dados e 
# notifica o usuário-alvo
async def handle_add_friend(context, payload):
    current_user = context['current_user']
    target_nickname = payload.get('target_nickname')
    if not target_nickname: return
    if target_nickname == current_user:
         await client_handler.send_message(context['writer'], 'ADD_FRIEND_RESPONSE', {
            'success': False, 'message': 'Voca não pode adicionar a si mesmo.' 
        })
         return

    success, message = db.add_friend_request_db(current_user, target_nickname)
    await client_handler.send_message(context['writer'], 'ADD_FRIEND_RESPONSE', {
        'success': success, 'message': message
    })
    
    # Verifica se o alvo está online usando o state_manager
    target_user_obj = state_manager.get_user(target_nickname)
    if success and target_user_obj:
        # Usa o writer do objeto ConnectedUser
        await client_handler.send_message(target_user_obj.writer, 'INCOMING_FRIEND_REQUEST', {
            'from_nickname': current_user
        })

# função é acionada quando um usuário aceita um pedido de amizade. Muda o status de pending para accepted
async def handle_accept_friend(context, payload):
    # Pega o objeto do usuário atual (quem está aceitando)
    current_user_obj = state_manager.get_user(context['current_user'])
    requester_nickname = payload.get('requester_nickname')
    if not current_user_obj or not requester_nickname: return
    
    success = db.update_friend_request_db(requester_nickname, current_user_obj.nickname, 'accepted')
    
    if success:
        # Pega o objeto do requisitante (se ele estiver online)
        requester_obj = state_manager.get_user(requester_nickname)
        
        # Notifica o requisitante (se online)
        if requester_obj:
            await client_handler.send_message(requester_obj.writer, 'FRIEND_REQUEST_ACCEPTED', {
                'by_nickname': current_user_obj.nickname, 
                # Pega o status atual de quem aceitou
                'status': current_user_obj.get_status_str() 
            })
            
        # Notifica o aceitante (você)
        await client_handler.send_message(current_user_obj.writer, 'FRIEND_REQUEST_ACCEPTED', {
            'by_nickname': requester_nickname, 
            'status': state_manager.get_user_status_str(requester_nickname) 
        })

async def handle_reject_friend(context, payload):
    requester_nickname = payload.get('requester_nickname')
    if not requester_nickname: return
    db.update_friend_request_db(requester_nickname, context['current_user'], 'rejected')

# Verifica se o usuário-alvo pode receber uma chamada e, se puder, encaminha o convite.
async def handle_invite(context, payload):
    current_user = context['current_user']
    target_nickname = payload.get('target_nickname')
    
    # Pega o objeto do usuário alvo
    target_user_obj = state_manager.get_user(target_nickname)
    
    # Verifica se o alvo existe E se seu status é ONLINE (usando a Enum)
    if target_user_obj and target_user_obj.status == UserStatus.ONLINE:
        # Usa o writer do objeto
        await client_handler.send_message(target_user_obj.writer, 'INCOMING_CALL', {'from_nickname': current_user})
        await client_handler.send_message(context['writer'], 'INVITE_RESPONSE', {
            'success': True, 'message': f'A chamar {target_nickname}...'
        })
    else:
        # Alvo não encontrado ou não está ONLINE
        await client_handler.send_message(context['writer'], 'INVITE_RESPONSE', {
            'success': False, 'message': f'Utilizador {target_nickname} está offline ou ocupado.'
        })

# Altera o status da amizade de pending para accepted e notifica ambos os usuários.
async def handle_accept(context, payload):
    current_user_obj = state_manager.get_user(context['current_user'])
    original_caller_nickname = payload.get('caller_nickname')
    original_caller_obj = state_manager.get_user(original_caller_nickname)
    
    # Verifica se ambos ainda estão online
    if current_user_obj and original_caller_obj:
        # Usa os métodos da classe ConnectedUser para mudar o estado
        current_user_obj.start_call(original_caller_nickname)
        original_caller_obj.start_call(current_user_obj.nickname)
        
        payload_data = {
            'relay_ip': '127.0.0.1', 
            'relay_port': 9000,
            'token': 'token_de_sessao'
        }
        # Envia a mensagem para o chamador original
        await client_handler.send_message(original_caller_obj.writer, 'CALL_ACCEPTED', {
            'callee_nickname': current_user_obj.nickname, **payload_data 
        })
        # Envia a mensagem para quem aceitou
        await client_handler.send_message(current_user_obj.writer, 'CALL_ACCEPTED', {
            'callee_nickname': current_user_obj.nickname, **payload_data 
        })
        
        # Notifica os amigos sobre a mudança de status
        await client_handler.broadcast_status_update(current_user_obj.nickname, UserStatus.IN_CALL.value)
        await client_handler.broadcast_status_update(original_caller_obj.nickname, UserStatus.IN_CALL.value)

# Envia uma notificação de rejeição para o chamador original.
async def handle_reject(context, payload):
    # Pega o objeto do chamador original
    caller_nickname = payload.get('caller_nickname')
    caller_obj = state_manager.get_user(caller_nickname)
    
    # Se o chamador ainda estiver online, notifica
    if caller_obj:
        await client_handler.send_message(caller_obj.writer, 'CALL_REJECTED', {
            'callee_nickname': context['current_user'] 
        })

# Finaliza uma chamada, atualiza o estado de ambos os usuários e notifica amigos e o parceiro.
async def handle_bye(context, payload):
    current_user_obj = state_manager.get_user(context['current_user'])
    
    if not current_user_obj or current_user_obj.status != UserStatus.IN_CALL:
        return 
        
    partner_nickname = current_user_obj.in_call_with
    
    current_user_obj.end_call()
    await client_handler.broadcast_status_update(current_user_obj.nickname, UserStatus.ONLINE.value)

    # Pega o objeto do parceiro (se ele ainda estiver online)
    partner_obj = state_manager.get_user(partner_nickname)
    if partner_obj:
        partner_obj.end_call()
        await client_handler.send_message(partner_obj.writer, 'CALL_ENDED', {
            'from_nickname': current_user_obj.nickname
        })
        await client_handler.broadcast_status_update(partner_obj.nickname, UserStatus.ONLINE.value)


#====================================================================

COMMAND_MAP = {
    # Comandos públicos
    'REGISTER': handle_register,
    'LOGIN': handle_login,
    
    # Comandos privados
    'GET_INITIAL_DATA': handle_get_initial_data,
    'SEARCH_USER': handle_search_user,
    'ADD_FRIEND': handle_add_friend,
    'ACCEPT_FRIEND': handle_accept_friend,
    'REJECT_FRIEND': handle_reject_friend,
    'INVITE': handle_invite,
    'ACCEPT': handle_accept,
    'REJECT': handle_reject,
    'BYE': handle_bye,
}

# Roteia um comando para a função de handler apropriada.
async def route_command(context, cmd, payload):

    # Verifica se o usuário está logado para comandos privados
    if cmd not in ('REGISTER', 'LOGIN') and not context.get('current_user'):
        await client_handler.send_message(context['writer'], 'ERROR', {'error': 'Autenticacao necessaria.'})
        return

    # Encontra a função no mapa
    handler_function = COMMAND_MAP.get(cmd)
    
    if handler_function:
        await handler_function(context, payload)
    else:
        logging.warning(f"Comando desconhecido recebido: {cmd}")