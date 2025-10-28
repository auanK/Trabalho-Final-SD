import logging
import asyncio
from typing import List, Optional
import db_manager as db
# --- MODIFICADO: Imports ---
from models import state_manager, UserStatus, UserProfile
# REMOVA A LINHA ABAIXO:
# from client_handler import send_binary_message
from protocol import CommandCode
# REMOVA A LINHA ABAIXO:
# from server.signal_server import client_handler # Não importe client_handler aqui
# --- FIM DA MODIFICAÇÃO ---

class AuthenticationService:
    def register_user(self, nickname: str, name: str, password: str) -> tuple[bool, str]:
        # (Sem mudanças na lógica interna)
        logging.info(f"Serviço: Tentando registrar usuário {nickname}")
        return db.register_user(nickname, name, password)

    def login_user(self, nickname: str, password: str, writer: asyncio.StreamWriter) -> tuple[bool, str]: # Retorna (success, message)
        """
        Tenta autenticar um usuário e adicioná-lo ao estado online.
        Retorna (sucesso_login, mensagem).
        """
        logging.info(f"Serviço: Tentando login para {nickname}")
        # 1. Verifica credenciais no DB (db.check_login retorna True/False)
        if not db.check_login(nickname, password):
            logging.warning(f"Serviço: Login falhou (credenciais inválidas) para {nickname}")
            return (False, "Credenciais invalidas.") # Retorna mensagem de credenciais

        # 2. Tenta adicionar ao state_manager
        success_add = state_manager.add_user(nickname, writer)
        if not success_add:
            logging.warning(f"Serviço: Login falhou (já conectado) para {nickname}")
            # Deixa o command_router fechar a conexão
            return (False, "Usuario ja conectado.")

        # 3. Sucesso!
        logging.info(f"Serviço: Login bem-sucedido para {nickname}")
        # Dispara a notificação para amigos
        # (client_handler.broadcast_status_update foi corrigido para ser chamado pelo command_router)
        # asyncio.create_task(client_handler.broadcast_status_update(nickname, UserStatus.ONLINE.value)) # Esta linha deve estar no command_router
        return (True, "Login bem-sucedido!")


class FriendshipService:
    # (search_users, reject_request, get_friends_with_status, get_pending_requests não mudam)
    def search_users(self, query: str, current_user_nickname: str) -> List[UserProfile]:
        # ... (código existente) ...
        logging.info(f"Serviço: Buscando usuários com query '{query}' (por {current_user_nickname})")
        results_dict = db.search_users_db(query, current_user_nickname)
        return [UserProfile(nickname=res['nickname'], name=res['name']) for res in results_dict]

    def reject_request(self, requester_nickname: str, rejector_nickname: str) -> None:
        # ... (código existente) ...
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
        # ... (código existente) ...
        logging.info(f"Serviço: Buscando pedidos pendentes para {nickname}")
        return db.get_pending_friend_requests_db(nickname)


    def send_request(self, requester_nickname: str, target_nickname: str) -> tuple[bool, str]:
        # (Lógica interna quase igual, REMOVE a notificação)
        logging.info(f"Serviço: {requester_nickname} tentando adicionar {target_nickname}")
        if requester_nickname == target_nickname:
             return (False, "Voce não pode adicionar a si mesmo.")

        success, message = db.add_friend_request_db(requester_nickname, target_nickname)

        return success, message

    def accept_request(self, requester_nickname: str, acceptor_nickname: str) -> tuple[bool, Optional[str], Optional[str]]:
        # (Lógica interna quase igual, REMOVE notificações, retorna status para o router)
        logging.info(f"Serviço: {acceptor_nickname} tentando aceitar pedido de {requester_nickname}")
        success = db.update_friend_request_db(requester_nickname, acceptor_nickname, 'accepted')

        if success:
            acceptor_status = state_manager.get_user_status_str(acceptor_nickname)
            requester_status = state_manager.get_user_status_str(requester_nickname)
         
            return (True, requester_status, acceptor_status)
        else:
            return (False, None, None)

# --- Instâncias (sem mudança) ---
auth_service = AuthenticationService()
friend_service = FriendshipService()