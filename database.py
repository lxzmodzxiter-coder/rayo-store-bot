import sqlite3
import datetime
from contextlib import contextmanager

DB_NAME = "store.db"

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Tabla de Usuarios
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                balance REAL DEFAULT 0.0,
                membership TEXT DEFAULT 'Inactiva',
                membership_expiry TEXT,
                banned INTEGER DEFAULT 0,
                created_at TEXT
            )
        """)
        
        # Tabla de Productos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                name TEXT,
                description TEXT,
                price REAL,
                stock INTEGER,
                status TEXT DEFAULT '🟢 Disponible'
            )
        """)
        
        # Tabla de Compras
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                product_name TEXT,
                price REAL,
                date TEXT,
                status TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        """)
        
        # Tabla de Pagos / Recargas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                method TEXT,
                status TEXT DEFAULT 'PENDIENTE',
                date TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        """)
        
        # Tabla de Cupones
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS coupons (
                code TEXT PRIMARY KEY,
                discount_type TEXT,
                value REAL,
                uses_left INTEGER,
                expires_at TEXT
            )
        """)
        
        # Tabla de Administradores y Permisos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                permissions TEXT
            )
        """)
        
        # Tabla de Transacciones de Saldo
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS credit_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                old_balance REAL,
                new_balance REAL,
                type TEXT,
                admin_id INTEGER,
                date TEXT
            )
        """)
        
        # Tabla de Logs de Auditoría
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor_id INTEGER,
                action TEXT,
                target_id INTEGER,
                details TEXT,
                date TEXT
            )
        """)
        
        # Tabla de Configuración
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('maintenance', 'OFF')")
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_banned ON users(banned)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_cat ON products(category)")

def get_user(user_id: int):
    with get_db() as conn:
        return conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()

def register_user(user_id: int, username: str, full_name: str):
    with get_db() as conn:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("""
            INSERT INTO users (user_id, username, full_name, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET username=excluded.username, full_name=excluded.full_name
        """, (user_id, username, full_name, now))

def update_balance(user_id: int, amount: float, tx_type: str, admin_id: int = None):
    with get_db() as conn:
        user = conn.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if not user:
            return False, "Usuario no encontrado"
        old_bal = user["balance"]
        new_bal = old_bal + amount
        if new_bal < 0:
            return False, "Saldo insuficiente / Negativo no permitido"
        
        conn.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_bal, user_id))
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("""
            INSERT INTO credit_transactions (user_id, amount, old_balance, new_balance, type, admin_id, date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, amount, old_bal, new_bal, tx_type, admin_id, now))
        return True, new_bal

def log_action(actor_id: int, action: str, target_id: int, details: str):
    with get_db() as conn:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("""
            INSERT INTO admin_logs (actor_id, action, target_id, details, date)
            VALUES (?, ?, ?, ?, ?)
        """, (actor_id, action, target_id, details, now))

def get_setting(key: str):
    with get_db() as conn:
        res = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return res["value"] if res else "OFF"

def set_setting(key: str, value: str):
    with get_db() as conn:
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        
