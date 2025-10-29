from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class UserRecord:
    """Representa os dados de um usuário, similar ao POJO pedido."""
    nickname: str
    name: str
    description: str = ""
    password_hash: str = field(default="DEFAULT_HASH", repr=False) 
    created_at: datetime = field(default_factory=datetime.now)