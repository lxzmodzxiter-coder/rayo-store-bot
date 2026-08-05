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

# Token oficial y Owner
TOKEN = "8799688315:AAH3afiU9b8RdEuWtCtj3ooBTopEgaJMFFg"
OWNER_ID = 7939709543

logger.info("Esperando 3 segundos antes de inicializar el bot...")
time.sleep(3)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# Base de datos en memoria
ADMINS_IDS = []
USER_CREDITS = {}
ALL_USERS = set()

BANNER_IMAGE_URL = "https://i.ibb.co/3m20gX28/51614.jpg"

# --- MENÚ PRINCIPAL PROFESIONAL Y ORDENADO ---
def main_menu(user_id):
    is_owner = (user_id == OWNER_ID)
    is_admin = (user_id in ADMINS_IDS or is_owner)

    keyboard = InlineKeyboardMarkup(row_width=2)
    
    keyboard.add(
        InlineKeyboardButton("📂 Catálogo SOCIOS", callback_data="ver_catalogo"),
        InlineKeyboardButton("👤 Mi Perfil", callback_data="mi_perfil")
    )
    keyboard.add(
        InlineKeyboardButton("💳 Recargar Saldo", callback_data="recargar_saldo"),
        InlineKeyboardButton("🎟️ Canjear Cupón", callback_data="canjear_cupon")
    )
    keyboard.add(
        InlineKeyboardButton("💎 Adquirir Premium ( 10% OFF 💰 )", callback_data="comprar_premium")
    )

    if is_owner:
        keyboard.add(InlineKeyboardButton("👑 PANEL DE OWNER", callback_data="panel_owner"))
    elif is_admin:
        keyboard.add(InlineKeyboardButton("⚙️ PANEL DE ADMIN", callback_data="panel_admin"))

    keyboard.add(
        InlineKeyboardButton("👨‍💻 Soporte Directo", url="https://t.me/StoreFixersXiters"),
        InlineKeyboardButton("📢 Canal Oficial", url="https://t.me/StoreFixersXiters")
    )
    
    return keyboard

def texto_principal(user_id, first_name):
    saldo = USER_CREDITS.get(user_id, 0.0)
    return (
        f"⚡ **RAYO FIX EXCLUSIVE** 🛍️\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 **Cliente:** {first_name}\n"
        f"🆔 **ID de Cuenta:** `{user_id}`\n"
        f"💰 **Saldo Disponible:** `${saldo:.2f} USD`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"¿Qué vamos a hacer hoy, {first_name}? Elige una opción:"
    )

# Comando /start
@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    ALL_USERS.add(user_id)

    try:
        await bot.send_photo(
            chat_id=message.chat.id,
            photo=BANNER_IMAGE_URL,
            caption=texto_principal(user_id, first_name),
            reply_markup=main_menu(user_id),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error enviando foto inicial: {e}")
        await message.answer(
            texto_principal(user_id, first_name),
            reply_markup=main_menu(user_id),
            parse_mode="Markdown"
        )

# --- MANEJADOR DE CLICS INSTÁNTANEOS ---
@dp.callback_query_handler(lambda c: True)
async def process_callback(callback_query: types.CallbackQuery):
    # Respuesta ultra rápida para quitar el estado de carga del botón al instante
    await callback_query.answer()

    data = callback_query.data
    user_id = callback_query.from_user.id
    first_name = callback_query.from_user.first_name
    chat_id = callback_query.message.chat.id
    message_id = callback_query.message.message_id

    try:
        if data == "inicio":
            await bot.edit_message_caption(
                chat_id=chat_id, message_id=message_id,
                caption=texto_principal(user_id, first_name),
                reply_markup=main_menu(user_id), parse_mode="Markdown"
            )

        elif data == "ver_catalogo":
            keyboard = InlineKeyboardMarkup(row_width=2).add(
                InlineKeyboardButton("🤖 ANDROID", callback_data="cat_android"),
                InlineKeyboardButton("🍏 IOS", callback_data="cat_ios")
            )
            keyboard.add(InlineKeyboardButton("⬅️ Volver al Menú", callback_data="inicio"))
            await bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption="📂 **CATÁLOGO OFICIAL - RAYO FIX** 🎮\n\nSelecciona tu sistema operativo:", reply_markup=keyboard, parse_mode="Markdown")

        elif data == "cat_android":
            keyboard = InlineKeyboardMarkup(row_width=1).add(
                InlineKeyboardButton("📦 DRIP CLIENT APK MOD", callback_data="comprar_prod"),
                InlineKeyboardButton("📦 DRIP CLIENT PROXY", callback_data="comprar_prod"),
                InlineKeyboardButton("📦 HG CHEATS", callback_data="comprar_prod"),
                InlineKeyboardButton("⬅️ Volver al Catálogo", callback_data="ver_catalogo")
            )
            await bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption="🤖 **PRODUCTOS ANDROID DISPONIBLES** 📱", reply_markup=keyboard, parse_mode="Markdown")

        elif data == "cat_ios":
            keyboard = InlineKeyboardMarkup(row_width=1).add(
                InlineKeyboardButton("📦 MONITE PRO", callback_data="comprar_prod"),
                InlineKeyboardButton("📦 CERTIFICADOS", callback_data="comprar_prod"),
                InlineKeyboardButton("⬅️ Volver al Catálogo", callback_data="ver_catalogo")
            )
            await bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption="🍏 **PRODUCTOS IOS DISPONIBLES** 🍎", reply_markup=keyboard, parse_mode="Markdown")

        elif data == "comprar_prod":
            keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Volver", callback_data="ver_catalogo"))
            await bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption="🛒 Para adquirir este producto, contacta directamente con soporte.", reply_markup=keyboard, parse_mode="Markdown")

        elif data == "recargar_saldo":
            keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Volver al Menú", callback_data="inicio"))
            await bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption="💳 **RECARGAR SALDO**\n\nComunícate con soporte para añadir fondos a tu cuenta de forma segura.", reply_markup=keyboard, parse_mode="Markdown")

        elif data == "canjear_cupon":
            keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Volver al Menú", callback_data="inicio"))
            await bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption="🎟️ **CANJEAR CUPÓN**\n\nEnvía tu código promocional al chat de soporte para validarlo.", reply_markup=keyboard, parse_mode="Markdown")

        elif data == "mi_perfil":
            saldo = USER_CREDITS.get(user_id, 0.0)
            rango = "👑 Owner" if user_id == OWNER_ID else ("🛡️ Administrador" if user_id in ADMINS_IDS else "👤 Cliente")
            keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Volver al Menú", callback_data="inicio"))
            await bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption=f"👤 **MI PERFIL - RAYO FIX**\n\n- **Nombre:** {first_name}\n- **ID:** `{user_id}`\n- **Rango:** {rango}\n- **Saldo:** `${saldo:.2f} USD`", reply_markup=keyboard, parse_mode="Markdown")

        elif data == "comprar_premium":
            keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Volver al Menú", callback_data="inicio"))
            await bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption="💎 **MEMBRESÍA PREMIUM (10% OFF)**\n\nObtén acceso ilimitado a herramientas exclusivas con descuento especial.", reply_markup=keyboard, parse_mode="Markdown")

        # --- PANEL DE OWNER ---
        elif data == "panel_owner":
            if user_id != OWNER_ID:
                return
            keyboard = InlineKeyboardMarkup(row_width=2).add(
                InlineKeyboardButton("💰 Dar Créditos", callback_data="owner_dar_creditos"),
                InlineKeyboardButton("💸 Quitar Créditos", callback_data="owner_quitar_creditos"),
                InlineKeyboardButton("🛡️ Dar Rango", callback_data="owner_dar_rango"),
                InlineKeyboardButton("🔻 Quitar Rango", callback_data="owner_quitarrango")
            )
            keyboard.add(InlineKeyboardButton("📢 Enviar Promoción Masiva", callback_data="owner_promo_info"))
            keyboard.add(InlineKeyboardButton("⬅️ Volver al Menú Principal", callback_data="inicio"))
            await bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption="👑 **PANEL DE OWNER - RAYO FIX**\n\nSelecciona una herramienta de gestión:", reply_markup=keyboard, parse_mode="Markdown")

        elif data == "owner_dar_creditos":
            keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Volver al Panel", callback_data="panel_owner"))
            await bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption="💰 **DAR CRÉDITOS**\n\nUsa en el chat:\n`/darcreditos ID_USUARIO MONTO`", reply_markup=keyboard, parse_mode="Markdown")

        elif data == "owner_quitar_creditos":
            keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Volver al Panel", callback_data="panel_owner"))
            await bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption="💸 **QUITAR CRÉDITOS**\n\nUsa en el chat:\n`/quitarcreditos ID_USUARIO MONTO`", reply_markup=keyboard, parse_mode="Markdown")

        elif data == "owner_dar_rango":
            keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Volver al Panel", callback_data="panel_owner"))
            await bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption="🛡️ **DAR RANGO ADMIN**\n\nUsa en el chat:\n`/darrango ID_USUARIO`", reply_markup=keyboard, parse_mode="Markdown")

        elif data == "owner_quitarrango":
            keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Volver al Panel", callback_data="panel_owner"))
            await bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption="🔻 **QUITAR RANGO ADMIN**\n\nUsa en el chat:\n`/quitarrango ID_USUARIO`", reply_markup=keyboard, parse_mode="Markdown")

        elif data == "owner_promo_info":
            keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Volver al Panel", callback_data="panel_owner"))
            await bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption="📢 **PROMOCIÓN MASIVA**\n\nPara enviar ofertas a todos, usa en el chat:\n`/promo Tu mensaje aquí`", reply_markup=keyboard, parse_mode="Markdown")

        # --- PANEL DE ADMIN ---
        elif data == "panel_admin":
            if user_id not in ADMINS_IDS and user_id != OWNER_ID:
                return
            keyboard = InlineKeyboardMarkup(row_width=2).add(
                InlineKeyboardButton("💰 Dar Créditos", callback_data="admin_dar_creditos"),
                InlineKeyboardButton("💸 Quitar Créditos", callback_data="admin_quitar_creditos")
            )
            keyboard.add(InlineKeyboardButton("⬅️ Volver al Menú Principal", callback_data="inicio"))
            await bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption="⚙️ **PANEL DE ADMINISTRADOR**", reply_markup=keyboard, parse_mode="Markdown")

        elif data == "admin_dar_creditos":
            keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Volver al Panel", callback_data="panel_admin"))
            await bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption="💰 Usa en el chat:\n`/darcreditos ID MONTO`", reply_markup=keyboard, parse_mode="Markdown")

        elif data == "admin_quitar_creditos":
            keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Volver al Panel", callback_data="panel_admin"))
            await bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption="💸 Usa en el chat:\n`/quitarcreditos ID MONTO`", reply_markup=keyboard, parse_mode="Markdown")

    except Exception as e:
        # Fallback de seguridad: si Telegram bloquea la edición por contenido idéntico, enviamos un mensaje nuevo limpio
        logger.error(f"Error al editar caption, intentando enviar nuevo mensaje: {e}")
        try:
            await bot.send_message(chat_id, "⚠️ Actualizando menú...", reply_markup=main_menu(user_id))
        except Exception:
            pass

# Comando para difusión de promos
@dp.message_handler(commands=["promo"])
async def cmd_promo(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    
    texto_promo = message.text.replace("/promo", "").strip()
    if not texto_promo:
        await message.reply("❌ Escribe el texto. Ejemplo:\n`/promo 🔥 OFERTA ESPECIAL 🔥`", parse_mode="Markdown")
        return

    promo_keyboard = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("👑 DUEÑO", url="https://t.me/StoreFixersXiters"),
        InlineKeyboardButton("📢 GRUPO", url="https://t.me/StoreFixersXiters"),
    )
    promo_keyboard.add(InlineKeyboardButton("⚠️ TÉRMINOS Y CONDICIONES", url="https://t.me/StoreFixersXiters"))

    enviados = 0
    for uid in ALL_USERS:
        try:
            await bot.send_photo(
                chat_id=uid,
                photo=BANNER_IMAGE_URL,
                caption=f"📢 **AVISO / PROMOCIÓN OFICIAL**\n\n{texto_promo}",
                reply_markup=promo_keyboard,
                parse_mode="Markdown"
            )
            enviados += 1
        except Exception as e:
            logger.error(f"Error enviando promo a {uid}: {e}")

    await message.reply(f"✅ ¡Promoción enviada exitosamente a **{enviados}** usuarios!")

# Comandos administrativos
@dp.message_handler(commands=["darcreditos"])
async def cmd_darcreditos(message: types.Message):
    if message.from_user.id != OWNER_ID and message.from_user.id not in ADMINS_IDS:
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
    if message.from_user.id != OWNER_ID and message.from_user.id not in ADMINS_IDS:
        return
    try:
        partes = message.text.split()
        target_id = int(partes[1])
        cantidad = float(partes[2])
        saldo_actual = USER_CREDITS.get(target_id, 0.0)
        nuevo_saldo = max(0.0, saldo_actual - cantidad)
        USER_CREDITS[target_id] = nuevo_saldo
        await message.reply(f"⚠️ Retirados **${cantidad:.2f}** al usuario `{target_id}`.", parse_mode="Markdown")
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
            await message.reply(f"✅ ¡Usuario `{target_id}` ascendido a Administrador!", parse_mode="Markdown")
        else:
            await message.reply("⚠️ El usuario ya es administrador.")
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
            await message.reply(f"🔻 El usuario `{target_id}` ya no es administrador.", parse_mode="Markdown")
        else:
            await message.reply("⚠️ Ese usuario no está en la lista.")
    except (IndexError, ValueError):
        await message.reply("❌ Uso incorrecto. Ejemplo: `/quitarrango 123456789`", parse_mode="Markdown")

if __name__ == "__main__":
    from aiogram import executor
    logger.info("Iniciando bot con manejo de excepciones y respuesta instantánea...")
    executor.start_polling(dp, skip_updates=True)
    
