import os
import sqlite3
import logging
import hashlib

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '', 'db', 'voip.db')) 

# Registra um novo usuário no banco de dados.
def register_user(nickname, name, password):
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (nickname, name, password_hash, created_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
            (nickname, name, password_hash)
        )
        conn.commit()
        logging.info(f"Novo usuario registrado: {nickname}")
        return (True, "Registo concluido com sucesso!")
    except sqlite3.IntegrityError:
        logging.warning(f"Tentativa de registro falhou: Nickname '{nickname}' ja existe.")
        return (False, "Nickname ja existe.")
    except sqlite3.Error as e:
        logging.error(f"Erro no banco de dados ao registrar {nickname}: {e}")
        return (False, f"Erro interno do servidor: {e}")
    finally:
        if conn:
            conn.close()

# Verifica as credenciais no banco de dados SQLite.
def check_login(nickname, password):
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT nickname FROM users WHERE nickname = ? AND password_hash = ?", (nickname, password_hash))
        user = cursor.fetchone()
        return True if user is not None else False
    except sqlite3.Error as e:
        logging.error(f"Erro no banco de dados ao autenticar {nickname}: {e}")
        return False
    finally:
        if conn:
            conn.close()

# Procura por usuários no DB, excluindo o próprio usuário.
def search_users_db(query, current_user_nickname):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT nickname, name FROM users WHERE nickname LIKE ? AND nickname != ?", 
            (f'{query}%', current_user_nickname)
        )
        results = [{'nickname': row[0], 'name': row[1]} for row in cursor.fetchall()]
        return results
    except sqlite3.Error as e:
        logging.error(f"Erro no banco de dados ao procurar usuários: {e}")
        return []

# Adiciona um pedido de amizade com status pendente.
def add_friend_request_db(requester, target):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM friendships WHERE (user_nickname_a = ? AND user_nickname_b = ?) OR (user_nickname_a = ? AND user_nickname_b = ?)",
            (requester, target, target, requester)
        )
        if cursor.fetchone():
            return (False, "Já existe uma relação (amigo ou pendente).")
        cursor.execute(
            "INSERT INTO friendships (user_nickname_a, user_nickname_b, status, created_at) VALUES (?, ?, 'pending', CURRENT_TIMESTAMP)",
            (requester, target)
        )
        conn.commit()
        logging.info(f"Novo pedido de amizade: {requester} -> {target}")
        return (True, "Pedido de amizade enviado.")
    except sqlite3.Error as e:
        logging.error(f"Erro no banco de dados ao adicionar amigo: {e}")
        return (False, f"Erro interno do servidor: {e}")
    finally:
        if conn:
            conn.close()

# Atualiza um pedido de amizade pendente para aceito ou rejeitado.
def update_friend_request_db(requester, acceptor, new_status):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE friendships SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE user_nickname_a = ? AND user_nickname_b = ? AND status = 'pending'",
            (new_status, requester, acceptor)
        )
        conn.commit()
        if cursor.rowcount > 0:
            logging.info(f"Pedido de amizade {requester} -> {acceptor} atualizado para {new_status}.")
            return True
        else:
            logging.warning(f"Nenhum pedido pendente encontrado para {requester} -> {acceptor}.")
            return False
    except sqlite3.Error as e:
        logging.error(f"Erro no banco de dados ao aceitar amigo: {e}")
        return False
    finally:
        if conn:
            conn.close()

#  Retorna uma lista de todos os nicknames que são amigos de um determinado usuário.
def get_friends_list_db(nickname):
    conn = None
    friends = []
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_nickname_b FROM friendships WHERE user_nickname_a = ? AND status = 'accepted'", (nickname,)
        )
        friends.extend([row[0] for row in cursor.fetchall()])
        cursor.execute(
            "SELECT user_nickname_a FROM friendships WHERE user_nickname_b = ? AND status = 'accepted'", (nickname,)
        )
        friends.extend([row[0] for row in cursor.fetchall()])
        return list(set(friends))
    except sqlite3.Error as e:
        logging.error(f"Erro no banco de dados ao buscar amigos de {nickname}: {e}")
        return []
    finally:
        if conn:
            conn.close()

# Retorna uma lista de nicknames que enviaram pedidos de amizade pendentes.
def get_pending_friend_requests_db(target_nickname):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_nickname_a FROM friendships WHERE user_nickname_b = ? AND status = 'pending'",
            (target_nickname,)
        )
        requesters = [row[0] for row in cursor.fetchall()]
        return requesters
    except sqlite3.Error as e:
        logging.error(f"Erro no banco de dados ao buscar pedidos pendentes de {target_nickname}: {e}")
        return []
    finally:
        if conn:
            conn.close()