import socket 
from .UserStatus import UserStatus

# Representa um usuário conectado e seu estado 
class ConnectedUser:
    def __init__(self, nickname: str, conn: socket.socket):
        self.nickname: str = nickname
        self.conn: socket.socket = conn 
        self.status: UserStatus = UserStatus.ONLINE
        self.in_call_with: str | None = None 

    def start_call(self, partner_nickname: str):
        self.status = UserStatus.IN_CALL
        self.in_call_with = partner_nickname

    def end_call(self):
        self.status = UserStatus.ONLINE
        self.in_call_with = None

    def get_status_str(self) -> str:
        return self.status.value