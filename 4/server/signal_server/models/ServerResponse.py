from dataclasses import dataclass
from typing import Optional, Dict

# Representa uma resposta do servidor
@dataclass
class ServerResponse:
    command: str
    payload: Dict
    success: Optional[bool] = None
    message: Optional[str] = None
