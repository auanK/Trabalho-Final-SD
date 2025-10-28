from dataclasses import dataclass

# Representa o perfil básico de um usuário (dados do DB)
# É útil para operações como buscar usuários, exibir informações de perfil, ou popular a lista de amigos com nomes. 
@dataclass
class UserProfile:
    nickname: str
    name: str
    