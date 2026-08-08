import os
import asyncio
import logging
import datetime

try:
    
except ImportError:
    pass

from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramBadRequest

from database import (
    get_connection, db_get_user, db_upsert_user, db_log_action, db_get_setting, db_set_setting
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID_ENV = os.getenv("OWNER_ID")
OWNER_ID = int(OWNER_ID_ENV) if OWNER_ID_ENV and OWNER_ID_ENV.isdigit() else 7939709543

if not BOT_TOKEN:
    logging.critical("BOT_TOKEN no encontrado en las variables de entorno.")
    exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

class StoreStates(StatesGroup):
    waiting_for_recharge_amount = State()
    waiting_for_recharge_voucher = State()
    waiting_for_coupon = State()
    waiting_for_broadcast = State()
    waiting_for_add_credit_id = State()
    waiting_for_add_credit_amount = State()
    waiting_for_remove_credit_id = State()
    waiting_for_remove_credit_amount = State()
    waiting_for_ban_id = State()
    waiting_for_unban_id = State()
    waiting_for_search_user = State()
    waiting_for_support_msg = State()

def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID

def is_admin(user_id: int) -> bool:
    if user_id == OWNER_ID:
        return True
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM admins WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res is not None

def back_home_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Inicio", callback_data="menu_main"),
         InlineKeyboardButton(text="⬅️ Atrás", callback_data="menu_main")]
    ])

def custom_back_kb(back_callback: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Inicio", callback_data="menu_main"),
         InlineKeyboardButton(text="⬅️ Atrás", callback_data=back_callback)]
    ])

def main_menu_kb(user_id: int):
    kb = [
        [InlineKeyboardButton(text="🛍️ Catálogo", callback_data="menu_catalog"),
         InlineKeyboardButton(text="👤 Mi Perfil", callback_data="menu_profile")],
        [InlineKeyboardButton(text="📦 Mis Compras", callback_data="menu_purchases"),
         InlineKeyboardButton(text="💳 Recargar Saldo", callback_data="menu_recharge")],
        [InlineKeyboardButton(text="🎟️ Cupones", callback_data="menu_coupons"),
         InlineKeyboardButton(text="💎 Premium", callback_data="menu_premium")],
        [InlineKeyboardButton(text="📞 Soporte", callback_data="menu_support"),
         InlineKeyboardButton(text="📢 Canal Oficial", callback_data="menu_channel")]
    ]
    if is_admin(user_id):
        kb.append([InlineKeyboardButton(text="⚙️ Panel Admin", callback_data="admin_panel")])
    if is_owner(user_id):
        kb.append([InlineKeyboardButton(text="👑 Panel Owner", callback_data="owner_panel")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    args = message.text.split()
    referrer_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
    
    db_upsert_user(user.id, user.full_name, user.username, referrer_id)
    u = db_get_user(user.id)
    
    if u and u["status"] == "BANNED":
        await message.answer("🚫 **CUENTA BLOQUEADA**\nNo tienes acceso autorizado a ⚡ LXZ STORE.", parse_mode="Markdown")
        return
        
    maintenance = db_get_setting("maintenance", "OFF")
    if maintenance == "ON" and not is_admin(user.id):
        await message.answer("🔧 **SISTEMA EN MANTENIMIENTO**\n⚡ LXZ STORE se encuentra actualizándose. Vuelve pronto.", parse_mode="Markdown")
        return
        
    text = (
        f"⚡ **LXZ STORE**\n\n"
        f"¡Hola, **{user.first_name}**! Bienvenido a nuestra tienda profesional.\n"
        f"Selecciona una opción del menú para continuar:"
    )
    await message.answer(text, parse_mode="Markdown", reply_markup=main_menu_kb(user.id))

@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext):
    await state.clear()
    u = db_get_user(message.from_user.id)
    if u and u["status"] == "BANNED":
        return
    await message.answer("⚡ **LXZ STORE**\n\nMenú Principal:", parse_mode="Markdown", reply_markup=main_menu_kb(message.from_user.id))

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ No tienes permisos.")
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Usuarios", callback_data="admin_users"),
         InlineKeyboardButton(text="📦 Productos", callback_data="admin_products")],
        [InlineKeyboardButton(text="💳 Pagos", callback_data="admin_payments"),
         InlineKeyboardButton(text="📊 Estadísticas", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 Difusión", callback_data="admin_broadcast"),
         InlineKeyboardButton(text="🎟️ Cupones", callback_data="admin_coupons")],
        [InlineKeyboardButton(text="🏠 Inicio", callback_data="menu_main")]
    ])
    await message.answer("⚙️ **PANEL DE ADMINISTRACIÓN**", parse_mode="Markdown", reply_markup=kb)

@router.message(Command("owner"))
async def cmd_owner(message: Message):
    if not is_owner(message.from_user.id):
        await message.answer("❌ No tienes permisos.")
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Dashboard", callback_data="owner_dashboard"),
         InlineKeyboardButton(text="👥 Usuarios", callback_data="owner_users")],
        [InlineKeyboardButton(text="📦 Productos", callback_data="owner_products"),
         InlineKeyboardButton(text="💳 Pagos", callback_data="owner_payments")],
        [InlineKeyboardButton(text="⚙️ Administradores", callback_data="owner_admins"),
         InlineKeyboardButton(text="🔧 Configuración", callback_data="owner_settings")],
        [InlineKeyboardButton(text="🎟️ Cupones", callback_data="owner_coupons"),
         InlineKeyboardButton(text="📢 Difusión", callback_data="owner_broadcast")],
        [InlineKeyboardButton(text="🛡️ Seguridad", callback_data="owner_security"),
         InlineKeyboardButton(text="📜 Registros", callback_data="owner_logs")],
        [InlineKeyboardButton(text="🏠 Inicio", callback_data="menu_main")]
    ])
    await message.answer("👑 **PANEL OWNER**", parse_mode="Markdown", reply_markup=kb)

@router.callback_query(F.data == "menu_main")
async def cb_menu_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    u = db_get_user(callback.from_user.id)
    if u and u["status"] == "BANNED":
        await callback.answer("Cuenta bloqueada", show_alert=True)
        return
    text = "⚡ **LXZ STORE**\n\nMenú Principal:"
    try:
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=main_menu_kb(callback.from_user.id))
    except TelegramBadRequest:
        await callback.message.answer(text, parse_mode="Markdown", reply_markup=main_menu_kb(callback.from_user.id))
    await callback.answer()

@router.callback_query(F.data == "menu_profile")
async def cb_profile(callback: CallbackQuery):
    u = db_get_user(callback.from_user.id)
    if not u:
        await callback.answer("Usuario no encontrado", show_alert=True)
        return
    text = (
        f"👤 **MI PERFIL**\n\n"
        f"📌 Nombre: `{u['name']}`\n"
        f"🔖 Username: `@{u['username'] or 'Sin username'}`\n"
        f"🆔 ID: `{u['user_id']}`\n"
        f"💰 Saldo: `${u['balance']:.2f} USD`\n"
        f"💎 Premium: `{u['premium'] or 'Inactivo'}`\n"
        f"📦 Compras: `{u['purchases_count']}`\n"
        f"💵 Total gastado: `${u['total_spent']:.2f} USD`\n"
        f"📅 Fecha de registro: `{u['registered_at'][:10]}`"
    )
    try:
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_home_kb())
    except TelegramBadRequest:
        pass
    await callback.answer()

@router.callback_query(F.data == "menu_purchases")
async def cb_purchases(callback: CallbackQuery):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM purchases WHERE user_id = ? ORDER BY id DESC LIMIT 5", (callback.from_user.id,))
    purchases = cursor.fetchall()
    conn.close()
    
    if not purchases:
        text = "📦 **MIS COMPRAS**\n\nAún no tienes compras registradas."
    else:
        text = "📦 **TUS ÚLTIMAS COMPRAS**\n\n"
        for p in purchases:
            text += f"📦 `{p['product_name']}`\n💵 Precio: `${p['total']}` | 📅 Fecha: `{p['purchased_at'][:10]}`\n📌 Estado: `{p['status']}`\n\n"
            
    try:
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_home_kb())
    except TelegramBadRequest:
        pass
    await callback.answer()

@router.callback_query(F.data == "menu_recharge")
async def cb_recharge(callback: CallbackQuery):
    yape = db_get_setting("yape_number", "999999999")
    binance = db_get_setting("binance_wallet", "T_USDT_WALLET")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇵🇪 Yape / Plin", callback_data="recharge_yape"),
         InlineKeyboardButton(text="💰 Binance USDT", callback_data="recharge_binance")],
        [InlineKeyboardButton(text="🏠 Inicio", callback_data="menu_main"),
         InlineKeyboardButton(text="⬅️ Atrás", callback_data="menu_main")]
    ])
    text = (
        f"💳 **RECARGAR SALDO**\n\n"
        f"Selecciona el método de pago:\n\n"
        f"🇵🇪 **Yape / Plin:** `{yape}`\n"
        f"💰 **Binance USDT:** `{binance}`"
    )
    try:
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
    except TelegramBadRequest:
        pass
    await callback.answer()

@router.callback_query(F.data.in_({"recharge_yape", "recharge_binance"}))
async def cb_recharge_method(callback: CallbackQuery, state: FSMContext):
    method = "Yape/Plin" if "yape" in callback.data else "Binance"
    await state.update_data(recharge_method=method)
    await state.set_state(StoreStates.waiting_for_recharge_amount)
    text = f"💳 **RECARGA - {method.upper()}**\n\nIngresa el monto exacto en USD que vas a recargar (Ej: 10):"
    try:
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=custom_back_kb("menu_recharge"))
    except TelegramBadRequest:
        pass
    await callback.answer()

@router.message(StoreStates.waiting_for_recharge_amount, F.text)
async def process_recharge_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.strip())
        if amount <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Ingresa un número válido mayor a 0.")
        return
        
    await state.update_data(recharge_amount=amount)
    await state.set_state(StoreStates.waiting_for_recharge_voucher)
    await message.answer("📸 Envía ahora la **foto del comprobante** de pago:", parse_mode="Markdown", reply_markup=custom_back_kb("menu_recharge"))

@router.message(StoreStates.waiting_for_recharge_voucher, F.photo)
async def process_recharge_voucher(message: Message, state: FSMContext):
    data = await state.get_data()
    amount = data.get("recharge_amount")
    method = data.get("recharge_method")
    photo_id = message.photo[-1].file_id
    
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.datetime.now().isoformat()
    cursor.execute("""
        INSERT INTO payments (user_id, amount, method, voucher_id, status, created_at)
        VALUES (?, ?, ?, ?, 'PENDING', ?)
    """, (message.from_user.id, amount, method, photo_id, now))
    payment_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    db_log_action(message.from_user.id, "RECHARGE_REQUEST", f"Solicitó recarga de ${amount} por {method}")
    await state.clear()
    
    await message.answer("✅ **SOLICITUD ENVIADA**\n\nTu comprobante ha sido enviado y está pendiente de aprobación por el equipo.", parse_mode="Markdown", reply_markup=back_home_kb())
    
    admin_text = (
        f"💳 **NUEVO PAGO PENDIENTE**\n\n"
        f"🆔 ID Solicitud: `{payment_id}`\n"
        f"👤 Usuario: `{message.from_user.full_name}` (`{message.from_user.id}`)\n"
        f"💵 Monto: `${amount} USD`\n"
        f"🛠️ Método: `{method}`"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Aprobar", callback_data=f"pay_approve_{payment_id}"),
         InlineKeyboardButton(text="❌ Rechazar", callback_data=f"pay_reject_{payment_id}")]
    ])
    try:
        await bot.send_photo(chat_id=OWNER_ID, photo=photo_id, caption=admin_text, parse_mode="Markdown", reply_markup=kb)
    except Exception:
        pass

@router.callback_query(F.data.startswith("pay_approve_"))
async def cb_pay_approve(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ No tienes permisos.", show_alert=True)
        return
        
    pay_id = int(callback.data.split("_")[2])
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM payments WHERE id = ?", (pay_id,))
    pay = cursor.fetchone()
    
    if not pay or pay["status"] != "PENDING":
        conn.close()
        await callback.answer("❌ El pago ya fue procesado o no existe.", show_alert=True)
        return
        
    cursor.execute("UPDATE payments SET status = 'APPROVED', admin_id = ? WHERE id = ?", (callback.from_user.id, pay_id))
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (pay["amount"], pay["user_id"]))
    conn.commit()
    conn.close()
    
    db_log_action(callback.from_user.id, "APPROVE_PAYMENT", f"Aprobó pago #{pay_id} de ${pay['amount']} al usuario {pay['user_id']}")
    
    try:
        await bot.send_message(pay["user_id"], f"✅ **PAGO APROBADO**\n\nTu recarga de **${pay['amount']} USD** ha sido acreditada correctamente.", parse_mode="Markdown")
    except Exception:
        pass
        
    try:
        await callback.message.edit_caption(caption=callback.message.caption + "\n\n✅ **APROBADO**", parse_mode="Markdown")
    except TelegramBadRequest:
        pass
    await callback.answer("Pago aprobado con éxito.")

@router.callback_query(F.data.startswith("pay_reject_"))
async def cb_pay_reject(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ No tienes permisos.", show_alert=True)
        return
        
    pay_id = int(callback.data.split("_")[2])
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM payments WHERE id = ?", (pay_id,))
    pay = cursor.fetchone()
    
    if not pay or pay["status"] != "PENDING":
        conn.close()
        await callback.answer("❌ El pago ya fue procesado o no existe.", show_alert=True)
        return
        
    cursor.execute("UPDATE payments SET status = 'REJECTED', admin_id = ? WHERE id = ?", (callback.from_user.id, pay_id))
    conn.commit()
    conn.close()
    
    db_log_action(callback.from_user.id, "REJECT_PAYMENT", f"Rechazó pago #{pay_id} del usuario {pay['user_id']}")
    
    try:
        await bot.send_message(pay["user_id"], f"❌ **PAGO RECHAZADO**\n\nTu solicitud de recarga de **${pay['amount']} USD** fue rechazada. Contacta a soporte.", parse_mode="Markdown")
    except Exception:
        pass
        
    try:
        await callback.message.edit_caption(caption=callback.message.caption + "\n\n❌ **RECHAZADO**", parse_mode="Markdown")
    except TelegramBadRequest:
        pass
    await callback.answer("Pago rechazado.")

@router.callback_query(F.data == "menu_coupons")
async def cb_coupons(callback: CallbackQuery, state: FSMContext):
    await state.set_state(StoreStates.waiting_for_coupon)
    text = "🎟️ **CUPONES DE DESCUENTO**\n\nEnvía el código de tu cupón:"
    try:
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_home_kb())
    except TelegramBadRequest:
        pass
    await callback.answer()

@router.message(StoreStates.waiting_for_coupon, F.text)
async def process_coupon(message: Message, state: FSMContext):
    code = message.text.strip().upper()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM coupons WHERE code = ? AND status = 'ACTIVE'", (code,))
    coupon = cursor.fetchone()
    
    if not coupon:
        conn.close()
        await message.answer("❌ Cupón inválido o expirado.", reply_markup=back_home_kb())
        await state.clear()
        return
        
    cursor.execute("SELECT * FROM coupon_usage WHERE user_id = ? AND code = ?", (message.from_user.id, code))
    used = cursor.fetchone()
    if used:
        conn.close()
        await message.answer("❌ Ya has utilizado este cupón anteriormente.", reply_markup=back_home_kb())
        await state.clear()
        return
        
    cursor.execute("INSERT INTO coupon_usage (user_id, code) VALUES (?, ?)", (message.from_user.id, code))
    cursor.execute("UPDATE coupons SET uses_left = uses_left - 1 WHERE code = ?", (code,))
    conn.commit()
    conn.close()
    
    await state.clear()
    await message.answer(f"✅ **CUPÓN CANJEADO**\n\nEl cupón `{code}` se aplicó correctamente.", parse_mode="Markdown", reply_markup=back_home_kb())

@router.callback_query(F.data == "menu_premium")
async def cb_premium(callback: CallbackQuery):
    u = db_get_user(callback.from_user.id)
    status = f"💎 Premium ACTIVO ({u['premium']})" if u["premium"] else "💎 Premium INACTIVO"
    text = f"{status}\n\nObtén beneficios exclusivos, descuentos en todo el catálogo y soporte prioritario."
    try:
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_home_kb())
    except TelegramBadRequest:
        pass
    await callback.answer()

@router.callback_query(F.data == "menu_support")
async def cb_support(callback: CallbackQuery):
    support_username = db_get_setting("support_username", "@RayoFixSupport")
    text = f"📞 **SOPORTE OFICIAL**\n\nPara cualquier consulta o asistencia técnica:\n\n💬 {support_username}"
    try:
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_home_kb())
    except TelegramBadRequest:
        pass
    await callback.answer()

@router.callback_query(F.data == "menu_channel")
async def cb_channel(callback: CallbackQuery):
    channel_url = db_get_setting("channel_url", "https://t.me/TuCanal")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Abrir Canal", url=channel_url)],
        [InlineKeyboardButton(text="🏠 Inicio", callback_data="menu_main")]
    ])
    text = "📢 **CANAL OFICIAL**\n\nMantente al día con nuestras novedades, ofertas y stock actualizado."
    try:
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
    except TelegramBadRequest:
        pass
    await callback.answer()

@router.callback_query(F.data == "menu_catalog")
async def cb_catalog(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 Android", callback_data="category_android"),
         InlineKeyboardButton(text="🍎 iOS / iPhone", callback_data="category_ios")],
                [InlineKeyboardButton(text="💻 Windows / PC", callback_data="category_pc"),
         InlineKeyboardButton(text="🏠 Inicio", callback_data="menu_main")]
    ])
    try:
        await callback.message.edit_text("🛍️ **CATÁLOGO DE PRODUCTOS**\n\nSelecciona una categoría:", parse_mode="Markdown", reply_markup=kb)
    except TelegramBadRequest:
        pass
    await callback.answer()

@router.callback_query(F.data.startswith("category_"))
async def cb_category(callback: CallbackQuery):
    cat_key = callback.data.split("_")[1]
    if cat_key == "pc":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Atrás", callback_data="menu_catalog"),
             InlineKeyboardButton(text="🏠 Inicio", callback_data="menu_main")]
        ])
        try:
            await callback.message.edit_text("💻 **Windows / PC**\n\n🚧 Próximamente disponible.", parse_mode="Markdown", reply_markup=kb)
        except TelegramBadRequest:
            pass
        await callback.answer()
        return
        
    cat_name = "Android" if cat_key == "android" else "iOS"
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, price, stock FROM products WHERE category = ? AND status = 'ACTIVE'", (cat_name,))
    products = cursor.fetchall()
    conn.close()
    
    kb = []
    for p in products:
        stock_label = "🟢" if p["stock"] else "🔴"
        kb.append([InlineKeyboardButton(text=f"{stock_label} {p['name']} - ${p['price']}", callback_data=f"product_{p['id']}")])
    kb.append([InlineKeyboardButton(text="⬅️ Atrás", callback_data="menu_catalog"),
               InlineKeyboardButton(text="🏠 Inicio", callback_data="menu_main")])
               
    try:
        await callback.message.edit_text(f"📂 Categoría: **{cat_name}**\n\nElige un producto:", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    except TelegramBadRequest:
        pass
    await callback.answer()

@router.callback_query(F.data.startswith("product_"))
async def cb_product_detail(callback: CallbackQuery):
    prod_id = int(callback.data.split("_")[1])
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE id = ?", (prod_id,))
    p = cursor.fetchone()
    conn.close()
    
    if not p:
        await callback.answer("Producto no encontrado", show_alert=True)
        return
        
    stock_status = "🟢 Disponible" if p["stock"] else "🔴 Agotado"
    text = (
        f"📦 **{p['name']}**\n\n"
        f"📝 {p['description']}\n\n"
        f"💵 Precio: **${p['price']} USD**\n"
        f"📊 Stock: {stock_status}"
    )
    kb = [
        [InlineKeyboardButton(text="🛒 Comprar", callback_data=f"buy_{p['id']}")],
        [InlineKeyboardButton(text="⬅️ Atrás", callback_data=f"category_{p['category'].lower()}"),
         InlineKeyboardButton(text="🏠 Inicio", callback_data="menu_main")]
    ]
    try:
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    except TelegramBadRequest:
        pass
    await callback.answer()

@router.callback_query(F.data.startswith("buy_"))
async def cb_buy(callback: CallbackQuery):
    prod_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE id = ?", (prod_id,))
    p = cursor.fetchone()
    u = db_get_user(user_id)
    
    if not p or not p["stock"]:
        conn.close()
        await callback.answer("❌ Producto sin stock disponible.", show_alert=True)
        return
        
    price = p["price"]
    if u["premium"]:
        price = p["premium_price"] if "premium_price" in p.keys() and p["premium_price"] else price
        
    if u["balance"] < price:
        conn.close()
        await callback.answer("❌ Saldo insuficiente. Recarga tu cuenta.", show_alert=True)
        return
        
    stock_items = p["stock"].split("\n")
    delivered_item = stock_items.pop(0).strip()
    new_stock = "\n".join(stock_items) if stock_items else ""
    
    new_balance = u["balance"] - price
    new_spent = u["total_spent"] + price
    new_purchases = u["purchases_count"] + 1
    
    cursor.execute("UPDATE users SET balance = ?, total_spent = ?, purchases_count = ? WHERE user_id = ?", (new_balance, new_spent, new_purchases, user_id))
    cursor.execute("UPDATE products SET stock = ? WHERE id = ?", (new_stock, prod_id))
    cursor.execute("""
        INSERT INTO purchases (user_id, product_id, product_name, price, discount, total, coupon, purchased_at, status)
        VALUES (?, ?, ?, ?, 0.0, ?, 'NINGUNO', ?, 'COMPLETED')
    """, (user_id, prod_id, p["name"], price, price, datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    db_log_action(user_id, "PURCHASE", f"Compró {p['name']} por ${price}")
    
    text = (
        f"✅ **COMPRA REALIZADA**\n\n"
        f"📦 Producto: `{p['name']}`\n"
        f"🔑 **Entrega:**\n`{delivered_item}`\n\n"
        f"💵 Pagado: `${price:.2f} USD`\n"
        f"💰 Saldo restante: `${new_balance:.2f} USD`\n"
        f"📅 Fecha: `{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}`\n\n"
        f"Gracias por comprar en ⚡ LXZ STORE."
    )
    try:
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=back_home_kb())
    except TelegramBadRequest:
        pass
    await callback.answer("¡Compra exitosa!")

@router.callback_query(F.data == "admin_panel")
async def cb_admin_panel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ No tienes permisos.", show_alert=True)
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Usuarios", callback_data="admin_users"),
         InlineKeyboardButton(text="📦 Productos", callback_data="admin_products")],
        [InlineKeyboardButton(text="💳 Pagos", callback_data="admin_payments"),
         InlineKeyboardButton(text="📊 Estadísticas", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 Difusión", callback_data="admin_broadcast"),
         InlineKeyboardButton(text="🎟️ Cupones", callback_data="admin_coupons")],
        [InlineKeyboardButton(text="🏠 Inicio", callback_data="menu_main")]
    ])
    try:
        await callback.message.edit_text("⚙️ **PANEL DE ADMINISTRACIÓN**", parse_mode="Markdown", reply_markup=kb)
    except TelegramBadRequest:
        pass
    await callback.answer()

@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ No tienes permisos.", show_alert=True)
        return
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE premium IS NOT NULL")
    premium_users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE status = 'BANNED'")
    banned_users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM products")
    total_products = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM purchases")
    total_sales = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(total) FROM purchases")
    total_revenue = cursor.fetchone()[0] or 0.0
    cursor.execute("SELECT COUNT(*) FROM payments WHERE status = 'PENDING'")
    pending_payments = cursor.fetchone()[0]
    conn.close()
    
    text = (
        f"📊 **ESTADÍSTICAS ADMIN**\n\n"
        f"👥 Total Usuarios: `{total_users}`\n"
        f"💎 Premium: `{premium_users}`\n"
        f"🚫 Baneados: `{banned_users}`\n"
        f"📦 Productos: `{total_products}`\n"
        f"🛒 Ventas: `{total_sales}`\n"
        f"💰 Ingresos: `${total_revenue:.2f} USD`\n"
        f"💳 Pagos pendientes: `{pending_payments}`"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Atrás", callback_data="admin_panel"),
         InlineKeyboardButton(text="🏠 Inicio", callback_data="menu_main")]
    ])
    try:
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
    except TelegramBadRequest:
        pass
    await callback.answer()

@router.callback_query(F.data == "admin_users")
async def cb_admin_users(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ No tienes permisos.", show_alert=True)
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Dar Créditos", callback_data="adm_add_cred"),
         InlineKeyboardButton(text="➖ Quitar Créditos", callback_data="adm_rem_cred")],
        [InlineKeyboardButton(text="🚫 Banear", callback_data="adm_ban"),
         InlineKeyboardButton(text="✅ Desbanear", callback_data="adm_unban")],
        [InlineKeyboardButton(text="🔍 Buscar Usuario", callback_data="adm_search_user")],
        [InlineKeyboardButton(text="⬅️ Atrás", callback_data="admin_panel"),
         InlineKeyboardButton(text="🏠 Inicio", callback_data="menu_main")]
    ])
    try:
        await callback.message.edit_text("👥 **GESTIÓN DE USUARIOS**", parse_mode="Markdown", reply_markup=kb)
    except TelegramBadRequest:
        pass
    await callback.answer()

@router.callback_query(F.data == "adm_add_cred")
async def cb_adm_add_cred(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(StoreStates.waiting_for_add_credit_id)
    await callback.message.edit_text("➕ **DAR CRÉDITOS**\n\nIngresa el **ID del usuario**:", parse_mode="Markdown", reply_markup=custom_back_kb("admin_users"))
    await callback.answer()

@router.message(StoreStates.waiting_for_add_credit_id, F.text)
async def process_add_credit_id(message: Message, state: FSMContext):
    try:
        target_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ ID inválido.")
        return
    u = db_get_user(target_id)
    if not u:
        await message.answer("❌ Usuario no encontrado en la base de datos.")
        return
    await state.update_data(target_user_id=target_id)
    await state.set_state(StoreStates.waiting_for_add_credit_amount)
    await message.answer(f"👤 Usuario encontrado: `{u['name']}`\n\nIngresa la cantidad de créditos a **agregar**:", parse_mode="Markdown")

@router.message(StoreStates.waiting_for_add_credit_amount, F.text)
async def process_add_credit_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.strip())
        if amount <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("❌ Cantidad inválida.")
        return
    data = await state.get_data()
    target_id = data.get("target_user_id")
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, target_id))
    conn.commit()
    u = db_get_user(target_id)
    conn.close()
    
    await state.clear()
    await message.answer(f"✅ Se agregaron `${amount}` al usuario `{target_id}`.\nSaldo actual: `${u['balance']:.2f}`", parse_mode="Markdown", reply_markup=back_home_kb())
    try:
        await bot.send_message(target_id, f"💰 **SALDO ACTUALIZADO**\n\nSe agregaron: `+${amount}`\nSaldo actual: `${u['balance']:.2f} USD`", parse_mode="Markdown")
    except Exception:
        pass

@router.callback_query(F.data == "admin_broadcast")
async def cb_admin_broadcast(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ No tienes permisos.", show_alert=True)
        return
    await state.set_state(StoreStates.waiting_for_broadcast)
    try:
        await callback.message.edit_text("📢 **DIFUSIÓN MASIVA**\n\nEnvía el mensaje que deseas transmitir a todos los usuarios:", parse_mode="Markdown", reply_markup=custom_back_kb("admin_panel"))
    except TelegramBadRequest:
        pass
    await callback.answer()

@router.message(StoreStates.waiting_for_broadcast)
async def process_broadcast(message: Message, state: FSMContext):
    await state.clear()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE status != 'BANNED'")
    users = cursor.fetchall()
    conn.close()
    
    sent = 0
    failed = 0
    status_msg = await message.answer("📢 Iniciando difusión...")
    
    for row in users:
        try:
            await message.copy_to(chat_id=row["user_id"])
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1
            
    try:
        await status_msg.edit_text(f"📢 **DIFUSIÓN COMPLETADA**\n\n✅ Enviados: `{sent}`\n❌ Fallidos: `{failed}`", parse_mode="Markdown", reply_markup=back_home_kb())
    except TelegramBadRequest:
        pass

@router.callback_query(F.data == "owner_panel")
async def cb_owner_panel(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        await callback.answer("❌ No tienes permisos de Owner.", show_alert=True)
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Dashboard", callback_data="owner_dashboard"),
         InlineKeyboardButton(text="⚙️ Configuración", callback_data="owner_settings")],
        [InlineKeyboardButton(text="👥 Administradores", callback_data="owner_admins"),
         InlineKeyboardButton(text="🛡️ Mantenimiento ON/OFF", callback_data="owner_maint")],
        [InlineKeyboardButton(text="🏠 Inicio", callback_data="menu_main")]
    ])
    try:
        await callback.message.edit_text("👑 **PANEL OWNER**", parse_mode="Markdown", reply_markup=kb)
    except TelegramBadRequest:
        pass
    await callback.answer()

@router.callback_query(F.data == "owner_dashboard")
async def cb_owner_dashboard(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        await callback.answer("❌ No tienes permisos.", show_alert=True)
        return
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    u_count = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(total) FROM purchases")
    rev = cursor.fetchone()[0] or 0.0
    conn.close()
    
    text = f"📊 **OWNER DASHBOARD**\n\n👥 Usuarios Totales: `{u_count}`\n💵 Ingresos Totales: `${rev:.2f} USD`"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Atrás", callback_data="owner_panel"),
         InlineKeyboardButton(text="🏠 Inicio", callback_data="menu_main")]
    ])
    try:
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
    except TelegramBadRequest:
        pass
    await callback.answer()

@router.callback_query(F.data == "owner_maint")
async def cb_owner_maint(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        await callback.answer("❌ No tienes permisos.", show_alert=True)
        return
    current = db_get_setting("maintenance", "OFF")
    new_status = "ON" if current == "OFF" else "OFF"
    db_set_setting("maintenance", new_status)
    await callback.answer(f"Modo Mantenimiento: {new_status}", show_alert=True)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Atrás", callback_data="owner_panel"),
         InlineKeyboardButton(text="🏠 Inicio", callback_data="menu_main")]
    ])
    try:
        await callback.message.edit_text(f"👑 **PANEL OWNER**\n\nMantenimiento actual: **{new_status}**", parse_mode="Markdown", reply_markup=kb)
    except TelegramBadRequest:
        pass

@router.callback_query(F.data.in_({
    "admin_products", "admin_payments", "admin_coupons",
    "owner_users", "owner_products", "owner_payments",
    "owner_admins", "owner_settings", "owner_coupons",
    "owner_broadcast", "owner_security", "owner_logs",
    "adm_rem_cred", "adm_ban", "adm_unban", "adm_search_user"
}))
async def cb_stub_sections(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ No tienes permisos.", show_alert=True)
        return
    try:
        await callback.message.edit_text("🛠️ Sección funcional en desarrollo o gestionada vía comandos directos.", parse_mode="Markdown", reply_markup=back_home_kb())
    except TelegramBadRequest:
        pass
    await callback.answer()

async def main():
    if not BOT_TOKEN:
        logging.error("BOT_TOKEN no configurado.")
        return
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("⚡ LXZ STORE iniciado correctamente en modo Polling...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logging.info("🛑 Bot detenido y sesión cerrada correctamente.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("👋 Bot detenido manualmente por el usuario.")
