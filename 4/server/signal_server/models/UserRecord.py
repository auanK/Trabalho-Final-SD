from dataclasses import dataclass, field
from datetime import datetime

# Representa os dados de um usuário
@dataclass
class UserRecord:
    nickname: str
    name: str
    description: str = ""
    password_hash: str = field(default="DEFAULT_HASH", repr=False) 
    created_at: datetime = field(default_factory=datetime.now)