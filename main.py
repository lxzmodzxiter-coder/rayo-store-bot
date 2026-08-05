import logging
import os
import sqlite3
import time
import traceback
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest

# Configuración de logs profesionales
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- SERVIDOR WEB PARA MANTENER ACTIVO EN RENDER ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "¡Rayo Fix Store Bot está activo y operando al 100%!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host="0.0.0.0", port=port)

Thread(target=run_web, daemon=True).start()
# ---------------------------------------------------

# Credenciales y Configuración Segura por Variables de Entorno
TOKEN = os.getenv("BOT_TOKEN", "8799688315:AAH3afiU9b8RdEuWtCtj3ooBTopEgaJMFFg")
OWNER_ID = int(os.getenv("OWNER_ID", "7939709543"))

bot = Bot(token=TOKEN)
dp = Dispatcher()

BANNER_PRINCIPAL = "https://i.ibb.co/3m20gX28/51614.jpg"

# ==========================================
#      BASE DE DATOS (SQLite Integrada)
# ==========================================
def init_db():
    conn = sqlite3.connect("rayofix.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            username TEXT,
            saldo REAL DEFAULT 0.0,
            rango TEXT DEFAULT 'Cliente',
            is_premium INTEGER DEFAULT 0,
            fecha_registro TEXT,
            invitador INTEGER DEFAULT 0
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            categoria TEXT,
            nombre TEXT,
            precio REAL,
            descripcion TEXT,
            stock INTEGER
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS compras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            producto TEXT,
            precio REAL,
            fecha TEXT
        )
    """)
    
    conn.commit()
    conn.close()

init_db()

def es_admin_o_owner(user_id: int) -> bool:
    if user_id == OWNER_ID:
        return True
    conn = sqlite3.connect("rayofix.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM admins WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res is not None

# ==========================================
#         MENÚS Y ESTÉTICA (UI/UX)
# ==========================================
def menu_principal(user_id: int) -> InlineKeyboardMarkup:
    is_owner = (user_id == OWNER_ID)
    is_admin = es_admin_o_owner(user_id)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🛍️ Catálogo", callback_data="ver_catalogo"),
            InlineKeyboardButton(text="👤 Perfil", callback_data="mi_perfil")
        ],
        [
            InlineKeyboardButton(text="💳 Recargar", callback_data="recargar_saldo"),
            InlineKeyboardButton(text="🎟️ Cupones", callback_data="canjear_cupon")
        ],
        [
            InlineKeyboardButton(text="💎 Premium", callback_data="comprar_premium"),
            InlineKeyboardButton(text="📦 Compras", callback_data="mis_compras")
        ],
        [
            InlineKeyboardButton(text="📞 Soporte", url="https://t.me/StoreFixersXiters"),
            InlineKeyboardButton(text="📢 Canal", url="https://t.me/StoreFixersXiters")
        ]
    ])

    if is_owner:
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="👑 Panel Owner", callback_data="panel_owner")])
    elif is_admin:
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="⚙️ Panel Admin", callback_data="panel_admin")])
    
    return keyboard

def texto_principal(user_id: int, first_name: str) -> str:
    conn = sqlite3.connect("rayofix.db")
    cursor = conn.cursor()
    cursor.execute("SELECT saldo, rango, is_premium FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    saldo = row[0] if row else 0.0
    rango = row[1] if row else "Cliente"
    premium = "💎 Sí" if (row and row[2] == 1) else "No"

    return (
        f"⚡ **RAYO FIX STORE** ⚡\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 **Cliente:** {first_name}\n"
        f"🆔 **ID:** `{user_id}`\n"
        f"💰 **Saldo:** `${saldo:.2f} USD`\n"
        f"⭐ **Rango:** {rango} | **Premium:** {premium}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Selecciona una opción del menú:"
    )

# ==========================================
#     FUNCIÓN SEGURA DE EDICIÓN (ANTI-ERROR)
# ==========================================
async def actualizar_pantalla(callback: CallbackQuery, nuevo_texto: str, reply_markup: InlineKeyboardMarkup):
    message = callback.message
    try:
        if message.photo:
            await bot.edit_message_caption(
                chat_id=message.chat.id,
                message_id=message.message_id,
                caption=nuevo_texto,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        else:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=message.message_id,
                text=nuevo_texto,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            return
        logger.error(f"Error de Telegram al actualizar pantalla: {e}")
    except Exception as e:
        logger.error(f"Error general al actualizar pantalla: {e}")
        traceback.print_exc()

# ==========================================
#              COMANDO /START
# ==========================================
@dp.message(F.text.startswith("/start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    username = message.from_user.username or "Sin username"
    fecha = time.strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect("rayofix.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO users (user_id, first_name, username, fecha_registro) 
        VALUES (?, ?, ?, ?)
    """, (user_id, first_name, username, fecha))
    conn.commit()
    conn.close()

    try:
        await message.answer_photo(
            photo=BANNER_PRINCIPAL,
            caption=texto_principal(user_id, first_name),
            reply_markup=menu_principal(user_id),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error en /start al enviar foto: {e}")
        await message.answer(
            texto_principal(user_id, first_name),
            reply_markup=menu_principal(user_id),
            parse_mode="Markdown"
        )

# ==========================================
#           NAVEGACIÓN INTERACTIVA
# ==========================================
@dp.callback_query()
async def process_callback(callback: CallbackQuery):
    await callback.answer()

    data = callback.data
    user_id = callback.from_user.id
    first_name = callback.from_user.first_name

    try:
        if data == "inicio":
            await actualizar_pantalla(callback, texto_principal(user_id, first_name), menu_principal(user_id))

        elif data == "ver_catalogo":
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📱 Android", callback_data="cat_Android")],
                [InlineKeyboardButton(text="🍎 iPhone / iOS", callback_data="cat_iOS")],
                [InlineKeyboardButton(text="🖥️ Windows / PC", callback_data="cat_PC")],
                [InlineKeyboardButton(text="⬅️ Volver al Menú", callback_data="inicio")]
            ])
            await actualizar_pantalla(callback, "📂 **CATÁLOGO DE PRODUCTOS**\n\nElige una categoría:", keyboard)

        elif data.startswith("cat_"):
            categoria = data.split("_")[1]
            if categoria == "PC":
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Volver al Catálogo", callback_data="ver_catalogo")]
                ])
                await actualizar_pantalla(callback, "🖥️ **WINDOWS / PC**\n\n🚧 Próximamente...", keyboard)
                return

            conn = sqlite3.connect("rayofix.db")
            cursor = conn.cursor()
            cursor.execute("SELECT id, nombre, precio FROM productos WHERE categoria = ?", (categoria,))
            prods = cursor.fetchall()
            conn.close()

            keyboard = []
            for p_id, p_nombre, p_precio in prods:
                keyboard.append([InlineKeyboardButton(text=f"📦 {p_nombre} - ${p_precio:.2f}", callback_data=f"ver_prod_{p_id}")])
            keyboard.append([InlineKeyboardButton(text="⬅️ Volver al Catálogo", callback_data="ver_catalogo")])

            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            texto_cat = f"📂 **CATEGORÍA: {categoria.upper()}**\n\nSelecciona un producto:" if prods else f"📂 **CATEGORÍA: {categoria.upper()}**\n\n⚠️ No hay productos disponibles por el momento."
            await actualizar_pantalla(callback, texto_cat, markup)

        elif data.startswith("ver_prod_"):
            p_id = int(data.split("_")[2])
            conn = sqlite3.connect("rayofix.db")
            cursor = conn.cursor()
            cursor.execute("SELECT nombre, precio, descripcion, stock FROM productos WHERE id = ?", (p_id,))
            prod = cursor.fetchone()
            conn.close()

            if prod:
                nombre, precio, descripcion, stock = prod
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=f"🛒 Comprar (${precio:.2f})", callback_data=f"comprar_{p_id}")],
                    [InlineKeyboardButton(text="⬅️ Volver", callback_data="ver_catalogo")]
                ])
                caption = f"📦 **{nombre}**\n\n📝 **Descripción:** {descripcion}\n💰 **Precio:** `${precio:.2f} USD`\n📦 **Stock:** `{stock}` unidades"
                await actualizar_pantalla(callback, caption, keyboard)

        elif data.startswith("comprar_"):
            p_id = int(data.split("_")[1])
            conn = sqlite3.connect("rayofix.db")
            cursor = conn.cursor()
            cursor.execute("SELECT saldo FROM users WHERE user_id = ?", (user_id,))
            user_saldo_row = cursor.fetchone()
            user_saldo = user_saldo_row[0] if user_saldo_row else 0.0

            cursor.execute("SELECT nombre, precio, stock FROM productos WHERE id = ?", (p_id,))
            prod = cursor.fetchone()
            
            if prod:
                nombre, precio, stock = prod
                if stock <= 0:
                    await callback.answer("❌ Producto sin stock.", show_alert=True)
                elif user_saldo < precio:
                    await callback.answer("❌ Saldo insuficiente. Recarga tu cuenta.", show_alert=True)
                else:
                    nuevo_saldo = user_saldo - precio
                    cursor.execute("UPDATE users SET saldo = ? WHERE user_id = ?", (nuevo_saldo, user_id))
                    cursor.execute("UPDATE productos SET stock = stock - 1 WHERE id = ?", (p_id,))
                    cursor.execute("INSERT INTO compras (user_id, producto, precio, fecha) VALUES (?, ?, ?, ?)", 
                                   (user_id, nombre, precio, time.strftime("%Y-%m-%d %H:%M:%S")))
                    conn.commit()
                    await callback.answer("✅ ¡Compra realizada con éxito!", show_alert=True)
            conn.close()
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Volver al Menú", callback_data="inicio")]])
            await actualizar_pantalla(callback, "🎉 ¡Gracias por tu compra! Revisa los detalles en tu historial.", keyboard)

        elif data == "mi_perfil":
            conn = sqlite3.connect("rayofix.db")
            cursor = conn.cursor()
            cursor.execute("SELECT saldo, rango, is_premium, fecha_registro FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            conn.close()
            
            saldo = row[0] if row else 0.0
            rango = row[1] if row else "Cliente"
            prem = "Sí" if (row and row[2]==1) else "No"
            f_reg = row[3] if row else "N/D"

            keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Volver al Menú", callback_data="inicio")]])
            texto_perfil = (
                f"👤 **MI PERFIL - RAYO FIX**\n\n"
                f"• **Nombre:** {first_name}\n"
                f"• **ID:** `{user_id}`\n"
                f"• **Saldo:** `${saldo:.2f} USD`\n"
                f"• **Rango:** {rango}\n"
                f"• **Premium:** {prem}\n"
                f"• **Registro:** {f_reg}"
            )
            await actualizar_pantalla(callback, texto_perfil, keyboard)

        elif data == "recargar_saldo":
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Volver al Menú", callback_data="inicio")]])
            texto_recarga = (
                "💳 **MÉTODOS DE PAGO / RECARGA**\n\n"
                "Puedes recargar mediante:\n"
                "🇵🇪 **Yape / Plin**\n"
                "🌐 **Binance Pay / USDT (TRC20)**\n\n"
                "Envía el comprobante directamente a nuestro soporte con tu ID de cuenta."
            )
            await actualizar_pantalla(callback, texto_recarga, keyboard)

        elif data == "canjear_cupon":
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Volver al Menú", callback_data="inicio")]])
            await actualizar_pantalla(callback, "🎟️ **CANJEAR CUPÓN**\n\nEnvía tu código promocional al chat de soporte para aplicarlo.", keyboard)

        elif data == "comprar_premium":
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Volver al Menú", callback_data="inicio")]])
            await actualizar_pantalla(callback, "💎 **MEMBRESÍA PREMIUM (10% OFF)**\n\nObtén beneficios exclusivos comunicándote con soporte.", keyboard)

        elif data == "mis_compras":
            conn = sqlite3.connect("rayofix.db")
            cursor = conn.cursor()
            cursor.execute("SELECT producto, precio, fecha FROM compras WHERE user_id = ?", (user_id,))
            compras = cursor.fetchall()
            conn.close()

            texto_compras = "📦 **HISTORIAL DE COMPRAS**\n\n"
            if compras:
                for prod, precio, fecha in compras:
                    texto_compras += f"• **{prod}** - `${precio:.2f}` ({fecha})\n"
            else:
                texto_compras += "No registras compras recientes."

            keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Volver al Menú", callback_data="inicio")]])
            await actualizar_pantalla(callback, texto_compras, keyboard)

        # --- PANEL DE OWNER Y ADMIN ---
        elif data == "panel_owner":
            if user_id != OWNER_ID:
                return
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="➕ Agregar Producto", callback_data="owner_add_prod"),
                    InlineKeyboardButton(text="🗑️ Eliminar Producto", callback_data="owner_del_prod")
                ],
                [
                    InlineKeyboardButton(text="💰 Dar Saldo", callback_data="owner_dar_saldo"),
                    InlineKeyboardButton(text="🛡️ Dar Admin", callback_data="owner_dar_admin")
                ],
                [InlineKeyboardButton(text="⬅️ Volver al Menú", callback_data="inicio")]
            ])
            await actualizar_pantalla(callback, "👑 **PANEL DE OWNER**\n\nGestión general del sistema:", keyboard)

        elif data == "owner_add_prod":
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Volver al Panel", callback_data="panel_owner")]])
            await actualizar_pantalla(callback, "➕ **AGREGAR PRODUCTO**\n\nUsa el comando en el chat:\n`/addprod Categoria Nombre Precio Stock Descripcion`", keyboard)

        elif data == "owner_del_prod":
            conn = sqlite3.connect("rayofix.db")
            cursor = conn.cursor()
            cursor.execute("SELECT id, nombre FROM productos")
            prods = cursor.fetchall()
            conn.close()

            keyboard = []
            for p_id, p_nombre in prods:
                keyboard.append([InlineKeyboardButton(text=f"❌ Eliminar: {p_nombre}", callback_data=f"del_p_{p_id}")])
            keyboard.append([InlineKeyboardButton(text="⬅️ Volver al Panel", callback_data="panel_owner")])

            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            await actualizar_pantalla(callback, "🗑️ **ELIMINAR PRODUCTOS**\n\nSelecciona el producto a retirar:", markup)

        elif data.startswith("del_p_"):
            p_id = int(data.split("_")[2])
            conn = sqlite3.connect("rayofix.db")
            cursor = conn.cursor()
            cursor.execute("DELETE FROM productos WHERE id = ?", (p_id,))
            conn.commit()
            conn.close()
            await callback.answer("✅ Producto eliminado con éxito.", show_alert=True)
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Volver al Panel", callback_data="panel_owner")]])
            await actualizar_pantalla(callback, "✅ Producto eliminado correctamente.", keyboard)

        elif data == "owner_dar_saldo":
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Volver al Panel", callback_data="panel_owner")]])
            await actualizar_pantalla(callback, "💰 **DAR SALDO**\n\nUsa en el chat:\n`/darsaldo ID_USUARIO MONTO`", keyboard)

        elif data == "owner_dar_admin":
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Volver al Panel", callback_data="panel_owner")]])
            await actualizar_pantalla(callback, "🛡️ **DAR ADMIN**\n\nUsa en el chat:\n`/daradmin ID_USUARIO`", keyboard)

        elif data == "panel_admin":
            if not es_admin_o_owner(user_id):
                return
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💰 Dar Saldo", callback_data="owner_dar_saldo")],
                [InlineKeyboardButton(text="⬅️ Volver al Menú", callback_data="inicio")]
            ])
            await actualizar_pantalla(callback, "⚙️ **PANEL DE ADMINISTRADOR**", keyboard)

    except Exception as e:
        logger.error(f"Error crítico en callback general: {e}")
        traceback.print_exc()

# ==========================================
#          COMANDOS DE GESTIÓN (ADMIN)
# ==========================================
@dp.message(F.text.startswith("/addprod"))
async def cmd_addprod(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        partes = message.text.split(maxsplit=5)
        categoria = partes[1]
        nombre = partes[2]
        precio = float(partes[3])
        stock = int(partes[4])
        descripcion = partes[5]

        conn = sqlite3.connect("rayofix.db")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO productos (categoria, nombre, precio, stock, descripcion) 
            VALUES (?, ?, ?, ?, ?)
        """, (categoria, nombre, precio, stock, descripcion))
        conn.commit()
        conn.close()
        await message.reply(f"✅ Producto **{nombre}** agregado con éxito a la categoría **{categoria}**.", parse_mode="Markdown")
    except Exception:
        await message.reply("❌ Formato incorrecto. Uso:\n`/addprod Android DripMod 5.00 10 APK Modificado`", parse_mode="Markdown")

@dp.message(F.text.startswith("/darsaldo"))
async def cmd_darsaldo(message: Message):
    if not es_admin_o_owner(message.from_user.id):
        return
    try:
        partes = message.text.split()
        target_id = int(partes[1])
        monto = float(partes[2])

        conn = sqlite3.connect("rayofix.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET saldo = saldo + ? WHERE user_id = ?", (monto, target_id))
        conn.commit()
        conn.close()
        await message.reply(f"✅ Se agregaron **${monto:.2f} USD** al usuario `{target_id}`.", parse_mode="Markdown")
    except Exception:
        await message.reply("❌ Uso incorrecto. Ejemplo: `/darsaldo 123456789 10`", parse_mode="Markdown")

@dp.message(F.text.startswith("/daradmin"))
async def cmd_daradmin(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        target_id = int(message.text.split()[1])
        conn = sqlite3.connect("rayofix.db")
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (target_id,))
        cursor.execute("UPDATE users SET rango = 'Administrador' WHERE user_id = ?", (target_id,))
        conn.commit()
        conn.close()
        await message.reply(f"✅ Usuario `{target_id}` ascendido a Administrador.", parse_mode="Markdown")
    except Exception:
        await message.reply("❌ Uso incorrecto. Ejemplo: `/daradmin 123456789`", parse_mode="Markdown")

# ==========================================
#              INICIO DEL BOT
# ==========================================
async def main():
    logger.info("Iniciando Rayo Fix Store Bot con aiogram 3.x...")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    import asyncio
    while True:
        try:
            asyncio.run(main())
        except Exception as e:
            logger.error(f"Error crítico en polling: {e}. Reiniciando en 15 segundos...")
            time.sleep(15)
    
