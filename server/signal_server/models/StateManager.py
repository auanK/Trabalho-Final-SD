import asyncio
import socket 
import threading 

from .ConnectedUser import ConnectedUser

# Classe de gerenciamento que controla o dicionário de todos os usuários conectados
class _StateManager:
    def __init__(self):
        self._connected_users: dict[str, ConnectedUser] = {}
        self._lock = threading.Lock() # Um Lock normal é o correto

    # --- NOVA FUNÇÃO INTERNA ---
    def _get_user_unlocked(self, nickname: str) -> ConnectedUser | None:
        """ 
        Versão interna de get_user que assume que o lock JÁ FOI ADQUIRIDO.
        Não adquire o lock.
        """
        return self._connected_users.get(nickname)

    def add_user(self, nickname: str, conn: socket.socket) -> bool:
        with self._lock: # Adquire o lock
            if nickname in self._connected_users:
                return False
            
            user = ConnectedUser(nickname, conn)
            self._connected_users[nickname] = user
            return True
        # Libera o lock

    def remove_user(self, nickname: str) -> ConnectedUser | None:
        with self._lock: # Adquire o lock
            if nickname in self._connected_users:
                return self._connected_users.pop(nickname)
            return None
        # Libera o lock

    # --- MODIFICADO ---
    def get_user(self, nickname: str) -> ConnectedUser | None:
        with self._lock: # Adquire o lock
            # Chama a versão interna que não tenta readquirir o lock
            return self._get_user_unlocked(nickname) 
        # Libera o lock

    def get_all_users_items(self):
        with self._lock: # Adquire o lock
            return list(self._connected_users.items())
        # Libera o lock

    # --- MODIFICADO ---
    def get_user_status_str(self, nickname: str) -> str:
        with self._lock: # Adquire o lock
            # Chama a versão interna, evitando o lock duplo
            user = self._get_user_unlocked(nickname) 
            if user:
                return user.get_status_str()
            return 'Offline'
        # Libera o lock


# Instância global usada por todos os outros módulos.
state_manager = _StateManager()