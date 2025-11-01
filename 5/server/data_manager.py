import logging
import threading
from typing import Dict, List, Set, Optional, Tuple

USERS = {
    "voter1": {"password": "pw1", "role": "voter"},
    "voter2": {"password": "pw2", "role": "voter"},
    "voter3": {"password": "pw3", "role": "voter"},
    "adm1": {"password": "apw1", "role": "admin"},
}

CANDIDATES: List[str] = ["Candidato A", "Candidato B"]

VOTES: Dict[str, int] = {}
VOTED_USERS: Set[str] = set() 

VOTING_ACTIVE = False

LATEST_RESULTS: Dict = {}

_lock = threading.Lock()

def authenticate_user(username: str, password: str) -> Optional[str]:
    user = USERS.get(username)
    if user and user["password"] == password:
        return user["role"]
    return None

def start_voting() -> bool:
    global VOTING_ACTIVE, VOTES, VOTED_USERS, LATEST_RESULTS
    with _lock:
        if not VOTING_ACTIVE:
            VOTING_ACTIVE = True
            VOTES = {candidate: 0 for candidate in CANDIDATES}
            VOTED_USERS = set()
            LATEST_RESULTS = {}
            return True
        return False

def stop_voting() -> bool:
    global VOTING_ACTIVE
    with _lock:
        if VOTING_ACTIVE:
            VOTING_ACTIVE = False
            return True
        return False

def is_voting_active() -> bool:
    with _lock:
        return VOTING_ACTIVE

def get_candidates() -> List[str]:
    with _lock:
        return list(CANDIDATES) 

def add_candidate(candidate_name: str) -> Tuple[bool, str]:
    with _lock:
        if VOTING_ACTIVE:
            return False, "Não é possivel add novos candidatos enquanto uma votação está ocorrendo."
        if candidate_name in CANDIDATES:
            return False, f"Candidato '{candidate_name}' já existe."
        CANDIDATES.append(candidate_name)
        logging.info(f"Candidato adicionado {candidate_name}")
        return True, f"Candidato '{candidate_name}' adicionado."

def remove_candidate(candidate_name: str) -> Tuple[bool, str]:
    with _lock:
        if VOTING_ACTIVE:
            return False, "Não é possivel remover candidatos enquanto uma votação está ocorrendo."
        if candidate_name not in CANDIDATES:
            return False, f"Candidato '{candidate_name}' não encontrado"
        CANDIDATES.remove(candidate_name)
        logging.info(f"Candidato removido: {candidate_name}")
        return True, f"Candidato '{candidate_name}' removido."

def register_vote(username: str, candidate_name: str) -> Tuple[bool, str]:
    with _lock:
        if not VOTING_ACTIVE:
            return False, "Votação ainda não foi iniciada"
        if username in VOTED_USERS:
            return False, "Você ja votou."
        if candidate_name not in CANDIDATES:
            return False, f"Candidato inválido'{candidate_name}'."
        
        VOTES[candidate_name] = VOTES.get(candidate_name, 0) + 1
        VOTED_USERS.add(username)
        logging.info(f"Voto registrado por {username}")
        return True, f"Vote para '{candidate_name}' registrado."

def tally_votes() -> Dict:
    global LATEST_RESULTS
    with _lock:
        if VOTING_ACTIVE:
            return {"error": "votação ainda ativa"}
            
        total_votes = sum(VOTES.values())
        results = {
            "total_votes": total_votes,
            "votes_per_candidate": dict(VOTES), 
            "percentages": {},
            "winner": "No votes cast" if total_votes == 0 else "Tie"
        }
        
        if total_votes > 0:
            max_votes = -1
            winners = []
            for candidate, count in VOTES.items():
                percentage = (count / total_votes) * 100 if total_votes > 0 else 0
                results["percentages"][candidate] = round(percentage, 2)
                if count > max_votes:
                    max_votes = count
                    winners = [candidate]
                elif count == max_votes:
                    winners.append(candidate)
            
            if len(winners) == 1:
                results["winner"] = winners[0]
            elif len(winners) > 1:
                results["winner"] = f"Tie between: {', '.join(winners)}"
        
        logging.info(f"Resultado final: {results}")
        LATEST_RESULTS = results
        return results

def get_latest_results() -> Dict:
    with _lock:
        if VOTING_ACTIVE:
            return {"status": "ERROR", "message": "A votação ainda está em andamento."}
        if not LATEST_RESULTS:
            return {"status": "ERROR", "message": "Nenhuma votação foi concluída ainda."}
        
        return {"status": "OK", "results": LATEST_RESULTS}