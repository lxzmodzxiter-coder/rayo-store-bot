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
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
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
    waiting_for_user_id = State()
    waiting_for_amount = State()

class OwnerStates(StatesGroup):
    waiting_for_product_name = State()
    waiting_for_product_desc = State()
    waiting_for_product_price = State()
    waiting_for_product_stock = State()

class UserStates(StatesGroup):
    waiting_for_recharge_proof = State()
    waiting_for_coupon = State()

# ==========================================
# FUNCIONES DE VERIFICACIÓN
# ==========================================
def is_admin_or_owner(user_id: int) -> bool:
    if user_id == OWNER_ID:
        return True
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM admins WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res is not None

def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID

# ==========================================
# TECLADOS
# ==========================================
def nav_buttons(extra_back: str = "main_menu"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🏠 Inicio", callback_data="main_menu"),
            InlineKeyboardButton(text="⬅️ Atrás", callback_data=extra_back),
            InlineKeyboardButton(text="❌ Cerrar", callback_data="close_menu")
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
        
    keyboard.append([InlineKeyboardButton(text="❌ Cerrar", callback_data="close_menu")])
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

@router.callback_query(F.data == "close_menu")
async def cb_close(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except TelegramAPIError:
        pass
    await callback.answer("Menú cerrado.")

# --- CATÁLOGO ---
@router.callback_query(F.data == "menu_catalog")
async def cb_catalog(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Android", callback_data="cat_android"),
         InlineKeyboardButton(text="🍎 iPhone / iOS", callback_data="cat_ios")],
        [InlineKeyboardButton(text="🖥️ Windows / PC", callback_data="cat_windows")],
        [InlineKeyboardButton(text="🏠 Inicio", callback_data="main_menu"),
         InlineKeyboardButton(text="⬅️ Atrás", callback_data="main_menu"),
         InlineKeyboardButton(text="❌ Cerrar", callback_data="close_menu")]
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
            ("ANDROID", "HG CHEATS", "Herramienta de rendimiento gráfico", 20.0, 30, "Disponible", "https://i.imgur.com/4X7b9dM.png"),
            ("ANDROID", "HG CHEATS PROXY", "Conexión proxy dedicada HG", 12.0, 40, "Disponible", "https://i.imgur.com/4X7b9dM.png"),
            ("ANDROID", "BR MODS", "Configuraciones BR optimizadas", 18.0, 25, "Disponible", "https://i.imgur.com/4X7b9dM.png"),
            ("ANDROID", "Strick BR", "Herramienta de precisión móvil", 22.0, 15, "Disponible", "https://i.imgur.com/4X7b9dM.png"),
            ("ANDROID", "CUBAN APK MOD", "Mod APK optimizador general", 14.0, 60, "Disponible", "https://i.imgur.com/4X7b9dM.png"),
            ("ANDROID", "CUBAN PROXY", "Proxy seguro Cuban", 9.0, 80, "Disponible", "https://i.imgur.com/4X7b9dM.png"),
            ("ANDROID", "FFH4X", "Herramienta de gestión de sensibilidad", 25.0, 10, "Disponible", "https://i.imgur.com/4X7b9dM.png"),
            ("IOS", "MONITE PRO", "Versión profesional Monite iOS", 30.0, 20, "Disponible", "https://i.imgur.com/4X7b9dM.png"),
            ("IOS", "MONITE BÁSICO", "Versión estándar Monite iOS", 15.0, 35, "Disponible", "https://i.imgur.com/4X7b9dM.png"),
            ("IOS", "CERTIFICADOS", "Certificados firmados iOS seguros", 20.0, 100, "Disponible", "https://i.imgur.com/4X7b9dM.png"),
            ("IOS", "PROXY POTATSO", "Configuración Potatso avanzada", 12.0, 50, "Disponible", "https://i.imgur.com/4X7b9dM.png"),
            ("IOS", "FLUCK IOS", "Herramienta de ajustes iOS", 25.0, 18, "Disponible", "https://i.imgur.com/4X7b9dM.png")
        ]
        cursor.executemany("INSERT INTO products (category, name, description, price, stock, status, image_url) VALUES (?, ?, ?, ?, ?, ?, ?)", defaults)
        conn.commit()
        cursor.execute("SELECT id, name, price, stock FROM products WHERE category = ?", (cat,))
        products = cursor.fetchall()
    conn.close()

    keyboard = [[InlineKeyboardButton(text=f"{p[1]} - ${p[2]:.2f} (Stock: {p[3]})", callback_data=f"prod_{p[0]}")] for p in products]
    keyboard.append([
        InlineKeyboardButton(text="🏠 Inicio", callback_data="main_menu"),
        InlineKeyboardButton(text="⬅️ Atrás", callback_data="menu_catalog"),
        InlineKeyboardButton(text="❌ Cerrar", callback_data="close_menu")
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
            InlineKeyboardButton(text="⬅️ Atrás", callback_data="cat_android"),
            InlineKeyboardButton(text="❌ Cerrar", callback_data="close_menu")
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
    conn.commit()
    conn.close()
    
    await callback.answer("✅ ¡Compra exitosa!", show_alert=True)
    await callback.message.answer(f"🧾 **COMPRA EXITOSA**\n\n📦 {prod[0]}\n💵 Pagado: ${prod[1]:.2f}\n💰 Restante: ${new_bal:.2f}", reply_markup=nav_buttons(), parse_mode="Markdown")

# --- PERFIL Y COMPRAS ---
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

# --- RECARGAS ---
@router.callback_query(F.data == "menu_recharge")
async def cb_recharge(callback: CallbackQuery):
    text = "💳 **RECARGA DE SALDO**\n\nYape / Plin: 999-999-999\nBinance USDT: `T_WALLET_EXAMPLE`\n\nEnvía tu comprobante con el botón inferior."
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Enviar Comprobante", callback_data="send_proof")],
        [InlineKeyboardButton(text="🏠 Inicio", callback_data="main_menu"), InlineKeyboardButton(text="⬅️ Atrás", callback_data="main_menu"), InlineKeyboardButton(text="❌ Cerrar", callback_data="close_menu")]
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
    pay_id = cursor.lastrowid
    conn.commit()
    conn.close()
    await state.clear()
    await message.answer("✅ Comprobante enviado. El administrador lo validará pronto.", reply_markup=nav_buttons())

# --- SOPORTE Y CANAL ---
@router.callback_query(F.data == "menu_support")
async def cb_support(callback: CallbackQuery):
    await callback.message.edit_text("📞 **SOPORTE**\n\nContacto: @RayoFixSupport", reply_markup=nav_buttons(), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "menu_channel")
async def cb_channel(callback: CallbackQuery):
    await callback.message.edit_text("📢 **CANAL OFICIAL**\n\nt.me/RayoFixStoreChannel", reply_markup=nav_buttons(), parse_mode="Markdown")
    await callback.answer()

# --- PANEL ADMIN & OWNER ---
@router.callback_query(F.data == "admin_panel")
async def cb_admin_panel(callback: CallbackQuery):
    if not is_admin_or_owner(callback.from_user.id):
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Ver Usuarios", callback_data="admin_users"), InlineKeyboardButton(text="📊 Estadísticas", callback_data="admin_stats")],
        [InlineKeyboardButton(text="🏠 Inicio", callback_data="main_menu"), InlineKeyboardButton(text="⬅️ Atrás", callback_data="main_menu"), InlineKeyboardButton(text="❌ Cerrar", callback_data="close_menu")]
    ])
    await callback.message.edit_text("⚙️ **PANEL ADMIN**", reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(callback: CallbackQuery):
    if not is_admin_or_owner(callback.from_user.id):
        return
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    u_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*), SUM(price) FROM purchases")
    p_data = cursor.fetchone()
    conn.close()
    await callback.message.edit_text(f"📊 **ESTADÍSTICAS**\n\nUsuarios: `{u_count}`\nVentas: `{p_data[0] or 0}`\nIngresos: `${p_data[1] or 0.0:.2f}`", reply_markup=nav_buttons("admin_panel"), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "owner_panel")
async def cb_owner_panel(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Inicio", callback_data="main_menu"), InlineKeyboardButton(text="⬅️ Atrás", callback_data="main_menu"), InlineKeyboardButton(text="❌ Cerrar", callback_data="close_menu")]
    ])
    await callback.message.edit_text("👑 **PANEL OWNER**", reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

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
