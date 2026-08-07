import os
import sys
import logging
import sqlite3
import asyncio
from datetime import datetime
from threading import Thread

from flask import Flask
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.exceptions import TelegramAPIError

from database import init_db, db_get_user, db_register_user, DB_NAME

# ==========================================
# CONFIGURACIÓN DE LOGS Y ENTORNO
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("RAYO_FIX_STORE")

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

if not BOT_TOKEN:
    logger.critical("¡FATAL! La variable de entorno BOT_TOKEN no está configurada.")
    sys.exit(1)

init_db()

# ==========================================
# SERVIDOR FLASK (RENDER 24/7)
# ==========================================
app = Flask(__name__)

@app.route("/")
def health_check():
    return "⚡ RAYO FIX STORE Bot is running 24/7!", 200

def run_flask():
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def start_web_server():
    t = Thread(target=run_flask, daemon=True)
    t.start()

# ==========================================
# ESTADOS FSM
# ==========================================
class AdminStates(StatesGroup):
    waiting_for_broadcast = State()
    waiting_for_user_search = State()
    waiting_for_credit_amount = State()
    waiting_for_remove_credit_amount = State()
    waiting_for_product_name = State()
    waiting_for_product_desc = State()
    waiting_for_product_price = State()
    waiting_for_product_stock = State()
    waiting_for_coupon_code = State()

class OwnerStates(StatesGroup):
    waiting_for_admin_id = State()
    waiting_for_config_value = State()

class UserStates(StatesGroup):
    waiting_for_recharge_proof = State()
    waiting_for_coupon = State()

# ==========================================
# FUNCIONES DE VERIFICACIÓN Y REGISTRO DE LOGS
# ==========================================
def log_admin_action(admin_id: int, action: str, target_user_id: int = None, details: str = ""):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO admin_logs (admin_id, action, target_user_id, details, date) VALUES (?, ?, ?, ?, ?)",
        (admin_id, action, target_user_id, details, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()

def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID

def get_admin_permissions(user_id: int):
    if user_id == OWNER_ID:
        return {
            "MANAGE_USERS": 1, "MANAGE_PRODUCTS": 1, "MANAGE_PAYMENTS": 1,
            "MANAGE_CREDITS": 1, "MANAGE_PREMIUM": 1, "MANAGE_COUPONS": 1,
            "BROADCAST": 1, "VIEW_STATS": 1
        }
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT manage_users, manage_products, manage_payments, manage_credits, manage_premium, manage_coupons, broadcast, view_stats FROM admins WHERE user_id = ?",
        (user_id,)
    )
    res = cursor.fetchone()
    conn.close()
    if not res:
        return None
    return {
        "MANAGE_USERS": res[0], "MANAGE_PRODUCTS": res[1], "MANAGE_PAYMENTS": res[2],
        "MANAGE_CREDITS": res[3], "MANAGE_PREMIUM": res[4], "MANAGE_COUPONS": res[5],
        "BROADCAST": res[6], "VIEW_STATS": res[7]
    }

def is_admin_or_owner(user_id: int) -> bool:
    if user_id == OWNER_ID:
        return True
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM admins WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res is not None

def has_permission(user_id: int, perm: str) -> bool:
    if user_id == OWNER_ID:
        return True
    perms = get_admin_permissions(user_id)
    return perms is not None and perms.get(perm, 0) == 1

def is_maintenance_active() -> bool:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = 'maintenance'")
    res = cursor.fetchone()
    conn.close()
    return res is not None and res[0] == "1"

# ==========================================
# TECLADOS DE NAVEGACIÓN ESTÁNDAR
# ==========================================
def nav_buttons(extra_back: str = "main_menu"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🏠 Inicio", callback_data="main_menu"),
            InlineKeyboardButton(text="⬅️ Atrás", callback_data=extra_back)
        ]
    ])

def get_main_menu(user_id: int):
    keyboard = [
        [InlineKeyboardButton(text="🛍️ Catálogo", callback_data="menu_catalog"),
         InlineKeyboardButton(text="👤 Mi Perfil", callback_data="menu_profile")],
        [InlineKeyboardButton(text="💳 Recargar", callback_data="menu_recharge"),
         InlineKeyboardButton(text="🎟️ Cupones", callback_data="menu_coupons")],
        [InlineKeyboardButton(text="💎 Premium", callback_data="menu_premium"),
         InlineKeyboardButton(text="📦 Mis Compras", callback_data="menu_purchases")],
        [InlineKeyboardButton(text="📞 Soporte", callback_data="menu_support"),
         InlineKeyboardButton(text="📢 Canal", callback_data="menu_channel")]
    ]
    if is_admin_or_owner(user_id):
        keyboard.append([InlineKeyboardButton(text="⚙️ Panel Admin", callback_data="admin_panel")])
    if is_owner(user_id):
        keyboard.append([InlineKeyboardButton(text="👑 Panel Owner", callback_data="owner_panel")])
        
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# ==========================================
# ROUTER DE COMANDOS Y CALLBACKS
# ==========================================
router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    args = message.text.split()
    invited_by = int(args[1]) if len(args) > 1 and args[1].isdigit() and int(args[1]) != user.id else None

    db_register_user(user.id, user.full_name, user.username, invited_by)
    db_user = db_get_user(user.id)
    
    if db_user and db_user[8] == 1:
        await message.answer("⚠️ Tu cuenta ha sido baneada de la tienda.")
        return

    if is_maintenance_active() and not is_admin_or_owner(user.id):
        await message.answer("🛠️ **SISTEMA EN MANTENIMIENTO**\n\nLa tienda se encuentra temporalmente cerrada por mantenimiento. Vuelve pronto.", parse_mode="Markdown")
        return

    banner_text = (
        "⚡ **RAYO FIX STORE**\n\n"
        f"👤 **Cliente:** {user.full_name}\n"
        f"🆔 **ID:** `{user.id}`\n"
        f"💰 **Saldo:** ${db_user[4]:.2f}\n"
        f"💎 **Membresía:** {'Activa' if db_user[5] == 1 else 'Inactiva'}\n\n"
        "Selecciona una opción en el menú inferior:"
    )
    await message.answer(banner_text, reply_markup=get_main_menu(user.id), parse_mode="Markdown")

@router.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user = callback.from_user
    db_user = db_get_user(user.id)
    
    if is_maintenance_active() and not is_admin_or_owner(user.id):
        await callback.message.edit_text("🛠️ **SISTEMA EN MANTENIMIENTO**\n\nLa tienda se encuentra temporalmente cerrada.", parse_mode="Markdown")
        await callback.answer()
        return

    banner_text = (
        "⚡ **RAYO FIX STORE**\n\n"
        f"👤 **Cliente:** {user.full_name}\n"
        f"🆔 **ID:** `{user.id}`\n"
        f"💰 **Saldo:** ${db_user[4]:.2f}\n"
        f"💎 **Membresía:** {'Activa' if db_user[5] == 1 else 'Inactiva'}\n\n"
        "Selecciona una opción en el menú inferior:"
    )
    try:
        await callback.message.edit_text(banner_text, reply_markup=get_main_menu(user.id), parse_mode="Markdown")
    except TelegramAPIError:
        await callback.message.answer(banner_text, reply_markup=get_main_menu(user.id), parse_mode="Markdown")
    await callback.answer()

# --- CATÁLOGO ---
@router.callback_query(F.data == "menu_catalog")
async def cb_catalog(callback: CallbackQuery):
    if is_maintenance_active() and not is_admin_or_owner(callback.from_user.id):
        await callback.answer("⚠️ Tienda en mantenimiento.", show_alert=True)
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Android", callback_data="cat_android"),
         InlineKeyboardButton(text="🍎 iPhone / iOS", callback_data="cat_ios")],
        [InlineKeyboardButton(text="🖥️ Windows / PC", callback_data="cat_windows")],
        [InlineKeyboardButton(text="🏠 Inicio", callback_data="main_menu"),
         InlineKeyboardButton(text="⬅️ Atrás", callback_data="main_menu")]
    ])
    await callback.message.edit_text("📂 **CATÁLOGO GENERAL DE RAYO FIX STORE**\n\nSelecciona una categoría:", reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "cat_windows")
async def cb_cat_windows(callback: CallbackQuery):
    await callback.message.edit_text("🖥️ **Windows / PC**\n\n🚧 Próximamente...", reply_markup=nav_buttons("menu_catalog"), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data.in_({"cat_android", "cat_ios"}))
async def cb_show_category_products(callback: CallbackQuery):
    cat = "ANDROID" if callback.data == "cat_android" else "IOS"
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, price, stock FROM products WHERE category = ?", (cat,))
    products = cursor.fetchall()
    
    if not products:
        defaults = [
            ("ANDROID", "DRIP CLIENT APK MOD", "Mod APK avanzado para optimización", 15.0, 99, "Disponible", "https://i.imgur.com/4X7b9dM.png"),
            ("ANDROID", "DRIP CLIENT PROXY", "Proxy optimizado para Drip Client", 10.0, 50, "Disponible", "https://i.imgur.com/4X7b9dM.png"),
            ("IOS", "MONITE PRO", "Versión profesional Monite iOS", 30.0, 20, "Disponible", "https://i.imgur.com/4X7b9dM.png"),
            ("IOS", "CERTIFICADOS", "Certificados firmados iOS seguros", 20.0, 100, "Disponible", "https://i.imgur.com/4X7b9dM.png")
        ]
        cursor.executemany("INSERT INTO products (category, name, description, price, stock, status, image_url) VALUES (?, ?, ?, ?, ?, ?, ?)", defaults)
        conn.commit()
        cursor.execute("SELECT id, name, price, stock FROM products WHERE category = ?", (cat,))
        products = cursor.fetchall()
    conn.close()

    keyboard = [[InlineKeyboardButton(text=f"{p[1]} - ${p[2]:.2f} (Stock: {p[3]})", callback_data=f"prod_{p[0]}")] for p in products]
    keyboard.append([
        InlineKeyboardButton(text="🏠 Inicio", callback_data="main_menu"),
        InlineKeyboardButton(text="⬅️ Atrás", callback_data="menu_catalog")
    ])
    await callback.message.edit_text(f"📦 **Productos en {cat}**", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data.startswith("prod_"))
async def cb_product_detail(callback: CallbackQuery):
    p_id = int(callback.data.split("_")[1])
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT name, description, price, stock, status, image_url FROM products WHERE id = ?", (p_id,))
    prod = cursor.fetchone()
    conn.close()
    
    if not prod:
        await callback.answer("Producto no encontrado.", show_alert=True)
        return
        
    text = f"🛍️ **{prod[0]}**\n\n📝 **Descripción:** {prod[1]}\n💵 **Precio:** ${prod[2]:.2f}\n📦 **Stock:** {prod[3]}\n🟢 **Estado:** {prod[4]}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Comprar Ahora", callback_data=f"buy_{p_id}")],
        [
            InlineKeyboardButton(text="🏠 Inicio", callback_data="main_menu"),
            InlineKeyboardButton(text="⬅️ Atrás", callback_data="cat_android")
        ]
    ])
    try:
        await callback.message.delete()
        await callback.message.answer_photo(photo=prod[5] or "https://i.imgur.com/4X7b9dM.png", caption=text, reply_markup=kb, parse_mode="Markdown")
    except TelegramAPIError:
        await callback.message.answer(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data.startswith("buy_"))
async def cb_buy_product(callback: CallbackQuery):
    if is_maintenance_active() and not is_admin_or_owner(callback.from_user.id):
        await callback.answer("⚠️ Tienda en mantenimiento. No se pueden procesar compras.", show_alert=True)
        return

    p_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT name, price, stock FROM products WHERE id = ?", (p_id,))
    prod = cursor.fetchone()
    cursor.execute("SELECT balance, purchases_count FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if not prod or prod[2] <= 0:
        await callback.answer("❌ Sin stock o producto no disponible.", show_alert=True)
        return
    if user[0] < prod[1]:
        await callback.answer("❌ Saldo insuficiente.", show_alert=True)
        return
        
    new_bal, new_stock, new_purchases = user[0] - prod[1], prod[2] - 1, user[1] + 1
    date_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = ?, purchases_count = ? WHERE id = ?", (new_bal, new_purchases, user_id))
    cursor.execute("UPDATE products SET stock = ? WHERE id = ?", (new_stock, p_id))
    cursor.execute("INSERT INTO purchases (user_id, product_name, price, date, status) VALUES (?, ?, ?, ?, ?)", (user_id, prod[0], prod[1], date_now, "Completado"))
    cursor.execute(
        "INSERT INTO credit_transactions (user_id, admin_id, amount, type, previous_balance, new_balance, date) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, 0, prod[1], "PURCHASE", user[0], new_bal, date_now)
    )
    conn.commit()
    conn.close()
    
    await callback.answer("✅ ¡Compra exitosa!", show_alert=True)
    await callback.message.answer(f"🧾 **COMPRA EXITOSA**\n\n📦 {prod[0]}\n💵 Pagado: ${prod[1]:.2f}\n💰 Restante: ${new_bal:.2f}", reply_markup=nav_buttons(), parse_mode="Markdown")

# --- PERFIL, COMPRAS, CUPONES USUARIO ---
@router.callback_query(F.data == "menu_profile")
async def cb_profile(callback: CallbackQuery):
    u = db_get_user(callback.from_user.id)
    text = f"👤 **MI PERFIL**\n\n📌 Nombre: {u[1]}\n🔖 @{u[2]}\n🆔 `{u[0]}`\n💰 Saldo: ${u[4]:.2f}\n💎 Premium: {'Sí' if u[5] == 1 else 'No'}\n📦 Compras: {u[6]}\n📅 Registro: {u[3]}"
    await callback.message.edit_text(text, reply_markup=nav_buttons(), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "menu_purchases")
async def cb_my_purchases(callback: CallbackQuery):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT product_name, price, date, status FROM purchases WHERE user_id = ? ORDER BY id DESC LIMIT 10", (callback.from_user.id,))
    rows = cursor.fetchall()
    conn.close()
    
    text = "📦 **MIS COMPRAS**\n\n" + ("No tienes compras recientes." if not rows else "".join([f"• {r[0]} - ${r[1]:.2f}\n  📅 {r[2]}\n\n" for r in rows]))
    await callback.message.edit_text(text, reply_markup=nav_buttons(), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "menu_coupons")
async def cb_user_coupons_menu(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.waiting_for_coupon)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Inicio", callback_data="main_menu"), InlineKeyboardButton(text="⬅️ Atrás", callback_data="main_menu")]
    ])
    await callback.message.edit_text("🎟️ **CANJEAR CUPÓN**\n\nEnvía el código del cupón por el chat para aplicarlo a tu saldo:", reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@router.message(UserStates.waiting_for_coupon)
async def process_user_coupon(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    user_id = message.from_user.id
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, type, value, uses FROM coupons WHERE code = ?", (code,))
    coupon = cursor.fetchone()
    
    if not coupon or coupon[3] <= 0:
        conn.close()
        await message.answer("❌ Cupón inválido o agotado.", reply_markup=nav_buttons())
        await state.clear()
        return

    c_id, c_type, c_value, c_uses = coupon[0], coupon[1], coupon[2], coupon[3]
    cursor.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
    user_bal = cursor.fetchone()[0]
    
    added_val = c_value if c_type == "fixed" else (user_bal * (c_value / 100.0))
    new_bal = user_bal + added_val
    
    cursor.execute("UPDATE users SET balance = ? WHERE id = ?", (new_bal, user_id))
    cursor.execute("UPDATE coupons SET uses = ? WHERE id = ?", (c_uses - 1, c_id))
    conn.commit()
    conn.close()
    
    await state.clear()
    await message.answer(f"✅ **CUPÓN CANJEADO**\n\n🎟️ Código: {code}\n💰 Saldo acreditado: ${added_val:.2f}\n💰 Nuevo saldo: ${new_bal:.2f}", reply_markup=nav_buttons(), parse_mode="Markdown")

# --- RECARGAS ---
@router.callback_query(F.data == "menu_recharge")
async def cb_recharge(callback: CallbackQuery):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key IN ('yape_plin', 'binance_wallet')")
    rows = cursor.fetchall()
    conn.close()
    yape = rows[0][0] if len(rows) > 0 else "999-999-999"
    binance = rows[1][0] if len(rows) > 1 else "T_WALLET_EXAMPLE"

    text = f"💳 **RECARGA DE SALDO**\n\nYape / Plin: {yape}\nBinance USDT: `{binance}`\n\nEnvía tu comprobante con el botón inferior."
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Enviar Comprobante", callback_data="send_proof")],
        [InlineKeyboardButton(text="🏠 Inicio", callback_data="main_menu"), InlineKeyboardButton(text="⬅️ Atrás", callback_data="main_menu")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "send_proof")
async def cb_send_proof_prompt(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.waiting_for_recharge_proof)
    await callback.message.edit_text("📤 Envía una **FOTO de tu comprobante** por el chat:", reply_markup=nav_buttons("menu_recharge"), parse_mode="Markdown")
    await callback.answer()

@router.message(UserStates.waiting_for_recharge_proof, F.photo)
async def process_recharge_proof(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    user = message.from_user
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO payments (user_id, amount, method, proof, status, date) VALUES (?, ?, ?, ?, ?, ?)", (user.id, 0.0, "Foto", photo_id, "Pendiente", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()
    await state.clear()
    await message.answer("✅ Comprobante enviado. El administrador lo validará pronto.", reply_markup=nav_buttons())

# --- SOPORTE Y CANAL ---
@router.callback_query(F.data == "menu_support")
async def cb_support(callback: CallbackQuery):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = 'support_username'")
    res = cursor.fetchone()
    conn.close()
    sup = res[0] if res else "@RayoFixSupport"
    await callback.message.edit_text(f"📞 **SOPORTE**\n\nContacto: {sup}", reply_markup=nav_buttons(), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "menu_channel")
async def cb_channel(callback: CallbackQuery):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = 'channel_link'")
    res = cursor.fetchone()
    conn.close()
    chan = res[0] if res else "t.me/RayoFixStoreChannel"
    await callback.message.edit_text(f"📢 **CANAL OFICIAL**\n\n{chan}", reply_markup=nav_buttons(), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "menu_premium")
async def cb_menu_premium_user(callback: CallbackQuery):
    await callback.message.edit_text("💎 **MEMBRESÍA PREMIUM**\n\nAdquiere beneficios exclusivos y prioridad en la tienda contactando al soporte.", reply_markup=nav_buttons(), parse_mode="Markdown")
    await callback.answer()

# ==========================================
# PANEL ADMIN
# ==========================================
@router.callback_query(F.data == "admin_panel")
async def cb_admin_panel(callback: CallbackQuery):
    if not is_admin_or_owner(callback.from_user.id):
        await callback.answer("❌ No tienes permisos.", show_alert=True)
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Usuarios", callback_data="admin_users"),
         InlineKeyboardButton(text="📦 Productos", callback_data="admin_products")],
        [InlineKeyboardButton(text="💳 Pagos", callback_data="admin_payments"),
         InlineKeyboardButton(text="💰 Créditos", callback_data="admin_credits")],
        [InlineKeyboardButton(text="📊 Estadísticas", callback_data="admin_stats"),
         InlineKeyboardButton(text="📢 Difusión", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="🎟️ Cupones", callback_data="admin_coupons")],
        [InlineKeyboardButton(text="🏠 Inicio", callback_data="main_menu"),
         InlineKeyboardButton(text="⬅️ Atrás", callback_data="main_menu")]
    ])
    await callback.message.edit_text("⚙️ **PANEL ADMINISTRADOR**", reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

# --- GESTIÓN DE USUARIOS ADMIN ---
@router.callback_query(F.data == "admin_users")
async def cb_admin_users(callback: CallbackQuery, state: FSMContext):
    if not is_admin_or_owner(callback.from_user.id) or not has_permission(callback.from_user.id, "MANAGE_USERS"):
        await callback.answer("❌ Sin permisos.", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_for_user_search)
    await callback.message.edit_text(
        "👥 **GESTIÓN DE USUARIOS**\n\nEnvía el ID del usuario o su Username (ej: `123456789` o `@usuario`) para gestionarlo:",
        reply_markup=nav_buttons("admin_panel"), parse_mode="Markdown"
    )
    await callback.answer()

@router.message(AdminStates.waiting_for_user_search)
async def process_user_search(message: Message, state: FSMContext):
    query = message.text.strip().lstrip("@")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if query.isdigit():
        cursor.execute("SELECT id, full_name, username, date, balance, is_premium, purchases_count, banned FROM users WHERE id = ?", (int(query),))
    else:
        cursor.execute("SELECT id, full_name, username, date, balance, is_premium, purchases_count, banned FROM users WHERE username = ?", (query,))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        await message.answer("❌ Usuario no encontrado.", reply_markup=nav_buttons("admin_panel"))
        await state.clear()
        return

    await state.clear()
    await show_user_profile(message, user)

async def show_user_profile(target_message: Message, user_tuple, is_edit: bool = False):
    u_id, name, uname, reg, bal, prem, compras, banned = user_tuple
    text = (
        "👤 **PERFIL DEL USUARIO**\n\n"
        f"🆔 ID: `{u_id}`\n"
        f"👤 Nombre: {name}\n"
        f"🔖 Username: @{uname or 'N/A'}\n"
        f"💰 Saldo: ${bal:.2f}\n"
        f"💎 Premium: {'Sí' if prem == 1 else 'No'}\n"
        f"📦 Compras: {compras}\n"
        f"🚫 Estado: {'Baneado' if banned == 1 else 'Activo'}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Dar Créditos", callback_data=f"adm_addcred_{u_id}"),
         InlineKeyboardButton(text="➖ Quitar Créditos", callback_data=f"adm_remcred_{u_id}")],
        [InlineKeyboardButton(text="💎 Activar Prem", callback_data=f"adm_setprem_1_{u_id}"),
         InlineKeyboardButton(text="❌ Quitar Prem", callback_data=f"adm_setprem_0_{u_id}")],
        [InlineKeyboardButton(text="🚫 Banear", callback_data=f"adm_ban_1_{u_id}"),
         InlineKeyboardButton(text="✅ Desbanear", callback_data=f"adm_ban_0_{u_id}")],
        [InlineKeyboardButton(text="📦 Compras", callback_data=f"adm_u_purchases_{u_id}"),
         InlineKeyboardButton(text="💳 Pagos", callback_data=f"adm_u_payments_{u_id}")],
        [InlineKeyboardButton(text="🏠 Inicio", callback_data="main_menu"),
         InlineKeyboardButton(text="⬅️ Atrás", callback_data="admin_users")]
    ])
    if is_edit:
        await target_message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    else:
        await target_message.answer(text, reply_markup=kb, parse_mode="Markdown")

# Acciones de Perfil de Usuario en Callback
@router.callback_query(F.data.startswith("adm_setprem_"))
async def cb_admin_set_premium(callback: CallbackQuery):
    parts = callback.data.split("_")
    val, u_id = int(parts[2]), int(parts[3])
    if not is_admin_or_owner(callback.from_user.id) or not has_permission(callback.from_user.id, "MANAGE_PREMIUM"):
        await callback.answer("❌ Sin permisos.", show_alert=True)
        return
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_premium = ? WHERE id = ?", (val, u_id))
    cursor.execute("SELECT id, full_name, username, date, balance, is_premium, purchases_count, banned FROM users WHERE id = ?", (u_id,))
    u_data = cursor.fetchone()
    conn.close()
    
    log_admin_action(callback.from_user.id, "SET_PREMIUM", u_id, f"Valor: {val}")
    await callback.answer("✅ Estado Premium actualizado.", show_alert=True)
    await show_user_profile(callback.message, u_data, is_edit=True)

@router.callback_query(F.data.startswith("adm_ban_"))
async def cb_admin_set_ban(callback: CallbackQuery):
    parts = callback.data.split("_")
    val, u_id = int(parts[2]), int(parts[3])
    if not is_admin_or_owner(callback.from_user.id) or not has_permission(callback.from_user.id, "MANAGE_USERS"):
        await callback.answer("❌ Sin permisos.", show_alert=True)
        return
    if u_id == OWNER_ID:
        await callback.answer("❌ No puedes banear al Owner.", show_alert=True)
        return
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET banned = ? WHERE id = ?", (val, u_id))
    cursor.execute("SELECT id, full_name, username, date, balance, is_premium, purchases_count, banned FROM users WHERE id = ?", (u_id,))
    u_data = cursor.fetchone()
    conn.close()
    
    log_admin_action(callback.from_user.id, "BAN_USER" if val == 1 else "UNBAN_USER", u_id)
    await callback.answer("✅ Estado de baneo actualizado.", show_alert=True)
    await show_user_profile(callback.message, u_data, is_edit=True)

@router.callback_query(F.data.startswith("adm_addcred_"))
async def cb_admin_add_credit_prompt(callback: CallbackQuery, state: FSMContext):
    if not is_admin_or_owner(callback.from_user.id) or not has_permission(callback.from_user.id, "MANAGE_CREDITS"):
        await callback.answer("❌ Sin permisos.", show_alert=True)
        return
    u_id = int(callback.data.split("_")[2])
    await state.update_data(target_user=u_id)
    await state.set_state(AdminStates.waiting_for_credit_amount)
    await callback.message.edit_text("💰 Envía la **cantidad de créditos** a añadir:", reply_markup=nav_buttons("admin_users"), parse_mode="Markdown")
    await callback.answer()

@router.message(AdminStates.waiting_for_credit_amount)
async def process_add_credit_amount(message: Message, state: FSMContext):
    try:
        amt = float(message.text.strip())
        if amt <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Cantidad inválida. Envía un número positivo:", reply_markup=nav_buttons("admin_users"))
        return
        
    data = await state.get_data()
    u_id = data.get("target_user")
    await state.clear()
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT balance, username FROM users WHERE id = ?", (u_id,))
    res = cursor.fetchone()
    if not res:
        conn.close()
        await message.answer("❌ Usuario no encontrado.", reply_markup=nav_buttons("admin_users"))
        return
    prev_bal, uname = res[0], res[1]
    new_bal = prev_bal + amt
    
    cursor.execute("UPDATE users SET balance = ? WHERE id = ?", (new_bal, u_id))
    cursor.execute(
        "INSERT INTO credit_transactions (user_id, admin_id, amount, type, previous_balance, new_balance, date) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (u_id, message.from_user.id, amt, "ADMIN_ADJUSTMENT", prev_bal, new_bal, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()
    
    log_admin_action(message.from_user.id, "ADD_CREDIT", u_id, f"Cantidad: {amt}")
    await message.answer(
        f"✅ **CRÉDITOS AÑADIDOS**\n\n👤 Usuario: @{uname or 'N/A'}\n🆔 ID: `{u_id}`\n💰 Cantidad: ${amt:.2f}\n💳 Saldo anterior: ${prev_bal:.2f}\n💰 Nuevo saldo: ${new_bal:.2f}",
        reply_markup=nav_buttons("admin_users"), parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("adm_remcred_"))
async def cb_admin_rem_credit_prompt(callback: CallbackQuery, state: FSMContext):
    if not is_admin_or_owner(callback.from_user.id) or not has_permission(callback.from_user.id, "MANAGE_CREDITS"):
        await callback.answer("❌ Sin permisos.", show_alert=True)
        return
    u_id = int(callback.data.split("_")[2])
    await state.update_data(target_user=u_id)
    await state.set_state(AdminStates.waiting_for_remove_credit_amount)
    await callback.message.edit_text("➖ Envía la **cantidad de créditos** a retirar:", reply_markup=nav_buttons("admin_users"), parse_mode="Markdown")
    await callback.answer()

@router.message(AdminStates.waiting_for_remove_credit_amount)
async def process_rem_credit_amount(message: Message, state: FSMContext):
    try:
        amt = float(message.text.strip())
        if amt <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Cantidad inválida. Envía un número positivo:", reply_markup=nav_buttons("admin_users"))
        return
        
    data = await state.get_data()
    u_id = data.get("target_user")
    await state.clear()
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT balance, username FROM users WHERE id = ?", (u_id,))
    res = cursor.fetchone()
    if not res:
        conn.close()
        await message.answer("❌ Usuario no encontrado.", reply_markup=nav_buttons("admin_users"))
        return
    prev_bal, uname = res[0], res[1]
    if prev_bal < amt:
        conn.close()
        await message.answer("❌ El usuario no tiene suficiente saldo para retirar esa cantidad.", reply_markup=nav_buttons("admin_users"))
        return
        
    new_bal = prev_bal - amt
    cursor.execute("UPDATE users SET balance = ? WHERE id = ?", (new_bal, u_id))
    cursor.execute(
        "INSERT INTO credit_transactions (user_id, admin_id, amount, type, previous_balance, new_balance, date) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (u_id, message.from_user.id, amt, "REMOVE", prev_bal, new_bal, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()
    
    log_admin_action(message.from_user.id, "REMOVE_CREDIT", u_id, f"Cantidad: {amt}")
    await message.answer(
        f"➖ **CRÉDITOS RETIRADOS**\n\n👤 Usuario: @{uname or 'N/A'}\n💸 Cantidad: ${amt:.2f}\n💳 Saldo anterior: ${prev_bal:.2f}\n💰 Nuevo saldo: ${new_bal:.2f}",
        reply_markup=nav_buttons("admin_users"), parse_mode="Markdown"
    )

# --- PRODUCTOS ADMIN ---
@router.callback_query(F.data == "admin_products")
async def cb_admin_products(callback: CallbackQuery):
    if not is_admin_or_owner(callback.from_user.id) or not has_permission(callback.from_user.id, "MANAGE_PRODUCTS"):
        await callback.answer("❌ Sin permisos.", show_alert=True)
        return
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, category, name, price, stock, status FROM products")
    prods = cursor.fetchall()
    conn.close()
    
    text = "📦 **GESTIÓN DE PRODUCTOS**\n\n" + ("No hay productos." if not prods else "".join([f"ID: `{p[0]}` | [{p[1]}] {p[2]} - ${p[3]:.2f} (Stock: {p[4]})\n" for p in prods]))
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Inicio", callback_data="main_menu"), InlineKeyboardButton(text="⬅️ Atrás", callback_data="admin_panel")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

# --- PAGOS ADMIN ---
@router.callback_query(F.data == "admin_payments")
async def cb_admin_payments(callback: CallbackQuery):
    if not is_admin_or_owner(callback.from_user.id) or not has_permission(callback.from_user.id, "MANAGE_PAYMENTS"):
        await callback.answer("❌ Sin permisos.", show_alert=True)
        return
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_id, amount, method, status, date, proof FROM payments WHERE status = 'Pendiente' ORDER BY id DESC LIMIT 5")
    payments = cursor.fetchall()
    conn.close()
    
    if not payments:
        await callback.message.edit_text("💳 **PAGOS PENDIENTES**\n\nNo hay pagos pendientes de revisión.", reply_markup=nav_buttons("admin_panel"), parse_mode="Markdown")
        await callback.answer()
        return

    p = payments[0]
    p_id, u_id, amt, meth, stat, date_p, proof = p[0], p[1], p[2], p[3], p[4], p[5], p[6]
    text = f"🧾 **PAGO PENDIENTE #{p_id}**\n\n🆔 Usuario ID: `{u_id}`\n💵 Monto: ${amt:.2f}\n💳 Método: {meth}\n📌 Estado: {stat}\n📅 Fecha: {date_p}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Aprobar", callback_data=f"pay_approve_{p_id}"),
         InlineKeyboardButton(text="❌ Rechazar", callback_data=f"pay_reject_{p_id}")],
        [InlineKeyboardButton(text="🏠 Inicio", callback_data="main_menu"), InlineKeyboardButton(text="⬅️ Atrás", callback_data="admin_panel")]
    ])
    try:
        await callback.message.delete()
        await callback.message.answer_photo(photo=proof, caption=text, reply_markup=kb, parse_mode="Markdown")
    except TelegramAPIError:
        await callback.message.answer(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data.startswith("pay_approve_"))
async def cb_approve_payment(callback: CallbackQuery):
    if not is_admin_or_owner(callback.from_user.id) or not has_permission(callback.from_user.id, "MANAGE_PAYMENTS"):
        await callback.answer("❌ Sin permisos.", show_alert=True)
        return
    p_id = int(callback.data.split("_")[2])
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, amount, status FROM payments WHERE id = ?", (p_id,))
    pay = cursor.fetchone()
    if not pay or pay[2] != "Pendiente":
        conn.close()
        await callback.answer("❌ El pago ya fue procesado o no existe.", show_alert=True)
        return
    u_id, amt = pay[0], pay[1]
    
    cursor.execute("UPDATE payments SET status = 'Aprobado' WHERE id = ?", (p_id,))
    cursor.execute("SELECT balance FROM users WHERE id = ?", (u_id,))
    prev_bal = cursor.fetchone()[0]
    new_bal = prev_bal + amt
    cursor.execute("UPDATE users SET balance = ? WHERE id = ?", (new_bal, u_id))
    conn.commit()
    conn.close()
    
    log_admin_action(callback.from_user.id, "APPROVE_PAYMENT", u_id, f"Pago #{p_id} - Monto: {amt}")
    await callback.answer("✅ Pago aprobado y saldo acreditado.", show_alert=True)
    await callback.message.answer(f"✅ **RECARGA APROBADA**\n\n💰 Monto: ${amt:.2f}\n💳 Nuevo saldo: ${new_bal:.2f}\n🧾 Pago: #{p_id}", reply_markup=nav_buttons("admin_panel"), parse_mode="Markdown")

# --- CRÉDITOS ADMIN ---
@router.callback_query(F.data == "admin_credits")
async def cb_admin_credits(callback: CallbackQuery):
    if not is_admin_or_owner(callback.from_user.id) or not has_permission(callback.from_user.id, "MANAGE_CREDITS"):
        await callback.answer("❌ Sin permisos.", show_alert=True)
        return
    await callback.message.edit_text("💰 **SISTEMA DE CRÉDITOS**\n\nUsa los comandos:\n`/addcredit ID CANTIDAD`\n`/removecredit ID CANTIDAD`\n`/balance ID`", reply_markup=nav_buttons("admin_panel"), parse_mode="Markdown")
    await callback.answer()

# --- ESTADÍSTICAS ADMIN ---
@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(callback: CallbackQuery):
    if not is_admin_or_owner(callback.from_user.id) or not has_permission(callback.from_user.id, "VIEW_STATS"):
        await callback.answer("❌ Sin permisos.", show_alert=True)
        return
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    u_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_premium = 1")
    prem_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE banned = 1")
    ban_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*), SUM(stock) FROM products")
    p_data = cursor.fetchone()
    cursor.execute("SELECT COUNT(*), SUM(price) FROM purchases")
    sales_data = cursor.fetchone()
    cursor.execute("SELECT COUNT(*) FROM payments WHERE status = 'Pendiente'")
    pend_pay = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM coupons")
    coup_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM admins")
    adm_count = cursor.fetchone()[0] + 1
    conn.close()

    text = (
        "📊 **ESTADÍSTICAS GENERALES**\n\n"
        f"👥 Usuarios totales: `{u_count}`\n"
        f"💎 Premium: `{prem_count}`\n"
        f"🚫 Baneados: `{ban_count}`\n"
        f"📦 Productos: `{p_data[0] or 0}` (Stock: {p_data[1] or 0})\n"
        f"🛒 Ventas: `{sales_data[0] or 0}`\n"
        f"💰 Ingresos: `${sales_data[1] or 0.0:.2f}`\n"
        f"💳 Pagos pendientes: `{pend_pay}`\n"
        f"🎟️ Cupones: `{coup_count}`\n"
        f"👑 Administradores: `{adm_count}`"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Inicio", callback_data="main_menu"), InlineKeyboardButton(text="⬅️ Atrás", callback_data="admin_panel")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

# --- DIFUSIÓN ADMIN ---
@router.callback_query(F.data == "admin_broadcast")
async def cb_admin_broadcast(callback: CallbackQuery, state: FSMContext):
    if not is_admin_or_owner(callback.from_user.id) or not has_permission(callback.from_user.id, "BROADCAST"):
        await callback.answer("❌ Sin permisos.", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_for_broadcast)
    await callback.message.edit_text("📢 **DIFUSIÓN**\n\nEnvía el mensaje (texto, foto o video) que deseas difundir a todos los usuarios:", reply_markup=nav_buttons("admin_panel"), parse_mode="Markdown")
    await callback.answer()

@router.message(AdminStates.waiting_for_broadcast)
async def process_broadcast_message(message: Message, state: FSMContext):
    await state.clear()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE banned = 0")
    users = cursor.fetchall()
    conn.close()

    sent, failed = 0, 0
    bot = message.bot
    for u in users:
        try:
            if message.photo:
                await bot.send_photo(chat_id=u[0], photo=message.photo[-1].file_id, caption=message.caption or "")
            elif message.video:
                await bot.send_video(chat_id=u[0], video=message.video.file_id, caption=message.caption or "")
            elif message.document:
                await bot.send_document(chat_id=u[0], document=message.document.file_id, caption=message.caption or "")
            else:
                await bot.send_message(chat_id=u[0], text=message.text or "")
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1

    log_admin_action(message.from_user.id, "BROADCAST", details=f"Enviados: {sent}, Fallidos: {failed}")
    await message.answer(f"📢 **DIFUSIÓN COMPLETADA**\n\n✅ Enviados: {sent}\n❌ Fallidos: {failed}", reply_markup=nav_buttons("admin_panel"), parse_mode="Markdown")

# --- CUPONES ADMIN ---
@router.callback_query(F.data == "admin_coupons")
async def cb_admin_coupons(callback: CallbackQuery):
    if not is_admin_or_owner(callback.from_user.id) or not has_permission(callback.from_user.id, "MANAGE_COUPONS"):
        await callback.answer("❌ Sin permisos.", show_alert=True)
        return
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT code, type, value, uses FROM coupons")
    coupons = cursor.fetchall()
    conn.close()
    
    text = "🎟️ **GESTIÓN DE CUPONES**\n\n" + ("No hay cupones activos." if not coupons else "".join([f"• `{c[0]}` | Tipo: {c[1]} | Valor: {c[2]} | Usos: {c[3]}\n" for c in coupons]))
    text += "\nUsa `/createcoupon CODIGO TIPO VALOR USOS`"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Inicio", callback_data="main_menu"), InlineKeyboardButton(text="⬅️ Atrás", callback_data="admin_panel")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

# ==========================================
# PANEL OWNER
# ==========================================
@router.callback_query(F.data == "owner_panel")
async def cb_owner_panel(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        await callback.answer("❌ Acceso exclusivo del Owner.", show_alert=True)
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Dashboard", callback_data="owner_dashboard"),
         InlineKeyboardButton(text="⚙️ Administradores", callback_data="owner_admins")],
        [InlineKeyboardButton(text="🛡️ Seguridad", callback_data="owner_security"),
         InlineKeyboardButton(text="📜 Registros", callback_data="owner_logs")],
        [InlineKeyboardButton(text="🔧 Configuración", callback_data="owner_settings")],
        [InlineKeyboardButton(text="🏠 Inicio", callback_data="main_menu"),
         InlineKeyboardButton(text="⬅️ Atrás", callback_data="main_menu")]
    ])
    await callback.message.edit_text("👑 **PANEL OWNER**", reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "owner_dashboard")
async def cb_owner_dashboard(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        return
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    u_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_premium = 1")
    prem = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE banned = 1")
    banned = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM products")
    prods = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*), SUM(price) FROM purchases")
    sales = cursor.fetchone()
    cursor.execute("SELECT COUNT(*) FROM payments WHERE status = 'Pendiente'")
    pend = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM admins")
    admins = cursor.fetchone()[0] + 1
    cursor.execute("SELECT COUNT(*) FROM coupons")
    coupons = cursor.fetchone()[0]
    conn.close()

    text = (
        "📊 **DASHBOARD OWNER**\n\n"
        f"👥 Usuarios: `{u_count}`\n"
        f"💎 Premium: `{prem}`\n"
        f"🚫 Baneados: `{banned}`\n"
        f"📦 Productos: `{prods}`\n"
        f"🛒 Ventas: `{sales[0] or 0}`\n"
        f"💰 Ingresos: `${sales[1] or 0.0:.2f}`\n"
        f"💳 Pagos pendientes: `{pend}`\n"
        f"⚙️ Administradores: `{admins}`\n"
        f"🎟️ Cupones: `{coupons}`"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Inicio", callback_data="main_menu"), InlineKeyboardButton(text="⬅️ Atrás", callback_data="owner_panel")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "owner_admins")
async def cb_owner_admins(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        return
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM admins")
    admins = cursor.fetchall()
    conn.close()
    
    text = f"👑 **ADMINISTRADORES**\n\nOwner ID: `{OWNER_ID}`\n\n" + ("No hay admins adicionales." if not admins else "".join([f"• ID: `{a[0]}`\n" for a in admins]))
    text += "\nUsa `/addadmin ID` o `/removeadmin ID`"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Inicio", callback_data="main_menu"), InlineKeyboardButton(text="⬅️ Atrás", callback_data="owner_panel")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "owner_security")
async def cb_owner_security(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        return
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE banned = 1")
    b_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM payments WHERE status = 'Pendiente'")
    p_count = cursor.fetchone()[0]
    conn.close()

    text = f"🛡️ **SEGURIDAD DEL SISTEMA**\n\n🚫 Usuarios baneados: `{b_count}`\n💳 Pagos pendientes: `{p_count}`\n🔒 Estado: Operativo"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Inicio", callback_data="main_menu"), InlineKeyboardButton(text="⬅️ Atrás", callback_data="owner_panel")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "owner_logs")
async def cb_owner_logs(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        return
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT admin_id, action, target_user_id, details, date FROM admin_logs ORDER BY id DESC LIMIT 10")
    logs = cursor.fetchall()
    conn.close()

    text = "📜 **REGISTROS / LOGS RECIENTES**\n\n" + ("No hay registros." if not logs else "".join([f"• [{l[4]}] Admin `{l[0]}` -> {l[1]} (Target: {l[2]}): {l[3]}\n" for l in logs]))
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Inicio", callback_data="main_menu"), InlineKeyboardButton(text="⬅️ Atrás", callback_data="owner_panel")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "owner_settings")
async def cb_owner_settings(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        return
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = 'maintenance'")
    res = cursor.fetchone()
    conn.close()
    maint = "ACTIVADO" if res and res[0] == "1" else "DESACTIVADO"

    text = f"🔧 **CONFIGURACIÓN**\n\nEstado Mantenimiento: `{maint}`\n\nUsa `/maintenance` para alternar."
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Inicio", callback_data="main_menu"), InlineKeyboardButton(text="⬅️ Atrás", callback_data="owner_panel")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

# ==========================================
# COMANDOS DIRECTOS (ADMIN & OWNER)
# ==========================================
@router.message(Command("addcredit"))
async def cmd_addcredit(message: Message):
    if not is_admin_or_owner(message.from_user.id) or not has_permission(message.from_user.id, "MANAGE_CREDITS"):
        await message.answer("❌ No tienes permisos para realizar esta acción.")
        return
    args = message.text.split()
    if len(args) < 3 or not args[1].isdigit():
        await message.answer("❌ Uso correcto: `/addcredit ID CANTIDAD`", parse_mode="Markdown")
        return
    u_id, amt = int(args[1]), float(args[2])
    if amt <= 0:
        await message.answer("❌ La cantidad debe ser positiva.")
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT balance, username FROM users WHERE id = ?", (u_id,))
    res = cursor.fetchone()
    if not res:
        conn.close()
        await message.answer("❌ Usuario no encontrado.")
        return
    prev_bal, uname = res[0], res[1]
    new_bal = prev_bal + amt
    cursor.execute("UPDATE users SET balance = ? WHERE id = ?", (new_bal, u_id))
    cursor.execute(
        "INSERT INTO credit_transactions (user_id, admin_id, amount, type, previous_balance, new_balance, date) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (u_id, message.from_user.id, amt, "ADMIN_ADJUSTMENT", prev_bal, new_bal, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()

    log_admin_action(message.from_user.id, "ADD_CREDIT", u_id, f"Cantidad: {amt}")
    await message.answer(f"✅ **CRÉDITOS AÑADIDOS**\n\n👤 Usuario: @{uname or 'N/A'}\n🆔 ID: `{u_id}`\n💰 Cantidad: ${amt:.2f}\n💳 Saldo anterior: ${prev_bal:.2f}\n💰 Nuevo saldo: ${new_bal:.2f}", parse_mode="Markdown")

@router.message(Command("removecredit"))
async def cmd_removecredit(message: Message):
    if not is_admin_or_owner(message.from_user.id) or not has_permission(message.from_user.id, "MANAGE_CREDITS"):
        await message.answer("❌ No tienes permisos para realizar esta acción.")
        return
    args = message.text.split()
    if len(args) < 3 or not args[1].isdigit():
        await message.answer("❌ Uso correcto: `/removecredit ID CANTIDAD`", parse_mode="Markdown")
        return
    u_id, amt = int(args[1]), float(args[2])
    if amt <= 0:
        await message.answer("❌ La cantidad debe ser positiva.")
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT balance, username FROM users WHERE id = ?", (u_id,))
    res = cursor.fetchone()
    if not res:
        conn.close()
        await message.answer("❌ Usuario no encontrado.")
        return
    prev_bal, uname = res[0], res[1]
    if prev_bal < amt:
        conn.close()
        await message.answer("❌ El usuario no tiene suficiente saldo.")
        return
    new_bal = prev_bal - amt
    cursor.execute("UPDATE users SET balance = ? WHERE id = ?", (new_bal, u_id))
    cursor.execute(
        "INSERT INTO credit_transactions (user_id, admin_id, amount, type, previous_balance, new_balance, date) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (u_id, message.from_user.id, amt, "REMOVE", prev_bal, new_bal, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()

    log_admin_action(message.from_user.id, "REMOVE_CREDIT", u_id, f"Cantidad: {amt}")
    await message.answer(f"➖ **CRÉDITOS RETIRADOS**\n\n👤 Usuario: @{uname or 'N/A'}\n💸 Cantidad: ${amt:.2f}\n💳 Saldo anterior: ${prev_bal:.2f}\n💰 Nuevo saldo: ${new_bal:.2f}", parse_mode="Markdown")

@router.message(Command("balance"))
async def cmd_balance(message: Message):
    if not is_admin_or_owner(message.from_user.id):
        await message.answer("❌ No tienes permisos.")
        return
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("❌ Uso correcto: `/balance ID`", parse_mode="Markdown")
        return
    u_id = int(args[1])
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT balance, username FROM users WHERE id = ?", (u_id,))
    res = cursor.fetchone()
    conn.close()
    if not res:
        await message.answer("❌ Usuario no encontrado.")
        return
    await message.answer(f"💰 Saldo de @{res[1] or 'N/A'} (`{u_id}`): **${res[0]:.2f}**", parse_mode="Markdown")

@router.message(Command("premium"))
async def cmd_premium(message: Message):
    if not is_admin_or_owner(message.from_user.id) or not has_permission(message.from_user.id, "MANAGE_PREMIUM"):
        await message.answer("❌ No tienes permisos.")
        return
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("❌ Uso correcto: `/premium ID`", parse_mode="Markdown")
        return
    u_id = int(args[1])
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT is_premium FROM users WHERE id = ?", (u_id,))
    res = cursor.fetchone()
    if not res:
        conn.close()
        await message.answer("❌ Usuario no encontrado.")
        return
    new_status = 0 if res[0] == 1 else 1
    cursor.execute("UPDATE users SET is_premium = ? WHERE id = ?", (new_status, u_id))
    conn.commit()
    conn.close()

    log_admin_action(message.from_user.id, "TOGGLE_PREMIUM", u_id, f"Nuevo estado: {new_status}")
    await message.answer(f"💎 Estado Premium actualizado para `{u_id}`: **{'Activo' if new_status == 1 else 'Inactivo'}**", parse_mode="Markdown")

@router.message(Command("ban"))
async def cmd_ban(message: Message):
    if not is_admin_or_owner(message.from_user.id) or not has_permission(message.from_user.id, "MANAGE_USERS"):
        await message.answer("❌ No tienes permisos.")
        return
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("❌ Uso correcto: `/ban ID`", parse_mode="Markdown")
        return
    u_id = int(args[1])
    if u_id == OWNER_ID:
        await message.answer("❌ No puedes banear al Owner.")
        return
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET banned = 1 WHERE id = ?", (u_id,))
    conn.commit()
    conn.close()

    log_admin_action(message.from_user.id, "BAN_USER", u_id)
    await message.answer(f"🚫 Usuario `{u_id}` baneado exitosamente.", parse_mode="Markdown")

@router.message(Command("unban"))
async def cmd_unban(message: Message):
    if not is_admin_or_owner(message.from_user.id) or not has_permission(message.from_user.id, "MANAGE_USERS"):
        await message.answer("❌ No tienes permisos.")
        return
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("❌ Uso correcto: `/unban ID`", parse_mode="Markdown")
        return
    u_id = int(args[1])
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET banned = 0 WHERE id = ?", (u_id,))
    conn.commit()
    conn.close()

    log_admin_action(message.from_user.id, "UNBAN_USER", u_id)
    await message.answer(f"✅ Usuario `{u_id}` desbaneado exitosamente.", parse_mode="Markdown")

@router.message(Command("addadmin"))
async def cmd_addadmin(message: Message):
    if not is_owner(message.from_user.id):
        await message.answer("❌ Comando exclusivo del Owner.")
        return
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("❌ Uso correcto: `/addadmin ID`", parse_mode="Markdown")
        return
    u_id = int(args[1])
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO admins (user_id) VALUES (?)", (u_id,))
        conn.commit()
        await message.answer(f"✅ Administrador `{u_id}` añadido correctamente.", parse_mode="Markdown")
    except sqlite3.IntegrityError:
        await message.answer("⚠️ El usuario ya es administrador.")
    finally:
        conn.close()

@router.message(Command("removeadmin"))
async def cmd_removeadmin(message: Message):
    if not is_owner(message.from_user.id):
        await message.answer("❌ Comando exclusivo del Owner.")
        return
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("❌ Uso correcto: `/removeadmin ID`", parse_mode="Markdown")
        return
    u_id = int(args[1])
    conn = sqlite3.connect(DB_Name)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM admins WHERE user_id = ?", (u_id,))
    conn.commit()
    conn.close()
    await message.answer(f"🗑️ Administrador `{u_id}` eliminado correctamente.", parse_mode="Markdown")

@router.message(Command("createcoupon"))
async def cmd_createcoupon(message: Message):
    if not is_admin_or_owner(message.from_user.id) or not has_permission(message.from_user.id, "MANAGE_COUPONS"):
        await message.answer("❌ No tienes permisos.")
        return
    args = message.text.split()
    if len(args) < 5:
        await message.answer("❌ Uso correcto: `/createcoupon CODIGO TIPO VALOR USOS`\nEjemplo: `/createcoupon RAYO10 fixed 10 100`", parse_mode="Markdown")
        return
    code, c_type, val, uses = args[1].upper(), args[2].lower(), float(args[3]), int(args[4])
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO coupons (code, type, value, uses) VALUES (?, ?, ?, ?)", (code, c_type, val, uses))
        conn.commit()
        await message.answer(f"🎟️ Cupón `{code}` creado exitosamente.", parse_mode="Markdown")
    except sqlite3.IntegrityError:
        await message.answer("❌ El código de cupón ya existe.")
    finally:
        conn.close()

@router.message(Command("maintenance"))
async def cmd_maintenance(message: Message):
    if not is_owner(message.from_user.id):
        await message.answer("❌ Comando exclusivo del Owner.")
        return
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = 'maintenance'")
    res = cursor.fetchone()
    new_val = "0" if res and res[0] == "1" else "1"
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('maintenance', ?)", (new_val,))
    conn.commit()
    conn.close()
    await message.answer(f"🔧 Modo mantenimiento **{'ACTIVADO' if new_val == '1' else 'DESACTIVADO'}**.", parse_mode="Markdown")

# ==========================================
# INICIO PRINCIPAL
# ==========================================
async def main():
    start_web_server()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("⚡ RAYO FIX STORE iniciado correctamente.")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot detenido.")
