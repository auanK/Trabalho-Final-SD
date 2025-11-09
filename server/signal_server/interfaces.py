from abc import ABC, abstractmethod
from typing import List, Optional, Tuple, Dict
from models import UserProfile 

class IAuthenticationService(ABC):
    @abstractmethod
    def register_user(self, nickname: str, name: str, password: str) -> tuple[bool, str]:
        pass

    @abstractmethod
    def login_user(self, nickname: str, password: str) -> tuple[bool, str]:
        pass

class IFriendshipService(ABC):
    @abstractmethod
    def search_users(self, query: str, current_user_nickname: str) -> List[UserProfile]:
        pass
    
    @abstractmethod
    def get_friends_with_status(self, nickname: str) -> List[Dict]:
        pass

class ICallService(ABC):
    @abstractmethod
    def create_call_session(self, caller_nickname: str, callee_nickname: str) -> tuple[bool, str, Optional[dict]]:
        pass