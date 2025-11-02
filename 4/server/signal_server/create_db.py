import os
import sqlite3
import logging

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '', 'db', 'voip.db'))
DB_DIR = os.path.dirname(DB_PATH)

SQL_CREATE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    nickname TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

SQL_CREATE_FRIENDSHIPS_TABLE = """
CREATE TABLE IF NOT EXISTS friendships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_nickname_a TEXT NOT NULL,
    user_nickname_b TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('pending', 'accepted', 'rejected')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (user_nickname_a) REFERENCES users(nickname),
    FOREIGN KEY (user_nickname_b) REFERENCES users(nickname),
    UNIQUE(user_nickname_a, user_nickname_b)
);
"""

def setup_database():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
    
    try:
        if not os.path.exists(DB_DIR):
            logging.info(f"Criando diretório do banco de dados em: {DB_DIR}")
            os.makedirs(DB_DIR)
        else:
            logging.info(f"Diretório do banco de dados já existe: {DB_DIR}")
    except OSError as e:
        logging.error(f"Falha ao criar diretório do banco de dados: {e}")
        return

    conn = None
    try:
        logging.info(f"Conectando e criando banco de dados em: {DB_PATH}")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        logging.info("Criando tabela 'users'...")
        cursor.execute(SQL_CREATE_USERS_TABLE)
        
        logging.info("Criando tabela 'friendships'...")
        cursor.execute(SQL_CREATE_FRIENDSHIPS_TABLE)
        
        conn.commit()
        logging.info("✅ Banco de dados e tabelas criados com sucesso!")
        
    except sqlite3.Error as e:
        logging.error(f"Erro ao configurar o banco de dados: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    setup_database()