from dataclasses import dataclass

# Representa o perfil de um usuário 
@dataclass
class UserProfile:
    nickname: str
    name: str
    