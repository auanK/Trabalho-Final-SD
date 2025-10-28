import asyncio

from .ConnectedUser import ConnectedUser

# Classe de gerenciamento que controla o dicionário de todos os usuários conectados
class _StateManager:
    def __init__(self):
        self._connected_users: dict[str, ConnectedUser] = {}

    def add_user(self, nickname: str, writer: asyncio.StreamWriter) -> bool:
        if nickname in self._connected_users:
            return False
        
        user = ConnectedUser(nickname, writer)
        self._connected_users[nickname] = user
        return True

    def remove_user(self, nickname: str) -> ConnectedUser | None:
        if nickname in self._connected_users:
            return self._connected_users.pop(nickname)
        return None

    def get_user(self, nickname: str) -> ConnectedUser | None:
        return self._connected_users.get(nickname)

    def get_all_users_items(self):
        return self._connected_users.items()

    def get_user_status_str(self, nickname: str) -> str:
        user = self.get_user(nickname)
        if user:
            return user.get_status_str()
        return 'Offline'


# Instância global usada por todos os outros módulos.
# So armazena usuarios online ou em ligação.
state_manager = _StateManager()