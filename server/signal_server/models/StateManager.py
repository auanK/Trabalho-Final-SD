from ast import Dict
import logging
import secrets
from models.ConnectedUser import ConnectedUser
from collections import defaultdict
from typing import List, Optional, Tuple
from models.UserStatus import UserStatus

# Gerenciamento de estado do servidor adaptado para RMI
class StateManager:

    def __init__(self):
        self.users: Dict[str, ConnectedUser] = {} # Usuários ativos (nickname -> ConnectedUser)
        self.tokens: Dict[str, str] = {} # Mapeamento de tokens (token -> nickname)
        self.nick_to_token: Dict[str, str] = {} # Mapeamento reverso (nickname -> token)
        self.event_queues: Dict[str, List[Dict]] = defaultdict(list) # Filas de eventos para polling (nickname -> List[EventDict])

    def add_user(self, nickname: str) -> bool:
        if nickname in self.users:
            logging.warning(f"Usuário {nickname} já está no estado.")
            self.users[nickname].status = UserStatus.ONLINE
            return True
        
        self.users[nickname] = ConnectedUser(nickname)
        logging.info(f"Usuário {nickname} adicionado ao estado (Online).")
        return True

    def remove_user(self, nickname: str) -> Optional[ConnectedUser]:
        user = self.users.pop(nickname, None)
        if user:
            token = self.nick_to_token.pop(nickname, None)
            if token:
                self.tokens.pop(token, None)
            logging.info(f"Usuário {nickname} removido do estado.")
        return user

    # Gera e armazena tokens de sessão para usuários
    def add_user_token(self, nickname: str) -> str:
        
        # Se já existir um token, invalida o antigo
        if nickname in self.nick_to_token:
            old_token = self.nick_to_token[nickname]
            self.tokens.pop(old_token, None)
            
        token = secrets.token_hex(24)
        self.tokens[token] = nickname
        self.nick_to_token[nickname] = token
        logging.info(f"Token gerado para {nickname}.")
        return token

    # Valida um token e retorna o nickname associado
    def validate_token(self, token: str) -> Optional[str]:
        return self.tokens.get(token)

    # Adiciona um evento à fila de um usuário.
    def add_event(self, target_nickname: str, event_data: Dict):

        # Só enfileira eventos para usuários que estão online
        target_user = self.users.get(target_nickname)
        if target_user:
            self.event_queues[target_nickname].append(event_data)
            logging.info(f"Evento {event_data.get('command')} enfileirado para {target_nickname}")
        else:
            logging.warning(f"Evento {event_data.get('command')} descartado para {target_nickname} (offline).")

    # Busca e limpa eventos pendentes para um usuário.
    def get_and_clear_events(self, nickname: str) -> List[Dict]:
        if nickname in self.event_queues:
            events = self.event_queues.pop(nickname)
            if events:
                logging.info(f"Entregando {len(events)} evento(s) para {nickname}.")
            return events
        return []

    def get_user(self, nickname: str) -> Optional[ConnectedUser]:
        return self.users.get(nickname)

    def get_all_users_items(self) -> List[Tuple[str, ConnectedUser]]:
        return list(self.users.items())

    def get_user_status_str(self, nickname: str) -> str:
        user = self.get_user(nickname)
        if user:
            return user.status.value
        return UserStatus.OFFLINE.value

# Instância global
state_manager = StateManager()