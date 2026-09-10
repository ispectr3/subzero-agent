import os
import sqlite3
from typing import Optional

DEFAULT_SUBZERO_DIR = os.path.expanduser("~/.subzero")
DEFAULT_DB_PATH = os.path.join(DEFAULT_SUBZERO_DIR, "finance.db")


class Database:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._shared_conn: Optional[sqlite3.Connection] = None

        if self.db_path == ":memory:":
            self._shared_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._shared_conn.row_factory = sqlite3.Row
            self._shared_conn.execute("PRAGMA foreign_keys = ON;")
        else:
            db_dir = os.path.dirname(os.path.abspath(self.db_path))
            os.makedirs(db_dir, exist_ok=True)

        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        """Retorna uma conexão ativa com o SQLite com chaves estrangeiras e Row factory."""
        if self._shared_conn:
            return self._shared_conn

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        if self.db_path != ":memory:":
            conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    def _init_db(self):
        """Cria e migra tabelas essenciais para o funcionamento do SubZero."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Categorias
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    type TEXT CHECK(type IN ('INCOME', 'EXPENSE')) NOT NULL,
                    icon TEXT DEFAULT ''
                );
            """)

            # Transações
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    amount REAL NOT NULL CHECK(amount > 0),
                    category_id INTEGER NOT NULL,
                    description TEXT NOT NULL,
                    date TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE RESTRICT
                );
            """)

            # Assinaturas / Recorrências
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    amount REAL NOT NULL,
                    cadence TEXT CHECK(cadence IN ('MONTHLY', 'YEARLY', 'WEEKLY')) NOT NULL DEFAULT 'MONTHLY',
                    status TEXT CHECK(status IN ('ACTIVE', 'CANCELLED', 'PAUSED')) NOT NULL DEFAULT 'ACTIVE',
                    category_name TEXT DEFAULT 'Assinaturas & Serviços',
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    charges_count INTEGER DEFAULT 1,
                    previous_amount REAL,
                    notes TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Anomalias & Cobranças Duplicadas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS anomalies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    severity TEXT NOT NULL DEFAULT 'MEDIUM',
                    merchant TEXT NOT NULL,
                    description TEXT NOT NULL,
                    amount REAL NOT NULL,
                    date TEXT NOT NULL,
                    resolved INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Índices para performance instantânea
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_desc ON transactions(description);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_anomalies_resolved ON anomalies(resolved);")

            # Categorias padrão
            cursor.execute("SELECT COUNT(*) FROM categories;")
            if cursor.fetchone()[0] == 0:
                default_categories = [
                    ("Salário", "INCOME", "💼"),
                    ("Freelance & Contratos", "INCOME", "💻"),
                    ("Investimentos & Dividendos", "INCOME", "📈"),
                    ("Assinaturas & Serviços", "EXPENSE", "💳"),
                    ("Alimentação & Mercado", "EXPENSE", "🍔"),
                    ("Moradia & Contas", "EXPENSE", "🏠"),
                    ("Transporte", "EXPENSE", "🚗"),
                    ("Lazer & Entretenimento", "EXPENSE", "🍿"),
                    ("Saúde & Bem-estar", "EXPENSE", "💊"),
                    ("Educação & Cursos", "EXPENSE", "📚"),
                    ("Outros", "EXPENSE", "📦"),
                ]
                cursor.executemany(
                    "INSERT INTO categories (name, type, icon) VALUES (?, ?, ?);",
                    default_categories
                )

            conn.commit()
