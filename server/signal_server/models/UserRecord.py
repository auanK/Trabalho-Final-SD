# Em models/UserRecord.py (ou similar)
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class UserRecord:
    """Representa os dados de um usuário, similar ao POJO pedido."""
    nickname: str
    name: str
    description: str = "" # Usaremos este como o terceiro atributo para o stream
    # Atributos com valor padrão, não usados diretamente nos streams Q2/Q3
    password_hash: str = field(default="DEFAULT_HASH", repr=False) # repr=False para não mostrar em prints
    created_at: datetime = field(default_factory=datetime.now)