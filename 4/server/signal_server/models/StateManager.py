import socket 
import threading 

from .ConnectedUser import ConnectedUser


# Gerencia o estado dos usuários conectados ao servidor.
class _StateManager:
    def __init__(self):
        self._connected_users: dict[str, ConnectedUser] = {}
        self._lock = threading.Lock()

    def _get_user_unlocked(self, nickname: str) -> ConnectedUser | None:
        return self._connected_users.get(nickname)

    def add_user(self, nickname: str, conn: socket.socket) -> bool:
        with self._lock:
            if nickname in self._connected_users:
                return False
            
            user = ConnectedUser(nickname, conn)
            self._connected_users[nickname] = user
            return True

    def remove_user(self, nickname: str) -> ConnectedUser | None:
        with self._lock:
            if nickname in self._connected_users:
                return self._connected_users.pop(nickname)
            return None

    def get_user(self, nickname: str) -> ConnectedUser | None:
        with self._lock:
            return self._get_user_unlocked(nickname) 

    def get_all_users_items(self):
        with self._lock: 
            return list(self._connected_users.items())

    def get_user_status_str(self, nickname: str) -> str:
        with self._lock: 
            user = self._get_user_unlocked(nickname) 
            if user:
                return user.get_status_str()
            return 'Offline'


# Instância global do gerenciador de estado
state_manager = _StateManager()