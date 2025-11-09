import logging
from xmlrpc.server import SimpleXMLRPCServer
from services import auth_service, friend_service, call_service
from models.StateManager import state_manager
from models.UserStatus import UserStatus

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Esta classe agrupa todos os seus serviços e os expõe para o RMI.
class ApiDispatcher:

    def __init__(self):
        self.auth = auth_service
        self.friend = friend_service
        self.call = call_service

    # --- Métodos de Autenticação (públicos) ---

    def register(self, nickname: str, name: str, password: str) -> tuple[bool, str]:
        return self.auth.register_user(nickname, name, password)

    def login(self, nickname: str, password: str) -> tuple[bool, str, str | None]:
        success, message = self.auth.login_user(nickname, password)
        if success:
            token = state_manager.add_user_token(nickname)
            self.friend.broadcast_status_update(nickname, UserStatus.ONLINE.value)
            return (True, message, token)
        return (False, message, None)

    # --- Métodos que requerem token ---
    def _validate_token(self, token: str) -> str:
        nickname = state_manager.validate_token(token)
        if not nickname:
            raise ValueError("Token de sessão inválido ou expirado.")
        return nickname

    def get_initial_data(self, token: str) -> dict:
        nickname = self._validate_token(token)
        friends = self.friend.get_friends_with_status(nickname)
        pending = self.friend.get_pending_requests(nickname)
        return {'friends': friends, 'pending': pending}

    def search_users(self, token: str, query: str) -> list[dict]:
        nickname = self._validate_token(token)
        profiles = self.friend.search_users(query, nickname)
        return [{'nickname': p.nickname, 'name': p.name} for p in profiles]

    def send_friend_request(self, token: str, target_nickname: str) -> tuple[bool, str]:
        nickname = self._validate_token(token)
        return self.friend.send_request(nickname, target_nickname)

    def accept_friend_request(self, token: str, requester_nickname: str) -> tuple[bool, str | None, str | None]:
        nickname = self._validate_token(token)
        return self.friend.accept_request(requester_nickname, nickname)

    def reject_friend_request(self, token: str, requester_nickname: str) -> None:
        nickname = self._validate_token(token)
        return self.friend.reject_request(requester_nickname, nickname)

    def invite_to_call(self, token: str, target_nickname: str) -> tuple[bool, str]:
        nickname = self._validate_token(token)
        return self.call.invite(nickname, target_nickname)

    def accept_call(self, token: str, caller_nickname: str) -> dict:
        nickname = self._validate_token(token)
        success, message, relay_info = self.call.accept(caller_nickname, nickname)
        
        if success and relay_info:
            self.friend.broadcast_status_update(caller_nickname, UserStatus.IN_CALL.value)
            self.friend.broadcast_status_update(nickname, UserStatus.IN_CALL.value)
            
            relay_info['callee_nickname'] = nickname 
            
            return relay_info 
        
        # Levanta um erro se a aceitação falhar
        raise Exception(message or "Falha ao aceitar chamada.")

    def reject_call(self, token: str, caller_nickname: str) -> bool:
        nickname = self._validate_token(token)
        self.call.reject(caller_nickname, nickname)
        return True

    def end_call(self, token: str) -> bool:
        nickname = self._validate_token(token)

        user = state_manager.get_user(nickname)
        if not user: return False
        
        partner_nickname = user.in_call_with
        self.call.end_call(nickname)
        
        self.friend.broadcast_status_update(nickname, UserStatus.ONLINE.value)
        if partner_nickname:
            self.friend.broadcast_status_update(partner_nickname, UserStatus.ONLINE.value)
            
        return True

    def logout(self, token: str) -> bool:
        nickname = self._validate_token(token)
        
   
        user = state_manager.get_user(nickname)
        if user and user.status == UserStatus.IN_CALL:
            self.end_call(token)
            
        state_manager.remove_user(nickname) 
        self.friend.broadcast_status_update(nickname, "Offline")
        logging.info(f"Usuário '{nickname}' deslogado e token removido.")
        return True

    # Este é o método que o cliente chamará em loop. 
    # Busca todos os eventos pendentes para o usuário e limpa a fila.
    def get_updates(self, token: str) -> list[dict]:
        nickname = self._validate_token(token)
        return state_manager.get_and_clear_events(nickname)

# --- Configuração e Inicialização do Servidor ---
def main():
    server_host = '0.0.0.0'
    server_port = 8888
    
    try:
        server = SimpleXMLRPCServer((server_host, server_port), allow_none=True)
        server.register_introspection_functions()
        
        server.register_instance(ApiDispatcher())
        
        logging.info(f"Servidor RMI (XML-RPC) iniciado em http://{server_host}:{server_port}")
        server.serve_forever()
        
    except KeyboardInterrupt:
        logging.info("Servidor RMI desligado.")
    except Exception as e:
        logging.error(f"Erro fatal no servidor RMI: {e}", exc_info=True)

if __name__ == "__main__":
    main()