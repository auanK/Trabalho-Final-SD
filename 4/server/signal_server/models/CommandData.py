from dataclasses import dataclass
from typing import Dict

# Representa os dados essenciais de uma mensagem/comando
@dataclass
class CommandData:
    command: str
    payload: Dict 