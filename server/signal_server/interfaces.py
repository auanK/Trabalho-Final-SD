from abc import ABC, abstractmethod
from typing import List, Optional, Tuple, Dict
import asyncio
from models import UserProfile 

# Interface para o Serviço de Autenticação
class IAuthenticationService(ABC):
    
    @abstractmethod
    def register_user(self, nickname: str, name: str, password: str) -> tuple[bool, str]:
        """Tenta registrar um novo usuário."""
        pass

    @abstractmethod
    def login_user(self, nickname: str, password: str, writer: asyncio.StreamWriter) -> tuple[bool, str]:
        """Tenta autenticar um usuário e registrá-lo no estado online."""
        pass

# Interface para o Serviço de Amizade
class IFriendshipService(ABC):

    @abstractmethod
    def search_users(self, query: str, current_user_nickname: str) -> List[UserProfile]:
        """Busca usuários por nickname."""
        pass

    @abstractmethod
    def send_request(self, requester_nickname: str, target_nickname: str) -> tuple[bool, str]:
        """Envia um pedido de amizade."""
        pass

    @abstractmethod
    def accept_request(self, requester_nickname: str, acceptor_nickname: str) -> tuple[bool, Optional[str], Optional[str]]:
        """Aceita um pedido de amizade."""
        pass

    @abstractmethod
    def reject_request(self, requester_nickname: str, rejector_nickname: str) -> None:
        """Rejeita um pedido de amizade."""
        pass

    @abstractmethod
    def get_friends_with_status(self, nickname: str) -> List[Dict]:
        """Busca amigos e seus status online/offline."""
        pass

    @abstractmethod
    def get_pending_requests(self, nickname: str) -> List[str]:
        """Busca pedidos de amizade pendentes."""
        pass

