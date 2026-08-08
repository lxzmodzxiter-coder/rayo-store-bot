import sqlite3
import datetime
import os

DB_NAME = "store.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            username TEXT,
            registered_at TEXT,
            balance REAL DEFAULT 0.0,
            premium TEXT DEFAULT NULL,
            purchases_count INTEGER DEFAULT 0,
            total_spent REAL DEFAULT 0.0,
            referred_by INTEGER DEFAULT NULL,
            status TEXT DEFAULT 'ACTIVE',
            last_activity TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            name TEXT,
            description TEXT,
            price REAL,
            premium_price REAL,
            stock TEXT,
            status TEXT DEFAULT 'ACTIVE',
            is_offer INTEGER DEFAULT 0,
            image_url TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_id INTEGER,
            product_name TEXT,
            price REAL,
            discount REAL,
            total REAL,
            coupon TEXT,
            purchased_at TEXT,
            status TEXT DEFAULT 'COMPLETED'
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            method TEXT,
            voucher_id TEXT,
            status TEXT DEFAULT 'PENDING',
            created_at TEXT,
            admin_id INTEGER DEFAULT NULL,
            rejection_reason TEXT DEFAULT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS coupons (
            code TEXT PRIMARY KEY,
            type TEXT,
            value REAL,
            uses_left INTEGER,
            expires_at TEXT,
            status TEXT DEFAULT 'ACTIVE'
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS coupon_usage (
            user_id INTEGER,
            code TEXT,
            PRIMARY KEY (user_id, code)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY,
            role TEXT DEFAULT 'ADMIN',
            added_by INTEGER,
            added_at TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            inviter_id INTEGER,
            invited_id INTEGER,
            reward REAL,
            status TEXT DEFAULT 'COMPLETED',
            PRIMARY KEY (inviter_id, invited_id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            user_id INTEGER,
            product_id INTEGER,
            PRIMARY KEY (user_id, product_id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            details TEXT,
            created_at TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message TEXT,
            status TEXT DEFAULT 'OPEN',
            created_at TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cart (
            user_id INTEGER,
            product_id INTEGER,
            quantity INTEGER DEFAULT 1,
            PRIMARY KEY (user_id, product_id)
        )
    """)
    
    conn.commit()
    conn.close()
    
init_db()

def db_get_user(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def db_upsert_user(user_id, name, username, referrer_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.datetime.now().isoformat()
    user = db_get_user(user_id)
    if not user:
        cursor.execute("""
            INSERT INTO users (user_id, name, username, registered_at, balance, status, last_activity, referred_by)
            VALUES (?, ?, ?, ?, 0.0, 'ACTIVE', ?, ?)
        """, (user_id, name, username, now, now, referrer_id))
        if referrer_id and referrer_id != user_id:
            cursor.execute("INSERT OR IGNORE INTO referrals (inviter_id, invited_id, reward) VALUES (?, ?, 1.0)", (referrer_id, user_id))
            cursor.execute("UPDATE users SET balance = balance + 1.0 WHERE user_id = ?", (referrer_id,))
    else:
        cursor.execute("UPDATE users SET name = ?, username = ?, last_activity = ? WHERE user_id = ?", (name, username, now, user_id))
    conn.commit()
    conn.close()

def db_log_action(user_id, action, details):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.datetime.now().isoformat()
    cursor.execute("INSERT INTO logs (user_id, action, details, created_at) VALUES (?, ?, ?, ?)", (user_id, action, details, now))
    conn.commit()
    conn.close()

def db_get_setting(key, default=""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row["value"] if row else default

def db_set_setting(key, value):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()
    
