import asyncio
import logging
import os
import sys
from datetime import datetime
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from dotenv import load_dotenv

from database import init_db, get_db, get_user, register_user, update_balance, log_action, get_setting, set_setting

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", 0))

if not BOT_TOKEN:
    print("Error crítico: BOT_TOKEN no configurado en variables de entorno.")
    sys.exit(1)

logging.basicConfig(level=logging.INFO)
router = Router()

class AdminStates(StatesGroup):
    waiting_for_broadcast = State()
    waiting_for_add_credit = State()
    waiting_for_remove_credit = State()
    waiting_for_user_search = State()
    waiting_for_recharge_proof = State()

def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID

def is_admin(user_id: int) -> bool:
    if is_owner(user_id):
        return True
    with get_db() as conn:
        res = conn.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,)).fetchone()
        return res is not None

@router.message()
@router.callback_query()
async def global_security_filter(event: Message | CallbackQuery, *args, **kwargs):
    user = event.from_user
    if not user:
        return
    
    register_user(user.id, user.username or "", user.full_name)
    
    db_user = get_user(user.id)
    if db_user and db_user["banned"] == 1:
        msg = "❌ Tu cuenta se encuentra baneada de este bot."
        if isinstance(event, Message):
            await event.answer(msg)
        else:
            await event.answer(msg, show_alert=True)
        return

    maintenance = get_setting("maintenance")
    if maintenance == "ON" and not is_admin(user.id):
        m_text = "🔧 **TIENDA EN MANTENIMIENTO**\n\nEstamos actualizando nuestros sistemas. Regresamos pronto."
        if isinstance(event, Message):
            await event.answer(m_text, parse_mode="Markdown")
        else:
            await event.answer("🔧 Tienda en mantenimiento temporal.", show_alert=True)
        return

@router.message(Command("start"))
async def cmd_start(message: Message):
    user = message.from_user
    db_user = get_user(user.id)
    
    keyboard_buttons = [
        [
            InlineKeyboardButton(text="🛍️ Catálogo", callback_data="menu_catalogo"),
            InlineKeyboardButton(text="👤 Mi Perfil", callback_data="menu_perfil")
        ],
        [
            InlineKeyboardButton(text="💳 Recargar Saldo", callback_data="menu_recargar"),
            InlineKeyboardButton(text="🎟️ Cupones", callback_data="menu_cupones")
        ],
        [
            InlineKeyboardButton(text="💎 Premium", callback_data="menu_premium"),
            InlineKeyboardButton(text="📦 Mis Compras", callback_data="menu_compras")
        ],
        [
            InlineKeyboardButton(text="📞 Soporte", url="https://t.me/SoporteLxzStore"),
            InlineKeyboardButton(text="📢 Canal Oficial", url="https://t.me/CanalLxzStore")
        ]
    ]
    
    if is_admin(user.id):
        keyboard_buttons.append([InlineKeyboardButton(text="🛡️ Panel Admin", callback_data="panel_admin")])
    if is_owner(user.id):
        keyboard_buttons.append([InlineKeyboardButton(text="👑 Panel Owner", callback_data="panel_owner")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    text = (
        "⚡ **LXZ STORE BEST**\n\n"
        f"👤 **Cliente:** {user.full_name}\n"
        f"💰 **Saldo:** ${db_user['balance']:.2f}\n"
        f"💎 **Premium:** {db_user['membership']}\n"
        f"📦 **Estado:** 🟢 Operativo\n\n"
        "Selecciona una opción en el menú inferior:"
    )
    
    if message.text and message.text.startswith("/start"):
        await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await message.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")

@router.callback_query(F.data == "nav_inicio")
async def nav_inicio(callback: CallbackQuery):
    await callback.answer()
    await cmd_start(callback.message)

@router.callback_query(F.data == "menu_catalogo")
async def show_catalog(callback: CallbackQuery):
    await callback.answer()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 ANDROID", callback_data="cat_ANDROID")],
        [InlineKeyboardButton(text="🍎 iOS / IPHONE", callback_data="cat_IOS")],
        [InlineKeyboardButton(text="💻 WINDOWS / PC", callback_data="cat_PC")],
        [InlineKeyboardButton(text="⬅️ Atrás", callback_data="nav_inicio")]
    ])
    await callback.message.edit_text(
        "🛍️ **CATÁLOGO DE PRODUCTOS - LXZ STORE BEST**\n\nSelecciona una categoría:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("cat_"))
async def show_category_products(callback: CallbackQuery):
    await callback.answer()
    cat = callback.data.split("_")[1]
    
    if cat == "PC":
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Atrás", callback_data="menu_catalogo")]])
        await callback.message.edit_text("💻 **WINDOWS / PC**\n\n🚧 Próximamente disponible.", reply_markup=keyboard, parse_mode="Markdown")
        return
        
    with get_db() as conn:
        products = conn.execute("SELECT * FROM products WHERE category = ? AND status != '🔴 Desactivado'", (cat,)).fetchall()
        
    if not products:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Atrás", callback_data="menu_catalogo")]])
        await callback.message.edit_text(f"📱 **{cat}**\n\nNo hay productos disponibles.", reply_markup=keyboard, parse_mode="Markdown")
        return
        
    buttons = []
    for p in products:
        buttons.append([InlineKeyboardButton(text=f"📦 {p['name']} - ${p['price']:.2f} ({p['stock']} disp.)", callback_data=f"prod_{p['id']}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Atrás", callback_data="menu_catalogo")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(f"📱 **CATEGORÍA: {cat}**", reply_markup=keyboard, parse_mode="Markdown")

@router.callback_query(F.data.startswith("prod_"))
async def show_product_detail(callback: CallbackQuery):
    await callback.answer()
    prod_id = int(callback.data.split("_")[1])
    
    with get_db() as conn:
        prod = conn.execute("SELECT * FROM products WHERE id = ?", (prod_id,)).fetchone()
        
    if not prod or prod["status"] == "🔴 Desactivado":
        await callback.answer("❌ Producto no disponible.", show_alert=True)
        return
        
    text = (
        f"📦 **DETALLES DEL PRODUCTO**\n\n"
        f"🏷️ **Nombre:** {prod['name']}\n"
        f"📝 **Descripción:** {prod['description']}\n"
        f"💰 **Precio:** ${prod['price']:.2f}\n"
        f"📊 **Stock:** {prod['stock']}\n"
    )
    
    buttons = []
    if prod["stock"] > 0 and prod["status"] == "🟢 Disponible":
        buttons.append([InlineKeyboardButton(text="🛒 Comprar Ahora", callback_data=f"buy_{prod['id']}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Atrás", callback_data=f"cat_{prod['category']}")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")

@router.callback_query(F.data.startswith("buy_"))
async def confirm_purchase(callback: CallbackQuery):
    await callback.answer()
    prod_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    
    with get_db() as conn:
        prod = conn.execute("SELECT * FROM products WHERE id = ?", (prod_id,)).fetchone()
        db_user = get_user(user_id)
        
    if not prod or prod["stock"] <= 0:
        await callback.answer("❌ Producto agotado.", show_alert=True)
        return
        
    remaining = db_user["balance"] - prod["price"]
    
    text = (
        "🛒 **CONFIRMAR COMPRA**\n\n"
        f"📦 Producto: {prod['name']}\n"
        f"💰 Precio: ${prod['price']:.2f}\n"
        f"💳 Tu saldo: ${db_user['balance']:.2f}\n"
        f"💰 Saldo restante: ${remaining:.2f}\n"
    )
    
    if remaining < 0:
        text += "\n❌ **Saldo insuficiente.**"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Recargar Saldo", callback_data="menu_recargar")],
            [InlineKeyboardButton(text="⬅️ Atrás", callback_data=f"prod_{prod_id}")]
        ])
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Confirmar", callback_data=f"execbuy_{prod_id}"),
             InlineKeyboardButton(text="❌ Cancelar", callback_data=f"prod_{prod_id}")]
        ])
        
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")

@router.callback_query(F.data.startswith("execbuy_"))
async def execute_purchase(callback: CallbackQuery):
    await callback.answer()
    prod_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    
    with get_db() as conn:
        prod = conn.execute("SELECT * FROM products WHERE id = ?", (prod_id,)).fetchone()
        db_user = get_user(user_id)
        
        if not prod or prod["stock"] <= 0 or db_user["balance"] < prod["price"]:
            await callback.answer("❌ Error en la compra (Stock o saldo).", show_alert=True)
            return
            
        success, res_val = update_balance(user_id, -prod["price"], "COMPRA")
        if not success:
            await callback.answer(f"❌ Error: {res_val}", show_alert=True)
            return
            
        new_stock = prod["stock"] - 1
        new_status = "🔴 Agotado" if new_stock == 0 else prod["status"]
        conn.execute("UPDATE products SET stock = ?, status = ? WHERE id = ?", (new_stock, new_status, prod_id))
        
        conn.execute("""
            INSERT INTO purchases (user_id, product_name, price, date, status)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, prod["name"], prod["price"], datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Completado"))

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Mis Compras", callback_data="menu_compras")],
        [InlineKeyboardButton(text="🏠 Menú Principal", callback_data="nav_inicio")]
    ])
    
    await callback.message.edit_text(
        f"🎉 **¡COMPRA EXITOSA EN LXZ STORE BEST!**\n\nHas adquirido: **{prod['name']}**",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "menu_perfil")
async def show_profile(callback: CallbackQuery):
    await callback.answer()
    db_user = get_user(callback.from_user.id)
    text = (
        f"👤 **MI PERFIL - LXZ STORE BEST**\n\n"
        f"🏷️ Nombre: {db_user['full_name']}\n"
        f"💰 Saldo: ${db_user['balance']:.2f}\n"
        f"💎 Premium: {db_user['membership']}\n"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📜 Historial de Saldo", callback_data="hist_saldo")],
        [InlineKeyboardButton(text="⬅️ Atrás", callback_data="nav_inicio")]
    ])
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")

@router.callback_query(F.data == "menu_compras")
async def show_purchases(callback: CallbackQuery):
    await callback.answer()
    with get_db() as conn:
        purchases = conn.execute("SELECT * FROM purchases WHERE user_id = ? ORDER BY id DESC LIMIT 10", (callback.from_user.id,)).fetchall()
        
    text = "📦 **MIS COMPRAS**\n\n"
    for p in purchases:
        text += f"• **{p['product_name']}** - ${p['price']:.2f} ({p['date']})\n" if purchases else "No tienes compras."
        
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Atrás", callback_data="menu_perfil")]])
    await callback.message.edit_text(text if purchases else "📦 **MIS COMPRAS**\n\nNo tienes compras registradas.", reply_markup=keyboard, parse_mode="Markdown")

@router.callback_query(F.data == "hist_saldo")
async def show_credit_history(callback: CallbackQuery):
    await callback.answer()
    with get_db() as conn:
        txs = conn.execute("SELECT * FROM credit_transactions WHERE user_id = ? ORDER BY id DESC LIMIT 10", (callback.from_user.id,)).fetchall()
        
    text = "📜 **HISTORIAL DE MOVIMIENTOS**\n\n"
    for t in txs:
        text += f"• [{t['type']}] {t['amount']:+.2f}$ (Saldo: ${t['new_balance']:.2f})\n"
        
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Atrás", callback_data="menu_perfil")]])
    await callback.message.edit_text(text if txs else "📜 Sin movimientos.", reply_markup=keyboard, parse_mode="Markdown")

@router.callback_query(F.data == "menu_recargar")
async def menu_recharge(callback: CallbackQuery):
    await callback.answer()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇵🇪 Yape / Plin", callback_data="rec_yape")],
        [InlineKeyboardButton(text="💰 Binance USDT", callback_data="rec_binance")],
        [InlineKeyboardButton(text="⬅️ Atrás", callback_data="nav_inicio")]
    ])
    await callback.message.edit_text("💳 **RECARGAR SALDO**\n\nSelecciona el método:", reply_markup=keyboard, parse_mode="Markdown")

@router.callback_query(F.data.in_({"rec_yape", "rec_binance"}))
async def recharge_instructions(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    method = "Yape / Plin" if callback.data == "rec_yape" else "Binance USDT"
    await state.update_data(recharge_method=method)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Cancelar", callback_data="menu_recargar")]])
    await callback.message.edit_text(f"💳 **MÉTODO: {method}**\n\nEnvía tu comprobante en foto por este chat.", reply_markup=keyboard, parse_mode="Markdown")
    await state.set_state(AdminStates.waiting_for_recharge_proof)

@router.message(AdminStates.waiting_for_recharge_proof, F.photo)
async def handle_recharge_proof(message: Message, state: FSMContext):
    data = await state.get_data()
    method = data.get("recharge_method", "Desconocido")
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO payments (user_id, amount, method, status, date) VALUES (?, ?, ?, 'PENDIENTE', ?)",
                       (message.from_user.id, 0.0, method, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    await state.clear()
    await message.answer("✅ Comprobante enviado para verificación.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Menú", callback_data="nav_inicio")]]))

@router.callback_query(F.data == "menu_cupones")
async def menu_coupons(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text("🎟️ **CUPONES**\n\nPróximamente activo.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Atrás", callback_data="nav_inicio")]]))

@router.callback_query(F.data == "menu_premium")
async def menu_premium(callback: CallbackQuery):
    await callback.answer()
    db_user = get_user(callback.from_user.id)
    await callback.message.edit_text(f"💎 **PREMIUM**\n\nEstado: **{db_user['membership']}**", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Atrás", callback_data="nav_inicio")]]))

@router.callback_query(F.data == "panel_admin")
async def admin_panel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("❌ Denegado.", show_alert=True)
    await callback.answer()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Usuarios", callback_data="adm_users"), InlineKeyboardButton(text="📦 Productos", callback_data="adm_products")],
        [InlineKeyboardButton(text="⬅️ Menú Principal", callback_data="nav_inicio")]
    ])
    await callback.message.edit_text("🛡️ **PANEL ADMIN - LXZ STORE BEST**", reply_markup=keyboard, parse_mode="Markdown")

@router.callback_query(F.data == "panel_owner")
async def owner_panel(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        return await callback.answer("❌ Denegado.", show_alert=True)
    await callback.answer()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Dashboard", callback_data="owner_dash"), InlineKeyboardButton(text="🔧 Mantenimiento", callback_data="owner_maint")],
        [InlineKeyboardButton(text="🛡️ Panel Admin", callback_data="panel_admin"), InlineKeyboardButton(text="⬅️ Menú", callback_data="nav_inicio")]
    ])
    await callback.message.edit_text("👑 **PANEL OWNER**", reply_markup=keyboard, parse_mode="Markdown")

@router.callback_query(F.data == "owner_dash")
async def owner_dashboard(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        return
    await callback.answer()
    with get_db() as conn:
        users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        sales = conn.execute("SELECT COUNT(*) FROM purchases").fetchone()[0]
        income = conn.execute("SELECT SUM(price) FROM purchases").fetchone()[0] or 0.0
    text = f"📊 **DASHBOARD**\n\n👥 Usuarios: {users}\n🛒 Ventas: {sales}\n💰 Ingresos: ${income:.2f}"
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Atrás", callback_data="panel_owner")]]), parse_mode="Markdown")

@router.callback_query(F.data == "owner_maint")
async def owner_maintenance_toggle(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        return
    await callback.answer()
    current = get_setting("maintenance")
    new_val = "OFF" if current == "ON" else "ON"
    set_setting("maintenance", new_val)
    await callback.message.edit_text(f"🔧 Mantenimiento: **{new_val}**", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Atrás", callback_data="panel_owner")]]), parse_mode="Markdown")

@router.callback_query(F.data == "adm_users")
async def adm_users_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    await callback.answer()
    await callback.message.edit_text("👥 Usa comandos: `/addcredit ID CANT`, `/ban ID`", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Atrás", callback_data="panel_admin")]]), parse_mode="Markdown")

@router.callback_query(F.data == "adm_products")
async def adm_products_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    await callback.answer()
    with get_db() as conn:
        prods = conn.execute("SELECT * FROM products").fetchall()
    text = "📦 **PRODUCTOS**\n\n" + "\n".join([f"ID {p['id']} - {p['name']} (${p['price']})" for p in prods])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Atrás", callback_data="panel_admin")]]), parse_mode="Markdown")

@router.message(Command("addcredit"))
async def cmd_addcredit(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ No tienes permisos de administrador para usar este comando.")
        return
        
    args = message.text.split()
    if len(args) < 3:
        return await message.answer("⚠️ **Uso correcto:** `/addcredit ID CANTIDAD`\n*Ejemplo:* `/addcredit 123456789 10`", parse_mode="Markdown")
    
    try:
        target_id = int(args[1])
        # Reemplaza automáticamente las comas por puntos por si escriben decimales con coma
        amount = float(args[2].replace(",", "."))
    except ValueError:
        return await message.answer("❌ El ID y la cantidad deben ser números válidos. (Ej: `/addcredit 12345 5.0`)", parse_mode="Markdown")
    
    # Verificar si el usuario existe en la base de datos
    db_target = get_user(target_id)
    if not db_target:
        return await message.answer(f"❌ El usuario con ID `{target_id}` no está registrado. Debe abrir el bot y enviar `/start` primero.", parse_mode="Markdown")
        
    success, res = update_balance(target_id, amount, "ADMIN_ADD", message.from_user.id)
    if success:
        await message.answer(f"✅ Se han acreditado **${amount:.2f}** correctamente.\n👤 Usuario: `{target_id}`\n💰 Nuevo saldo: **${res:.2f}**", parse_mode="Markdown")
    else:
        await message.answer(f"❌ Error al actualizar el saldo: {res}")

@router.message(Command("ban"))
async def cmd_ban(message: Message):
    if not is_admin(message.from_user.id):
        return
    args = message.text.split()
    if len(args) < 2:
        return await message.answer("Uso: `/ban ID`", parse_mode="Markdown")
    
    try:
        target_id = int(args[1])
    except ValueError:
        return await message.answer("❌ El ID debe ser un número válido.")
        
    with get_db() as conn:
        conn.execute("UPDATE users SET banned = 1 WHERE user_id = ?", (target_id,))
    await message.answer("🚫 Usuario baneado correctamente.")

@router.message(Command("unban"))
async def cmd_unban(message: Message):
    if not is_admin(message.from_user.id):
        return
    args = message.text.split()
    if len(args) < 2:
        return await message.answer("Uso: `/unban ID`", parse_mode="Markdown")
        
    try:
        target_id = int(args[1])
    except ValueError:
        return await message.answer("❌ El ID debe ser un número válido.")
        
    with get_db() as conn:
        conn.execute("UPDATE users SET banned = 0 WHERE user_id = ?", (target_id,))
    await message.answer("✅ Usuario desbaneado correctamente.")

async def main():
    init_db()
    with get_db() as conn:
        if conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
            conn.execute("INSERT INTO products (category, name, description, price, stock, status) VALUES ('ANDROID', 'Script VIP Free Fire LXZ', 'Aimbot + ESP', 5.00, 10, '🟢 Disponible')")
            
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    
    await bot.delete_webhook(drop_pending_updates=True)
    print("⚡ LXZ STORE BEST - Bot iniciado exitosamente.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot detenido.")
