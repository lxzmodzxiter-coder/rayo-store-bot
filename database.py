#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🗄️ LXZ STORE BEST - Módulo de Base de Datos y Persistencia (SQLite)
"""

import sqlite3
import datetime
import logging

DB_PATH = "lxz_store.db"
logger = logging.getLogger("LXZStoreDatabase")

class Database:
    @staticmethod
    def get_connection() -> sqlite3.Connection:
        """Establece y retorna una conexión activa con SQLite."""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    @classmethod
    def initialize(cls, owner_id: int) -> None:
        """Inicializa todas las tablas necesarias para la tienda y asigna el Owner principal."""
        with cls.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    balance REAL DEFAULT 0.0,
                    total_spent REAL DEFAULT 0.0,
                    is_premium INTEGER DEFAULT 0,
                    is_banned INTEGER DEFAULT 0,
                    referred_by INTEGER,
                    referral_count INTEGER DEFAULT 0,
                    registered_at TEXT
                );

                CREATE TABLE IF NOT EXISTS products (
                    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    description TEXT,
                    price REAL,
                    stock INTEGER,
                    category TEXT,
                    benefits TEXT,
                    is_active INTEGER DEFAULT 1,
                    delivery_data TEXT
                );

                CREATE TABLE IF NOT EXISTS purchases (
                    purchase_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    product_id INTEGER,
                    product_name TEXT,
                    price REAL,
                    delivery_content TEXT,
                    created_at TEXT,
                    status TEXT
                );

                CREATE TABLE IF NOT EXISTS recharges (
                    recharge_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount REAL,
                    method TEXT,
                    proof_file_id TEXT,
                    status TEXT DEFAULT 'PENDIENTE',
                    created_at TEXT
                );

                CREATE TABLE IF NOT EXISTS coupons (
                    code TEXT PRIMARY KEY,
                    discount_type TEXT,
                    discount_value REAL,
                    uses_left INTEGER,
                    expires_at TEXT
                );

                CREATE TABLE IF NOT EXISTS admins (
                    user_id INTEGER PRIMARY KEY,
                    assigned_at TEXT
                );

                CREATE TABLE IF NOT EXISTS logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    user_id INTEGER,
                    action TEXT,
                    result TEXT
                );
            """)
            conn.commit()
            
            # Asignar administrador principal (Owner) por defecto
            cursor.execute(
                "INSERT OR IGNORE INTO admins (user_id, assigned_at) VALUES (?, ?)", 
                (owner_id, datetime.datetime.now().isoformat())
            )
            conn.commit()
            
        logger.info("Base de datos estructurada e inicializada correctamente.")
        
