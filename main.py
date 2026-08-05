import logging
import os
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Configuración básica de logs
logging.basicConfig(level=logging.INFO)

# --- MINI SERVIDOR WEB PARA CUMPLIR CON EL PUERTO DE RENDER ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "¡Rayo Store Bot está activo y funcionando perfectamente!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host="0.0.0.0", port=port)

Thread(target=run_web, daemon=True).start()
# -------------------------------------------------------------

# Token oficial de tu bot
TOKEN = "8717156909:AAGh4hpveIzg61gG1nGFtdg-aCi94YA05cE"
OWNER_ID = 7939709543

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# Base de datos en memoria
ADMINS_IDS = []
USER_CREDITS = {}

# Menú principal con botones
def main_menu():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("📂 VER CATÁLOGO", callback_data="ver_catalogo"),
        InlineKeyboardButton("💳 MIS CRÉDITOS", callback_data="ver_mis_creditos"),
        InlineKeyboardButton("⚙️ PANEL", callback_data="abrir_panel")
    )
    return keyboard

# Comando /start y respuesta automática a cualquier texto que escribas
@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 ¡Bienvenido a **Rayo Store**!\n\nSelecciona una de las opciones del menú:",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

@dp.message_handler()
async def echo_all_messages(message: types.Message):
    await message.answer(
        f"📩 Recibí tu mensaje: *{message.text}*\n\nSelecciona una opción del menú:",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

# Manejador de botones (Callbacks)
@dp.callback_query_handler(lambda c: True)
async def process_callback(callback_query: types.CallbackQuery):
    data = callback_query.data
    user_id = callback_query.from_user.id

    try:
        if data == "inicio":
            await bot.edit_message_text(
                "👋 ¡Bienvenido a **Rayo Store**!\n\nSelecciona una de las opciones del menú:",
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                reply_markup=main_menu(),
                parse_mode="Markdown"
            )

        elif data == "ver_catalogo":
            keyboard = InlineKeyboardMarkup(row_width=1)
            keyboard.add(
                InlineKeyboardButton("🤖 ANDROID", callback_data="cat_android"),
                InlineKeyboardButton("🍏 IOS", callback_data="cat_ios"),
                InlineKeyboardButton("⬅️ Regresar al Inicio", callback_data="inicio")
            )
            await bot.edit_message_text(
                "📂 **TENEMOS PRODUCTOS FULL PRINCIPAL** 🎮\nSelecciona tu sistema operativo:",
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )

        elif data == "cat_android":
            keyboard = InlineKeyboardMarkup(row_width=1)
            keyboard.add(
                InlineKeyboardButton("📦 DRIP CLIENT APK MOD", callback_data="comprar_prod"),
                InlineKeyboardButton("📦 DRIP CLIENT PROXY", callback_data="comprar_prod"),
                InlineKeyboardButton("📦 HG CHEATS", callback_data="comprar_prod"),
                InlineKeyboardButton("📦 HOLO VIP", callback_data="comprar_prod"),
                InlineKeyboardButton("📦 CUBAN PROXY", callback_data="comprar_prod"),
                InlineKeyboardButton("📦 CUBAN APK MOD", callback_data="comprar_prod"),
                InlineKeyboardButton("📦 HG CHEATS PROXY", callback_data="comprar_prod"),
                InlineKeyboardButton("📦 FFH4X", callback_data="comprar_prod"),
                InlineKeyboardButton("📦 BR MODS", callback_data="comprar_prod"),
                InlineKeyboardButton("📦 Strick BR", callback_data="comprar_prod"),
                InlineKeyboardButton("⬅️ Volver", callback_data="ver_catalogo")
            )
            await bot.edit_message_text(
                "🤖 **PRODUCTOS ANDROID** 📱\n\nElige tu producto:",
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )

        elif data == "cat_ios":
            keyboard = InlineKeyboardMarkup(row_width=1)
            keyboard.add(
                InlineKeyboardButton("📦 MONITE PRO", callback_data="comprar_prod"),
                InlineKeyboardButton("📦 MONITE BASICO", callback_data="comprar_prod"),
                InlineKeyboardButton("📦 CERTIFICADOS", callback_data="comprar_prod"),
                InlineKeyboardButton("📦 PROXY POTATSO", callback_data="comprar_prod"),
                InlineKeyboardButton("📦 ESIG ANUAL", callback_data="comprar_prod"),
                InlineKeyboardButton("📦 FLUCK IOS", callback_data="comprar_prod"),
                InlineKeyboardButton("⬅️ Volver", callback_data="ver_catalogo")
            )
            await bot.edit_message_text(
                "🍏 **PRODUCTOS IOS** 🍎\n\nElige tu producto:",
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )

        elif data == "comprar_prod":
            keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Volver al Catálogo", callback_data="ver_catalogo"))
            await bot.edit_message_text(
                "🛒 Para adquirir este producto, contacta con soporte o utiliza tus créditos disponibles.",
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                reply_markup=keyboard
            )

        elif data == "ver_mis_creditos":
            saldo = USER_CREDITS.get(user_id, 0)
            keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Volver al Inicio", callback_data="inicio"))
            await bot.edit_message_text(
                f"💳 Tu saldo actual es de: **{saldo} créditos**.",
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )

        elif data == "abrir_panel":
            keyboard = InlineKeyboardMarkup(row_width=1)
            if user_id == OWNER_ID or user_id in ADMINS_IDS:
                keyboard.add(
                    InlineKeyboardButton("📋 Ver Lista de Admins", callback_data="owner_list_admins"),
                    InlineKeyboardButton("💰 Gestionar Créditos", callback_data="admin_credits_menu"),
                    InlineKeyboardButton("❌ Cerrar Panel", callback_data="cerrar")
                )
                if user_id == OWNER_ID:
                    keyboard.insert(0, InlineKeyboardButton("➕ Agregar Admin", callback_data="owner_add_admin"))
                
                await bot.edit_message_text(
                    "👑 **PANEL DE ADMINISTRACIÓN**\n\nSelecciona una opción:",
                    chat_id=callback_query.message.chat.id,
                    message_id=callback_query.message.message_id,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
            else:
                await bot.answer_callback_query(callback_query.id, "❌ No tienes permisos para abrir el panel.", show_alert=True)

        elif data == "owner_add_admin":
            if user_id != OWNER_ID:
                return
            keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Volver al Panel", callback_data="abrir_panel"))
            await bot.edit_message_text(
                "➕ **AGREGAR NUEVO ADMIN**\n\nEnvíame el comando por chat privado:\n`/addadmin ID_DEL_USUARIO`",
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )

        elif data == "owner_list_admins":
            admins_text = "\n".join([str(aid) for aid in ADMINS_IDS]) if ADMINS_IDS else "No hay administradores registrados."
            keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Volver al Panel", callback_data="abrir_panel"))
            await bot.edit_message_text(
                f"📋 **LISTA DE ADMINISTRADORES:**\n\n{admins_text}",
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )

        elif data == "admin_credits_menu":
            keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Volver al Panel", callback_data="abrir_panel"))
            await bot.edit_message_text(
                "💰 **GESTIÓN DE CRÉDITOS**\n\nUsa los comandos directos en el chat:\n• `/darcreditos ID MONTO`\n• `/quitarcreditos ID MONTO`",
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )

        elif data == "cerrar":
            await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)

    except Exception as e:
        print(f"Error en callback: {e}")

# Comandos de administración
@dp.message_handler(commands=["panel"])
async def cmd_panel(message: types.Message):
    user_id = message.from_user.id
    if user_id == OWNER_ID or user_id in ADMINS_IDS:
        keyboard = InlineKeyboardMarkup(row_width=1)
        if user_id == OWNER_ID:
            keyboard.add(InlineKeyboardButton("➕ Agregar Admin", callback_data="owner_add_admin"))
        keyboard.add(
            InlineKeyboardButton("📋 Ver Lista de Admins", callback_data="owner_list_admins"),
            InlineKeyboardButton("💰 Gestionar Créditos", callback_data="admin_credits_menu"),
            InlineKeyboardButton("❌ Cerrar Panel", callback_data="cerrar")
        )
        await message.reply("👑 **PANEL DE ADMINISTRACIÓN**\n\nSelecciona una opción:", reply_markup=keyboard, parse_mode="Markdown")
    else:
        await message.reply("❌ No tienes permisos para usar este comando.")

@dp.message_handler(commands=["addadmin"])
async def cmd_addadmin(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        nuevo_id = int(message.text.split()[1])
        if nuevo_id not in ADMINS_IDS:
            ADMINS_IDS.append(nuevo_id)
            await message.reply(f"✅ ¡Usuario `{nuevo_id}` agregado como Admin exitosamente!", parse_mode="Markdown")
        else:
            await message.reply("⚠️ Ese usuario ya es administrador.")
    except (IndexError, ValueError):
        await message.reply("❌ Uso incorrecto. Ejemplo: `/addadmin 123456789`", parse_mode="Markdown")

@dp.message_handler(commands=["darcreditos"])
async def cmd_darcreditos(message: types.Message):
    if message.from_user.id != OWNER_ID and message.from_user.id not in ADMINS_IDS:
        return
    try:
        partes = message.text.split()
        target_id = int(partes[1])
        cantidad = int(partes[2])
        USER_CREDITS[target_id] = USER_CREDITS.get(target_id, 0) + cantidad
        saldo_actual = USER_CREDITS[target_id]
        await message.reply(f"✅ Agregados **{cantidad} créditos** al usuario `{target_id}`.\nSaldo total: **{saldo_actual}**.", parse_mode="Markdown")
    except (IndexError, ValueError):
        await message.reply("❌ Uso incorrecto. Ejemplo: `/darcreditos 123456789 50`", parse_mode="Markdown")

@dp.message_handler(commands=["quitarcreditos"])
async def cmd_quitarcreditos(message: types.Message):
    if message.from_user.id != OWNER_ID and message.from_user.id not in ADMINS_IDS:
        return
    try:
        partes = message.text.split()
        target_id = int(partes[1])
        cantidad = int(partes[2])
        saldo_actual = USER_CREDITS.get(target_id, 0)
        nuevos_creditos = max(0, saldo_actual - cantidad)
        USER_CREDITS[target_id] = nuevos_creditos
        await message.reply(f"⚠️ Retirados **{cantidad} créditos** al usuario `{target_id}`.\nSaldo actual: **{nuevos_creditos}**.", parse_mode="Markdown")
    except (IndexError, ValueError):
        await message.reply("❌ Uso incorrecto. Ejemplo: `/quitarcreditos 123456789 20`", parse_mode="Markdown")

@dp.message_handler(commands=["miscreditos"])
async def cmd_miscreditos(message: types.Message):
    saldo = USER_CREDITS.get(message.from_user.id, 0)
    await message.reply(f"💳 Tu saldo actual es de: **{saldo} créditos**.", parse_mode="Markdown")

if __name__ == "__main__":
    from aiogram import executor
    print("Iniciando bot con aiogram...")
    executor.start_polling(dp, skip_updates=True)
            
