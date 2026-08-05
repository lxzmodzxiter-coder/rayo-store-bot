import sqlite3
from datetime import datetime

DB_NAME = "database.db"


def connect():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        user_id INTEGER PRIMARY KEY,
        first_name TEXT,
        username TEXT,
        balance REAL DEFAULT 0,
        premium INTEGER DEFAULT 0,
        register_date TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admins(
        user_id INTEGER PRIMARY KEY
    )
    """)

    conn.commit()
    conn.close()


# ==========================
# USUARIOS
# ==========================

def register_user(user_id: int, first_name: str, username: str):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT user_id FROM users WHERE user_id=?",
        (user_id,)
    )

    if cursor.fetchone() is None:
        cursor.execute("""
        INSERT INTO users(
            user_id,
            first_name,
            username,
            register_date
        )
        VALUES(?,?,?,?)
        """, (
            user_id,
            first_name,
            username,
            datetime.now().strftime("%d/%m/%Y %H:%M")
        ))

    conn.commit()
    conn.close()


def get_user(user_id: int):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE user_id=?",
        (user_id,)
    )

    data = cursor.fetchone()

    conn.close()

    return data


def get_balance(user_id: int):

    user = get_user(user_id)

    if user:
        return float(user["balance"])

    return 0.0


def add_balance(user_id: int, amount: float):

    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE users
    SET balance = balance + ?
    WHERE user_id=?
    """, (
        amount,
        user_id
    ))

    conn.commit()
    conn.close()


def remove_balance(user_id: int, amount: float):

    current = get_balance(user_id)

    new_balance = current - amount

    if new_balance < 0:
        new_balance = 0

    conn = connect()

    cursor = conn.cursor()

    cursor.execute("""
    UPDATE users
    SET balance=?
    WHERE user_id=?
    """, (
        new_balance,
        user_id
    ))

    conn.commit()
    conn.close()


# ==========================
# PREMIUM
# ==========================

def is_premium(user_id: int):

    user = get_user(user_id)

    if not user:
        return False

    return bool(user["premium"])


def set_premium(user_id: int, status: bool):

    conn = connect()

    cursor = conn.cursor()

    cursor.execute("""
    UPDATE users
    SET premium=?
    WHERE user_id=?
    """, (
        1 if status else 0,
        user_id
    ))

    conn.commit()

    conn.close()


# ==========================
# ADMINS
# ==========================

def add_admin(user_id: int):

    conn = connect()

    cursor = conn.cursor()

    cursor.execute("""
    INSERT OR IGNORE INTO admins(user_id)
    VALUES(?)
    """, (
        user_id,
    ))

    conn.commit()

    conn.close()


def remove_admin(user_id: int):

    conn = connect()

    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM admins WHERE user_id=?",
        (user_id,)
    )

    conn.commit()

    conn.close()


def is_admin(user_id: int):

    conn = connect()

    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM admins WHERE user_id=?",
        (user_id,)
    )

    data = cursor.fetchone()

    conn.close()

    return data is not None


# ==========================
# ESTADÍSTICAS
# ==========================

def total_users():

    conn = connect()

    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM users"
    )

    total = cursor.fetchone()[0]

    conn.close()

    return total
