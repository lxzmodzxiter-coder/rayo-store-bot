import sqlite3
from datetime import datetime

DB_NAME = "rayo_fix_store.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Tabla de Usuarios
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        name TEXT,
        username TEXT,
        registered_at TEXT,
        balance REAL DEFAULT 0.0,
        is_premium INTEGER DEFAULT 0,
        purchases_count INTEGER DEFAULT 0,
        invited_by INTEGER,
        is_banned INTEGER DEFAULT 0
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
        status TEXT,
        image_url TEXT
    )
    """)
    
    # Tabla de Compras / Historial
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        product_name TEXT,
        price REAL,
        date TEXT,
        status TEXT
    )
    """)
    
    # Tabla de Pagos / Recargas pendientes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        method TEXT,
        proof TEXT,
        status TEXT,
        date TEXT
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
    
    # Tabla de Roles (Admins)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admins (
        user_id INTEGER PRIMARY KEY
    )
    """)

    # Tabla de Configuraciones del Sistema (Owner Panel)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)
    
    conn.commit()
    conn.close()

def db_get_user(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, username, registered_at, balance, is_premium, purchases_count, invited_by, is_banned FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def db_register_user(user_id: int, name: str, username: str, invited_by: int = None):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    if not cursor.fetchone():
        reg_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO users (id, name, username, registered_at, balance, is_premium, purchases_count, invited_by, is_banned) VALUES (?, ?, ?, ?, 0.0, 0, 0, ?, 0)",
            (user_id, name, username or "Sin username", reg_date, invited_by)
        )
        conn.commit()
    conn.close()
    
