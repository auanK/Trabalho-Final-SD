import logging
import secrets 
from typing import List, Optional
import db_manager as db
from models import state_manager, UserProfile, UserStatus
from interfaces import IAuthenticationService, IFriendshipService, ICallService 
import config 

# Serviço de autenticação
class AuthenticationService(IAuthenticationService):
    def register_user(self, nickname: str, name: str, password: str) -> tuple[bool, str]:
        return db.register_user(nickname, name, password)

    def login_user(self, nickname: str, password: str) -> tuple[bool, str]:
        
        if not db.check_login(nickname, password):
            logging.warning(f"Serviço: Login falhou (credenciais inválidas) para {nickname}")
            return (False, "Credenciais invalidas.")

        success_add = state_manager.add_user(nickname)
        if not success_add:
            logging.warning(f"Serviço: Login falhou (erro ao adicionar ao estado) para {nickname}")
            return (False, "Erro interno ao logar.")

        return (True, "Login bem-sucedido!")

# Serviço de amizade
class FriendshipService(IFriendshipService):
    
    def search_users(self, query: str, current_user_nickname: str) -> List[UserProfile]:
        results_dict = db.search_users_db(query, current_user_nickname)
        return [UserProfile(nickname=res['nickname'], name=res['name']) for res in results_dict]

    def reject_request(self, requester_nickname: str, rejector_nickname: str) -> None:
        db.update_friend_request_db(requester_nickname, rejector_nickname, 'rejected')

    def get_friends_with_status(self, nickname: str) -> List[dict]:
        friend_nicknames = db.get_friends_list_db(nickname)
        friends_with_status = []
        for friend in friend_nicknames:
            status = state_manager.get_user_status_str(friend)
            friends_with_status.append({'nickname': friend, 'status': status})
        return friends_with_status

    def get_pending_requests(self, nickname: str) -> List[str]:
        logging.info(f"Serviço: Buscando pedidos pendentes para {nickname}")
        return db.get_pending_friend_requests_db(nickname)

    def send_request(self, requester_nickname: str, target_nickname: str) -> tuple[bool, str]:

        if requester_nickname == target_nickname:
             return (False, "Voce não pode adicionar a si mesmo.")

        success, message = db.add_friend_request_db(requester_nickname, target_nickname)

        # Adiciona evento à fila do target
        if success:
            state_manager.add_event(
                target_nickname,
                {'command': 'INCOMING_FRIEND_REQUEST', 'from_nickname': requester_nickname}
            )

        return success, message

    def accept_request(self, requester_nickname: str, acceptor_nickname: str) -> tuple[bool, Optional[str], Optional[str]]:

        success = db.update_friend_request_db(requester_nickname, acceptor_nickname, 'accepted')

        if success:
            acceptor_status = state_manager.get_user_status_str(acceptor_nickname)
            requester_status = state_manager.get_user_status_str(requester_nickname)
         
            # Enfileira evento para o requisitante
            state_manager.add_event(
                requester_nickname,
                {'command': 'FRIEND_REQUEST_ACCEPTED', 'by_nickname': acceptor_nickname, 'status': acceptor_status}
            )
            # Enfileira evento para o aceitante
            state_manager.add_event(
                acceptor_nickname,
                {'command': 'FRIEND_REQUEST_ACCEPTED', 'by_nickname': requester_nickname, 'status': requester_status}
            )
            
            return (True, requester_status, acceptor_status)
        else:
            return (False, None, None)

    # Enfileira eventos de atualização de status para todos os amigos.
    def broadcast_status_update(self, changed_user_nickname: str, new_status_str: str):
        logging.info(f"Serviço: Transmitindo status {new_status_str} para {changed_user_nickname}")

        payload = {'command': 'STATUS_UPDATE', 'nickname': changed_user_nickname, 'status': new_status_str}
        friends_of_changed_user = db.get_friends_list_db(changed_user_nickname)
        
        for friend_nickname in friends_of_changed_user:
            state_manager.add_event(friend_nickname, payload)

# Serviço de chamadas
class CallService(ICallService):
    
    def create_call_session(self, caller_nickname: str, callee_nickname: str) -> tuple[bool, str, Optional[dict]]:

        logging.info(f"Serviço: Criando sessão de chamada para {caller_nickname} e {callee_nickname}")
        session_token = secrets.token_hex(16)
        relay_info = {
            'relay_ip': config.RELAY_SERVER_IP,
            'relay_port': config.RELAY_SERVER_PORT,
            'token': session_token
        }
        logging.info(f"Serviço: Sessão criada. Relay: {config.RELAY_SERVER_IP}:{config.RELAY_SERVER_PORT}")
        return (True, "Sessão criada com sucesso.", relay_info)

    # Enfileira um convite para o target.
    def invite(self, caller_nickname: str, callee_nickname: str) -> tuple[bool, str]:
        callee = state_manager.get_user(callee_nickname)
        
        if callee and callee.status == UserStatus.ONLINE:
            state_manager.add_event(
                callee_nickname,
                {'command': 'INCOMING_CALL', 'from_nickname': caller_nickname}
            )
            return (True, f'A chamar {callee_nickname}...')
        else:
            return (False, f'Utilizador {callee_nickname} está offline ou ocupado.')

    # Cria a sessão e enfileira 'CALL_ACCEPTED' para ambos.
    def accept(self, caller_nickname: str, callee_nickname: str) -> tuple[bool, str, Optional[dict]]:

        caller = state_manager.get_user(caller_nickname)
        callee = state_manager.get_user(callee_nickname)

        if not (caller and callee):
            return (False, "O autor da chamada ou o destinatário desconectou.", None)

        success, message, relay_info = self.create_call_session(caller_nickname, callee_nickname)

        if not success:
            return (False, message, None)

        caller.start_call(callee_nickname)
        callee.start_call(caller_nickname)
        
        payload_to_send = {
            'command': 'CALL_ACCEPTED',
            'callee_nickname': callee_nickname, 
            **relay_info
        }
        
        state_manager.add_event(caller_nickname, payload_to_send)
        state_manager.add_event(callee_nickname, payload_to_send)

        return (True, "Chamada aceita.", relay_info)

    # Enfileira uma rejeição para o chamador.
    def reject(self, caller_nickname: str, callee_nickname: str):
        state_manager.add_event(
            caller_nickname,
            {'command': 'CALL_REJECTED', 'callee_nickname': callee_nickname}
        )

    # Encerra a chamada e enfileira 'CALL_ENDED' para o parceiro.
    def end_call(self, user_ending_call: str):
        user = state_manager.get_user(user_ending_call)
        if not user or user.status != UserStatus.IN_CALL:
            return

        partner_nickname = user.in_call_with
        user.end_call()
        
        partner = state_manager.get_user(partner_nickname)
        if partner:
            partner.end_call()
            state_manager.add_event(
                partner_nickname,
                {'command': 'CALL_ENDED', 'from_nickname': user_ending_call}
            )

auth_service = AuthenticationService()
friend_service = FriendshipService()
call_service = CallService()