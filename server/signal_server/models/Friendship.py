from dataclasses import dataclass

# Representa uma relação de amizade
@dataclass
class Friendship:
    user_a: str 
    user_b: str 
    status: str