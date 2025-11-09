from pyparsing import Optional 
from .UserStatus import UserStatus

# Representa um usuário conectado.
class ConnectedUser:
    def __init__(self, nickname: str):
        self.nickname: str = nickname
        self.status: UserStatus = UserStatus.ONLINE
        self.in_call_with: Optional[str] = None

    def start_call(self, partner_nickname: str):
        self.status = UserStatus.IN_CALL
        self.in_call_with = partner_nickname

    def end_call(self):
        self.status = UserStatus.ONLINE
        self.in_call_with = None