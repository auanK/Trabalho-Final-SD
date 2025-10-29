import logging
import socket 
from typing import List, Optional
import db_manager as db
from models import state_manager, UserProfile 
from interfaces import IAuthenticationService, IFriendshipService

class AuthenticationService(IAuthenticationService):
    def register_user(self, nickname: str, name: str, password: str) -> tuple[bool, str]:
        logging.info(f"Serviço: Tentando registrar usuário {nickname}")
        return db.register_user(nickname, name, password)

    def login_user(self, nickname: str, password: str, conn: socket.socket) -> tuple[bool, str]:

        logging.info(f"Serviço: Tentando login para {nickname}")
        
        # Verifica credenciais no DB
        if not db.check_login(nickname, password):
            logging.warning(f"Serviço: Login falhou (credenciais inválidas) para {nickname}")
            return (False, "Credenciais invalidas.")

        # Tenta adicionar ao state_manager 
        success_add = state_manager.add_user(nickname, conn)
        if not success_add:
            logging.warning(f"Serviço: Login falhou (já conectado) para {nickname}")
            return (False, "Usuario ja conectado.")

        return (True, "Login bem-sucedido!")


class FriendshipService(IFriendshipService):

    def search_users(self, query: str, current_user_nickname: str) -> List[UserProfile]:
        logging.info(f"Serviço: Buscando usuários com query '{query}' (por {current_user_nickname})")
        results_dict = db.search_users_db(query, current_user_nickname)
        return [UserProfile(nickname=res['nickname'], name=res['name']) for res in results_dict]

    def reject_request(self, requester_nickname: str, rejector_nickname: str) -> None:
        logging.info(f"Serviço: {rejector_nickname} rejeitando pedido de {requester_nickname}")
        db.update_friend_request_db(requester_nickname, rejector_nickname, 'rejected')

    def get_friends_with_status(self, nickname: str) -> List[dict]:
        logging.info(f"Serviço: Buscando amigos com status para {nickname}")
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
        logging.info(f"Serviço: {requester_nickname} tentando adicionar {target_nickname}")
        if requester_nickname == target_nickname:
             return (False, "Voce não pode adicionar a si mesmo.")

        success, message = db.add_friend_request_db(requester_nickname, target_nickname)

        return success, message

    def accept_request(self, requester_nickname: str, acceptor_nickname: str) -> tuple[bool, Optional[str], Optional[str]]:
        logging.info(f"Serviço: {acceptor_nickname} tentando aceitar pedido de {requester_nickname}")
        success = db.update_friend_request_db(requester_nickname, acceptor_nickname, 'accepted')

        if success:
            acceptor_status = state_manager.get_user_status_str(acceptor_nickname)
            requester_status = state_manager.get_user_status_str(requester_nickname)
         
            return (True, requester_status, acceptor_status)
        else:
            return (False, None, None)

auth_service = AuthenticationService()
friend_service = FriendshipService()