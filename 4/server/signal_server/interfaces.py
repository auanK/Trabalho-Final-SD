from abc import ABC, abstractmethod
from typing import List, Optional, Tuple, Dict
import socket
from models import UserProfile 

# Interface para o Serviço de Autenticação
class IAuthenticationService(ABC):
    @abstractmethod
    def register_user(self, nickname: str, name: str, password: str) -> tuple[bool, str]:
        pass

    @abstractmethod
    def login_user(self, nickname: str, password: str, writer: socket.socket) -> tuple[bool, str]:
        pass

# Interface para o Serviço de Amizade
class IFriendshipService(ABC):
    @abstractmethod
    def search_users(self, query: str, current_user_nickname: str) -> List[UserProfile]:
        pass

    @abstractmethod
    def send_request(self, requester_nickname: str, target_nickname: str) -> tuple[bool, str]:
        pass

    @abstractmethod
    def accept_request(self, requester_nickname: str, acceptor_nickname: str) -> tuple[bool, Optional[str], Optional[str]]:
        pass

    @abstractmethod
    def reject_request(self, requester_nickname: str, rejector_nickname: str) -> None:
        pass

    @abstractmethod
    def get_friends_with_status(self, nickname: str) -> List[Dict]:
        pass

    @abstractmethod
    def get_pending_requests(self, nickname: str) -> List[str]:
        pass

# Interface para o Serviço de Chamada
class ICallService(ABC):
    @abstractmethod
    def create_call_session(self, caller_nickname: str, callee_nickname: str) -> tuple[bool, str, Optional[dict]]:
        pass