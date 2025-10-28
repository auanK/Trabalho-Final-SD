import asyncio
from .UserStatus import UserStatus

# Representa um usuário conectado e seu estado (online, offline, em chamdada).
# Contém informações temporárias e dinâmicas, relevantes apenas durante a sessão ativa
class ConnectedUser:
    def __init__(self, nickname: str, writer: asyncio.StreamWriter):
        self.nickname: str = nickname
        self.writer: asyncio.StreamWriter = writer
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