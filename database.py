# ============================================================
# DATABASE.PY
# RAYO FIX STORE
# Base de Datos Profesional
# ============================================================

import sqlite3
from contextlib import closing
from datetime import datetime

DB_NAME = "database.db"


# ============================================================
# CONEXIÓN
# ============================================================

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# ============================================================
# CREAR TODAS LAS TABLAS
# ============================================================

def init_db():

    with closing(get_connection()) as conn:

        cursor = conn.cursor()

        # =====================================================
        # USUARIOS
        # =====================================================

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users(

            user_id INTEGER PRIMARY KEY,

            first_name TEXT NOT NULL,

            username TEXT,

            balance REAL DEFAULT 0,

            premium INTEGER DEFAULT 0,

            register_date TEXT,

            total_purchases INTEGER DEFAULT 0,

            total_spent REAL DEFAULT 0,

            last_purchase TEXT

        )
        """)

        # =====================================================
        # ADMINISTRADORES
        # =====================================================

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins(

            user_id INTEGER PRIMARY KEY,

            added_date TEXT

        )
        """)

        # =====================================================
        # PRODUCTOS
        # =====================================================

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS products(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT,

            category TEXT,

            description TEXT,

            price REAL,

            stock INTEGER,

            image TEXT,

            status INTEGER DEFAULT 1

        )
        """)

        # =====================================================
        # CUPONES
        # =====================================================

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS coupons(

            code TEXT PRIMARY KEY,

            amount REAL,

            uses INTEGER,

            used INTEGER DEFAULT 0,

            created_date TEXT

        )
        """)

        # =====================================================
        # COMPRAS
        # =====================================================

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS purchases(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER,

            product_name TEXT,

            amount REAL,

            purchase_date TEXT

        )
        """)

        # =====================================================
        # RECARGAS
        # =====================================================

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS recharges(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER,

            amount REAL,

            method TEXT,

            status TEXT,

            recharge_date TEXT

        )
        """)

        # =====================================================
        # CONFIGURACIÓN
        # =====================================================

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings(

            key TEXT PRIMARY KEY,

            value TEXT

        )
        """)

        conn.commit()

    print("✅ Base de datos iniciada correctamente.")
    # ============================================================
# USUARIOS
# ============================================================

def user_exists(user_id: int) -> bool:

    with closing(get_connection()) as conn:

        cursor = conn.cursor()

        cursor.execute(
            "SELECT 1 FROM users WHERE user_id=?",
            (user_id,)
        )

        return cursor.fetchone() is not None


def register_user(user_id: int, first_name: str, username: str = None):

    if user_exists(user_id):
        return

    with closing(get_connection()) as conn:

        cursor = conn.cursor()

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
            datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        ))

        conn.commit()


def get_user(user_id: int):

    with closing(get_connection()) as conn:

        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE user_id=?",
            (user_id,)
        )

        return cursor.fetchone()


def update_username(user_id: int, username: str):

    with closing(get_connection()) as conn:

        cursor = conn.cursor()

        cursor.execute("""
        UPDATE users
        SET username=?
        WHERE user_id=?
        """, (
            username,
            user_id
        ))

        conn.commit()


def update_first_name(user_id: int, first_name: str):

    with closing(get_connection()) as conn:

        cursor = conn.cursor()

        cursor.execute("""
        UPDATE users
        SET first_name=?
        WHERE user_id=?
        """, (
            first_name,
            user_id
        ))

        conn.commit()


def delete_user(user_id: int):

    with closing(get_connection()) as conn:

        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM users WHERE user_id=?",
            (user_id,)
        )

        conn.commit()


# ============================================================
# SALDO
# ============================================================

def get_balance(user_id: int) -> float:

    user = get_user(user_id)

    if user is None:
        return 0.0

    return float(user["balance"])


def set_balance(user_id: int, amount: float):

    with closing(get_connection()) as conn:

        cursor = conn.cursor()

        cursor.execute("""
        UPDATE users
        SET balance=?
        WHERE user_id=?
        """, (
            amount,
            user_id
        ))

        conn.commit()


def add_balance(user_id: int, amount: float):

    balance = get_balance(user_id)

    set_balance(
        user_id,
        balance + amount
    )


def remove_balance(user_id: int, amount: float):

    balance = get_balance(user_id)

    new_balance = balance - amount

    if new_balance < 0:
        new_balance = 0

    set_balance(
        user_id,
        new_balance
    )


# ============================================================
# PREMIUM
# ============================================================

def is_premium(user_id: int) -> bool:

    user = get_user(user_id)

    if user is None:
        return False

    return bool(user["premium"])


def set_premium(user_id: int, value: bool):

    with closing(get_connection()) as conn:

        cursor = conn.cursor()

        cursor.execute("""
        UPDATE users
        SET premium=?
        WHERE user_id=?
        """, (
            1 if value else 0,
            user_id
        ))

        conn.commit()


# ============================================================
# ESTADÍSTICAS DEL USUARIO
# ============================================================

def add_purchase_stats(user_id: int, amount: float):

    with closing(get_connection()) as conn:

        cursor = conn.cursor()

        cursor.execute("""
        UPDATE users

        SET

        total_purchases = total_purchases + 1,

        total_spent = total_spent + ?,

        last_purchase = ?

        WHERE user_id=?

        """, (
            amount,
            datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            user_id
        ))

        conn.commit()


def get_total_spent(user_id: int):

    user = get_user(user_id)

    if user is None:
        return 0

    return float(user["total_spent"])


def get_total_purchases(user_id: int):

    user = get_user(user_id)

    if user is None:
        return 0

    return int(user["total_purchases"])
# ============================================================
# ADMINISTRADORES
# ============================================================

def add_admin(user_id: int):

    with closing(get_connection()) as conn:

        cursor = conn.cursor()

        cursor.execute("""
        INSERT OR IGNORE INTO admins(
            user_id,
            added_date
        )
        VALUES(?,?)
        """, (
            user_id,
            datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        ))

        conn.commit()


def remove_admin(user_id: int):

    with closing(get_connection()) as conn:

        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM admins WHERE user_id=?",
            (user_id,)
        )

        conn.commit()


def is_admin(user_id: int) -> bool:

    with closing(get_connection()) as conn:

        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM admins WHERE user_id=?",
            (user_id,)
        )

        return cursor.fetchone() is not None


def get_admins():

    with closing(get_connection()) as conn:

        cursor = conn.cursor()

        cursor.execute("""
        SELECT *
        FROM admins
        ORDER BY added_date DESC
        """)

        return cursor.fetchall()


# ============================================================
# PRODUCTOS
# ============================================================

def add_product(
    name: str,
    category: str,
    description: str,
    price: float,
    stock: int,
    image: str = ""
):

    with closing(get_connection()) as conn:

        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO products(

            name,
            category,
            description,
            price,
            stock,
            image

        )
        VALUES(?,?,?,?,?,?)
        """, (

            name,
            category,
            description,
            price,
            stock,
            image

        ))

        conn.commit()


def get_products():

    with closing(get_connection()) as conn:

        cursor = conn.cursor()

        cursor.execute("""
        SELECT *
        FROM products
        WHERE status=1
        ORDER BY category,name
        """)

        return cursor.fetchall()


def get_products_by_category(category: str):

    with closing(get_connection()) as conn:

        cursor = conn.cursor()

        cursor.execute("""
        SELECT *
        FROM products
        WHERE category=?
        AND status=1
        ORDER BY name
        """, (
            category,
        ))

        return cursor.fetchall()


def get_product(product_id: int):

    with closing(get_connection()) as conn:

        cursor = conn.cursor()

        cursor.execute("""
        SELECT *
        FROM products
        WHERE id=?
        """, (
            product_id,
        ))

        return cursor.fetchone()


def update_product_price(product_id: int, price: float):

    with closing(get_connection()) as conn:

        cursor = conn.cursor()

        cursor.execute("""
        UPDATE products
        SET price=?
        WHERE id=?
        """, (
            price,
            product_id
        ))

        conn.commit()


def update_product_stock(product_id: int, stock: int):

    with closing(get_connection()) as conn:

        cursor = conn.cursor()

        cursor.execute("""
        UPDATE products
        SET stock=?
        WHERE id=?
        """, (
            stock,
            product_id
        ))

        conn.commit()


def update_product_description(product_id: int, description: str):

    with closing(get_connection()) as conn:

        cursor = conn.cursor()

        cursor.execute("""
        UPDATE products
        SET description=?
        WHERE id=?
        """, (
            description,
            product_id
        ))

        conn.commit()


def delete_product(product_id: int):

    with closing(get_connection()) as conn:

        cursor = conn.cursor()

        cursor.execute("""
        UPDATE products
        SET status=0
        WHERE id=?
        """, (
            product_id,
        ))

        conn.commit()


def product_exists(product_id: int):

    return get_product(product_id) is not None    
# ============================================================
# RECARGAS
# ============================================================

def add_recharge(
    user_id: int,
    amount: float,
    method: str,
    status: str = "PENDIENTE"
):

    with closing(get_connection()) as conn:

        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO recharges(
            user_id,
            amount,
            method,
            status,
            recharge_date
        )
        VALUES(?,?,?,?,?)
        """, (
            user_id,
            amount,
            method,
            status,
            datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        ))

        conn.commit()


def get_recharges(user_id: int):

    with closing(get_connection()) as conn:

        cursor = conn.cursor()

        cursor.execute("""
        SELECT *
        FROM recharges
        WHERE user_id=?
        ORDER BY id DESC
        """, (
            user_id,
        ))

        return cursor.fetchall()


def update_recharge_status(recharge_id: int, status: str):

    with closing(get_connection()) as conn:

        cursor = conn.cursor()

        cursor.execute("""
        UPDATE recharges
        SET status=?
        WHERE id=?
        """, (
            status,
            recharge_id
        ))

        conn.commit()


# ============================================================
# CUPONES
# ============================================================

def create_coupon(
    code: str,
    amount: float,
    uses: int
):

    with closing(get_connection()) as conn:

        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO coupons(
            code,
            amount,
            uses,
            created_date
        )
        VALUES(?,?,?,?)
        """, (
            code.upper(),
            amount,
            uses,
            datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        ))

        conn.commit()


def get_coupon(code: str):

    with closing(get_connection()) as conn:

        cursor = conn.cursor()

        cursor.execute("""
        SELECT *
        FROM coupons
        WHERE code=?
        """, (
            code.upper(),
        ))

        return cursor.fetchone()


def redeem_coupon(code: str):

    coupon = get_coupon(code)

    if coupon is None:
        return False

    if coupon["used"] >= coupon["uses"]:
        return False

    with closing(get_connection()) as conn:

        cursor = conn.cursor()

        cursor.execute("""
        UPDATE coupons
        SET used = used + 1
        WHERE code=?
        """, (
            code.upper(),
        ))

        conn.commit()

    return True


def delete_coupon(code: str):

    with closing(get_connection()) as conn:

        cursor = conn.cursor()

        cursor.execute("""
        DELETE FROM coupons
        WHERE code=?
        """, (
            code.upper(),
        ))

        conn.commit()


# ============================================================
# COMPRAS
# ============================================================

def add_purchase(
    user_id: int,
    product_name: str,
    amount: float
):

    with closing(get_connection()) as conn:

        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO purchases(
            user_id,
            product_name,
            amount,
            purchase_date
        )
        VALUES(?,?,?,?)
        """, (
            user_id,
            product_name,
            amount,
            datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        ))

        conn.commit()

    add_purchase_stats(user_id, amount)


def get_purchases(user_id: int):

    with closing(get_connection()) as conn:

        cursor = conn.cursor()

        cursor.execute("""
        SELECT *
        FROM purchases
        WHERE user_id=?
        ORDER BY id DESC
        """, (
            user_id,
        ))

        return cursor.fetchall()


def purchase_product(
    user_id: int,
    product_id: int
):

    product = get_product(product_id)

    if product is None:
        return False, "Producto inexistente."

    if product["status"] == 0:
        return False, "Producto no disponible."

    if product["stock"] <= 0:
        return False, "Sin stock."

    balance = get_balance(user_id)

    if balance < product["price"]:
        return False, "Saldo insuficiente."

    remove_balance(
        user_id,
        product["price"]
    )

    update_product_stock(
        product_id,
        product["stock"] - 1
    )

    add_purchase(
        user_id,
        product["name"],
        product["price"]
    )

    return True, "Compra realizada correctamente."
    # ============================================================
# ESTADÍSTICAS GENERALES
# ============================================================

def total_users():

    with closing(get_connection()) as conn:

        cursor = conn.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM users"
        )

        return cursor.fetchone()[0]


def total_admins():

    with closing(get_connection()) as conn:

        cursor = conn.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM admins"
        )

        return cursor.fetchone()[0]


def total_products():

    with closing(get_connection()) as conn:

        cursor = conn.cursor()

        cursor.execute("""
        SELECT COUNT(*)
        FROM products
        WHERE status=1
        """)

        return cursor.fetchone()[0]


def total_sales():

    with closing(get_connection()) as conn:

        cursor = conn.cursor()

        cursor.execute("""
        SELECT COUNT(*)
        FROM purchases
        """)

        return cursor.fetchone()[0]


def total_income():

    with closing(get_connection()) as conn:

        cursor = conn.cursor()

        cursor.execute("""
        SELECT COALESCE(SUM(amount),0)
        FROM purchases
        """)

        return float(cursor.fetchone()[0])


# ============================================================
# BÚSQUEDA
# ============================================================

def search_users(search: str):

    with closing(get_connection()) as conn:

        cursor = conn.cursor()

        cursor.execute("""
        SELECT *
        FROM users

        WHERE

        first_name LIKE ?
        OR username LIKE ?
        OR CAST(user_id AS TEXT) LIKE ?

        ORDER BY register_date DESC
        """, (
            f"%{search}%",
            f"%{search}%",
            f"%{search}%"
        ))

        return cursor.fetchall()


# ============================================================
# CONFIGURACIÓN
# ============================================================

def set_setting(key: str, value: str):

    with closing(get_connection()) as conn:

        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO settings(key,value)

        VALUES(?,?)

        ON CONFLICT(key)

        DO UPDATE SET value=excluded.value
        """, (
            key,
            value
        ))

        conn.commit()


def get_setting(key: str, default=None):

    with closing(get_connection()) as conn:

        cursor = conn.cursor()

        cursor.execute("""
        SELECT value
        FROM settings
        WHERE key=?
        """, (
            key,
        ))

        data = cursor.fetchone()

        if data:

            return data["value"]

        return default


# ============================================================
# RESET
# ============================================================

def reset_balance(user_id: int):

    set_balance(
        user_id,
        0
    )


def clear_products():

    with closing(get_connection()) as conn:

        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM products"
        )

        conn.commit()


# ============================================================
# HEALTH CHECK
# ============================================================

def database_status():

    try:

        with closing(get_connection()) as conn:

            conn.execute("SELECT 1")

        return True

    except Exception:

        return False
