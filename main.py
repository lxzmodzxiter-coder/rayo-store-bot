import logging
import os
import time
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Configuración de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- MINI SERVIDOR WEB PARA CUMPLIR CON EL PUERTO DE RENDER ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "¡Rayo Fix Bot está activo y funcionando perfectamente!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host="0.0.0.0", port=port)

Thread(target=run_web, daemon=True).start()
# -------------------------------------------------------------

# Token oficial de tu nuevo bot y tu ID de Owner
TOKEN = "8799688315:AAH3afiU9b8RdEuWtCtj3ooBTopEgaJMFFg"
OWNER_ID = 7939709543

logger.info("Esperando 5 segundos antes de inicializar el bot...")
time.sleep(5)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# Base de datos simulada en memoria
ADMINS_IDS = []
USER_CREDITS = {}

# URL de la imagen que proporcionaste para el Banner Principal
BANNER_IMAGE_URL = "https://i.ibb.co/3m20gX28/51614.jpg"  # (Imagen cargada desde tu diseño)

# Menú Principal Estilo Pro
def main_menu(user_id):
    saldo = USER_CREDITS.get(user_id, 0.0)
    is_owner = (user_id == OWNER_ID)
    is_admin = (user_id in ADMINS_IDS or is_owner)

    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("📂 VER CATÁLOGO SOCIOS", callback_data="ver_catalogo"),
        InlineKeyboardButton("💳 Recargar Saldo", callback_data="recargar_saldo"),
        InlineKeyboardButton("🎟️ Canjear Cupón", callback_data="canjear_cupon"),
        InlineKeyboardButton("👤 Mi Perfil / Historial", callback_data="mi_perfil"),
        InlineKeyboardButton("💎 Adquirir Premium ( 10% OFF 💰 )", callback_data="comprar_premium")
    )

    # Agregar botones de paneles según el rango del usuario
    if is_owner:
        keyboard.add(InlineKeyboardButton("👑 PANEL DE OWNER", callback_data="panel_owner"))
    elif is_admin:
        keyboard.add(InlineKeyboardButton("⚙️ PANEL DE ADMIN", callback_data="panel_admin"))

    keyboard.row(
        InlineKeyboardButton("👨‍💻 Soporte Directo", url="https://t.me/StoreFixersXiters"),
        InlineKeyboardButton("📢 Canal Oficial", url="https://t.me/StoreFixersXiters")
    )
    return keyboard

def texto_bienvenida(user_id, first_name):
    saldo = USER_CREDITS.get(user_id, 0.0)
    return (
        f"⚡ **RAYO FIX EXCLUSIVE** 🛍️\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 **Cliente:** {first_name}\n"
        f"🆔 **ID de Cuenta:** `{user_id}`\n"
        f"💰 **Saldo Disponible:** `${saldo:.2f} USD`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"¿Qué vamos a hacer hoy, cariño? Elige una opción:"
    )

# Comando /start
@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    logger.info(f"Comando /start recibido de {user_id}")
    
    try:
        await bot.send_photo(
            chat_id=message.chat.id,
            photo=BANNER_IMAGE_URL,
            caption=texto_bienvenida(user_id, first_name),
            reply_markup=main_menu(user_id),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error enviando foto con banner: {e}")
        await message.answer(
            texto_bienvenida(user_id, first_name),
            reply_markup=main_menu(user_id),
            parse_mode="Markdown"
        )

# Manejador de botones (Callbacks)
@dp.callback_query_handler(lambda c: True)
async def process_callback(callback_query: types.CallbackQuery):
    data = callback_query.data
    user_id = callback_query.from_user.id
    first_name = callback_query.from_user.first_name

    try:
        if data == "inicio":
            try:
                await bot.edit_message_caption(
                    chat_id=callback_query.message.chat.id,
                    message_id=callback_query.message.message_id,
                    caption=texto_bienvenida(user_id, first_name),
                    reply_markup=main_menu(user_id),
                    parse_mode="Markdown"
                )
            except Exception:
                await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
                await bot.send_photo(
                    chat_id=callback_query.message.chat.id,
                    photo=BANNER_IMAGE_URL,
                    caption=texto_bienvenida(user_id, first_name),
                    reply_markup=main_menu(user_id),
                    parse_mode="Markdown"
                )

        elif data == "ver_catalogo":
            keyboard = InlineKeyboardMarkup(row_width=1).add(
                InlineKeyboardButton("🤖 ANDROID", callback_data="cat_android"),
                InlineKeyboardButton("🍏 IOS", callback_data="cat_ios"),
                InlineKeyboardButton("⬅️ Volver al Menú", callback_data="inicio")
            )
            await callback_query.message.edit_caption(
                caption="📂 **CATÁLOGO OFICIAL - RAYO FIX** 🎮\n\nSelecciona tu sistema operativo:",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )

        elif data == "cat_android":
            keyboard = InlineKeyboardMarkup(row_width=1).add(
                InlineKeyboardButton("📦 DRIP CLIENT APK MOD", callback_data="comprar_prod"),
                InlineKeyboardButton("📦 DRIP CLIENT PROXY", callback_data="comprar_prod"),
                InlineKeyboardButton("📦 HG CHEATS", callback_data="comprar_prod"),
                InlineKeyboardButton("📦 HOLO VIP", callback_data="comprar_prod"),
                InlineKeyboardButton("📦 CUBAN PROXY", callback_data="comprar_prod"),
                InlineKeyboardButton("⬅️ Volver", callback_data="ver_catalogo")
            )
            await callback_query.message.edit_caption(
                caption="🤖 **PRODUCTOS ANDROID DISPONIBLES** 📱",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )

        elif data == "cat_ios":
            keyboard = InlineKeyboardMarkup(row_width=1).add(
                InlineKeyboardButton("📦 MONITE PRO", callback_data="comprar_prod"),
                InlineKeyboardButton("📦 MONITE BASICO", callback_data="comprar_prod"),
                InlineKeyboardButton("📦 CERTIFICADOS", callback_data="comprar_prod"),
                InlineKeyboardButton("📦 PROXY POTATSO", callback_data="comprar_prod"),
                InlineKeyboardButton("⬅️ Volver", callback_data="ver_catalogo")
            )
            await callback_query.message.edit_caption(
                caption="🍏 **PRODUCTOS IOS DISPONIBLES** 🍎",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )

        elif data == "comprar_prod":
            keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Volver", callback_data="ver_catalogo"))
            await callback_query.message.edit_caption(
                caption="🛒 Para adquirir este producto, contacta con soporte o recarga saldo en tu cuenta.",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )

        elif data == "recargar_saldo":
            keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Volver", callback_data="inicio"))
            await callback_query.message.edit_caption(
                caption="💳 **RECARGAR SALDO**\n\nPara añadir fondos a tu cuenta, comunícate directamente con soporte.",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )

        elif data == "canjear_cupon":
            keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Volver", callback_data="inicio"))
            await callback_query.message.edit_caption(
                caption="🎟️ **CANJEAR CUPÓN**\n\nEnvía tu código de cupón al chat de soporte para validarlo.",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )

        elif data == "mi_perfil":
            saldo = USER_CREDITS.get(user_id, 0.0)
            rango = "👑 Owner" if user_id == OWNER_ID else ("🛡️ Administrador" if user_id in ADMINS_IDS else "👤 Cliente")
            keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Volver", callback_data="inicio"))
            await callback_query.message.edit_caption(
                caption=f"👤 **MI PERFIL**\n\n- Nombre: {first_name}\n- ID: `{user_id}`\n- Rango: {rango}\n- Saldo: `${saldo:.2f} USD`",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )

        elif data == "comprar_premium":
            keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Volver", callback_data="inicio"))
            await callback_query.message.edit_caption(
                caption="💎 **MEMBRESÍA PREMIUM (10% OFF)**\n\nObtén acceso total a todos los scripts con descuento especial.",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )

        # --- PANEL DE OWNER ---
        elif data == "panel_owner":
            if user_id != OWNER_ID:
                await bot.answer_callback_query(callback_query.id, "❌ No tienes acceso a este panel.", show_alert=True)
                return
            
            keyboard = InlineKeyboardMarkup(row_width=1).add(
                InlineKeyboardButton("💰 Dar Créditos", callback_data="owner_dar_creditos"),
                InlineKeyboardButton("💸 Quitar Créditos", callback_data="owner_quitar_creditos"),
                InlineKeyboardButton("🛡️ Dar Rango (Admin)", callback_data="owner_dar_rango"),
                InlineKeyboardButton("🔻 Quitar Rango (Admin)", callback_data="owner_quitar_rango"),
                InlineKeyboardButton("📋 Lista de Admins", callback_data="owner_lista_admins"),
                InlineKeyboardButton("📊 Estadísticas", callback_data="owner_stats"),
                InlineKeyboardButton("⬅️ Volver al Menú", callback_data="inicio")
            )
            await callback_query.message.edit_caption(
                caption="👑 **PANEL DE OWNER - RAYO FIX**\n\nSelecciona una herramienta de gestión:",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )

        elif data == "owner_dar_creditos":
            keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Volver al Panel", callback_data="panel_owner"))
            await callback_query.message.edit_caption(
                caption="💰 **DAR CRÉDITOS (Owner)**\n\nUsa el comando en el chat:\n`/darcreditos ID_USUARIO MONTO`",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )

        elif data == "owner_quitar_creditos":
            keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Volver al Panel", callback_data="panel_owner"))
            await callback_query.message.edit_caption(
                caption="💸 **QUITAR CRÉDITOS (Owner)**\n\nUsa el comando en el chat:\n`/quitarcreditos ID_USUARIO MONTO`",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )

        elif data == "owner_dar_rango":
            keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Volver al Panel", callback_data="panel_owner"))
            await callback_query.message.edit_caption(
                caption="🛡️ **DAR RANGO ADMIN**\n\nUsa el comando en el chat:\n`/darrango ID_USUARIO`",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )

        elif data == "owner_quitar_rango":
            keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Volver al Panel", callback_data="panel_owner"))
            await callback_query.message.edit_caption(
                caption="🔻 **QUITAR RANGO ADMIN**\n\nUsa el comando en el chat:\n`/quitarrango ID_USUARIO`",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )

        elif data == "owner_lista_admins":
            admins_text = "\n".join([f"• `{aid}`" for aid in ADMINS_IDS]) if ADMINS_IDS else "No hay administradores registrados."
            keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Volver al Panel", callback_data="panel_owner"))
            await callback_query.message.edit_caption(
                caption=f"📋 **LISTA DE ADMINISTRADORES:**\n\n{admins_text}",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )

        elif data == "owner_stats":
            total_usuarios = len(USER_CREDITS)
            total_admins = len(ADMINS_IDS)
            keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Volver al Panel", callback_data="panel_owner"))
            await callback_query.message.edit_caption(
                caption=f"📊 **ESTADÍSTICAS DEL BOT**\n\n- Usuarios registrados: {total_usuarios}\n- Administradores activos: {total_admins}\n- Estado del Bot: 🟢 En Línea (Render)",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )

        # --- PANEL DE ADMIN ---
        elif data == "panel_admin":
            if user_id not in ADMINS_IDS and user_id != OWNER_ID:
                await bot.answer_callback_query(callback_query.id, "❌ No tienes permisos de administrador.", show_alert=True)
                return

            keyboard = InlineKeyboardMarkup(row_width=1).add(
                InlineKeyboardButton("💰 Dar Créditos", callback_data="admin_dar_creditos"),
                InlineKeyboardButton("💸 Quitar Créditos", callback_data="admin_quitar_creditos"),
                InlineKeyboardButton("⬅️ Volver al Menú", callback_data="inicio")
            )
            await callback_query.message.edit_caption(
                caption="⚙️ **PANEL DE ADMINISTRADOR**\n\nSelecciona una opción:",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )

        elif data == "admin_dar_creditos":
            keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Volver al Panel", callback_data="panel_admin"))
            await callback_query.message.edit_caption(
                caption="💰 **DAR CRÉDITOS (Admin)**\n\nUsa el comando en el chat:\n`/darcreditos ID_USUARIO MONTO`",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )

        elif data == "admin_quitar_creditos":
            keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Volver al Panel", callback_data="panel_admin"))
            await callback_query.message.edit_caption(
                caption="💸 **QUITAR CRÉDITOS (Admin)**\n\nUsa el comando en el chat:\n`/quitarcreditos ID_USUARIO MONTO`",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )

    except Exception as e:
        logger.error(f"Error en callback: {e}")

# --- COMANDOS DE GESTIÓN (ADMIN Y OWNER) ---
@dp.message_handler(commands=["darcreditos"])
async def cmd_darcreditos(message: types.Message):
    user_id = message.from_user.id
    if user_id != OWNER_ID and user_id not in ADMINS_IDS:
        return
    try:
        partes = message.text.split()
        target_id = int(partes[1])
        cantidad = float(partes[2])
        USER_CREDITS[target_id] = USER_CREDITS.get(target_id, 0.0) + cantidad
        await message.reply(f"✅ Agregados **${cantidad:.2f}** al usuario `{target_id}`.", parse_mode="Markdown")
    except (IndexError, ValueError):
        await message.reply("❌ Uso incorrecto. Ejemplo: `/darcreditos 123456789 10`", parse_mode="Markdown")

@dp.message_handler(commands=["quitarcreditos"])
async def cmd_quitarcreditos(message: types.Message):
    user_id = message.from_user.id
    if user_id != OWNER_ID and user_id not in ADMINS_IDS:
        return
    try:
        partes = message.text.split()
        target_id = int(partes[1])
        cantidad = float(partes[2])
        saldo_actual = USER_CREDITS.get(target_id, 0.0)
        nuevo_saldo = max(0.0, saldo_actual - cantidad)
        USER_CREDITS[target_id] = nuevo_saldo
        await message.reply(f"⚠️ Retirados **${cantidad:.2f}** al usuario `{target_id}`. Saldo actual: **${nuevo_saldo:.2f}**.", parse_mode="Markdown")
    except (IndexError, ValueError):
        await message.reply("❌ Uso incorrecto. Ejemplo: `/quitarcreditos 123456789 5`", parse_mode="Markdown")

@dp.message_handler(commands=["darrango"])
async def cmd_darrango(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        target_id = int(message.text.split()[1])
        if target_id not in ADMINS_IDS and target_id != OWNER_ID:
            ADMINS_IDS.append(target_id)
            await message.reply(f"✅ ¡Usuario `{target_id}` ascendido a Administrador exitosamente!", parse_mode="Markdown")
        else:
            await message.reply("⚠️ El usuario ya es administrador o es el owner.")
    except (IndexError, ValueError):
        await message.reply("❌ Uso incorrecto. Ejemplo: `/darrango 123456789`", parse_mode="Markdown")

@dp.message_handler(commands=["quitarrango"])
async def cmd_quitarrango(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        target_id = int(message.text.split()[1])
        if target_id in ADMINS_IDS:
            ADMINS_IDS.remove(target_id)
            await message.reply(f"🔻 El usuario `{target_id}` ha sido retirado del rango de Administrador.", parse_mode="Markdown")
        else:
            await message.reply("⚠️ Ese usuario no se encuentra en la lista de administradores.")
    except (IndexError, ValueError):
        await message.reply("❌ Uso incorrecto. Ejemplo: `/quitarrango 123456789`", parse_mode="Markdown")

if __name__ == "__main__":
    from aiogram import executor
    logger.info("Iniciando polling del bot...")
    executor.start_polling(dp, skip_updates=True)
    
