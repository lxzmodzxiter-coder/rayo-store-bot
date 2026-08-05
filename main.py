import logging
import os
from threading import Thread
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

logging.basicConfig(level=logging.INFO)

# --- MINI SERVIDOR WEB PARA RENDER ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "¡Rayo Store Bot está activo y funcionando perfectamente!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host="0.0.0.0", port=port)

Thread(target=run_web, daemon=True).start()
# -------------------------------------

# Configuración del Bot
app = Client(
    "rayo_store_bot",
    api_id=38961296,
    api_hash="ff178285b739a05289139f74f397a3ba",
    bot_token="8717156909:AAGh4hpveIzg61gG1nGFtdg-aCi94YA05cE"
)

OWNER_ID = 7939709543  
ADMINS_IDS = []  
USER_CREDITS = {}  

# Manejador universal para cualquier mensaje o comando /start
@app.on_message(filters.private)
async def all_messages(client, message):
    texto = message.text if message.text else ""
    user_id = message.from_user.id
    
    # Si escriben start o cualquier cosa, respondemos con el menú
    keyboard = [
        [InlineKeyboardButton("📂 VER CATÁLOGO", callback_data="ver_catalogo")],
        [InlineKeyboardButton("💳 MIS CRÉDITOS", callback_data="ver_mis_creditos")],
        [InlineKeyboardButton("⚙️ PANEL", callback_data="abrir_panel")]
    ]
    
    await message.reply_text(
        "👋 ¡Bienvenido a **Rayo Store**!\n\nSelecciona una de las opciones del menú:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# --- MANEJADOR DE BOTONES (CALLBACKS) ---
@app.on_callback_query()
async def callback_handler(client, callback_query):
    data = callback_query.data
    user_id = callback_query.from_user.id

    try:
        if data == "inicio":
            keyboard = [
                [InlineKeyboardButton("📂 VER CATÁLOGO", callback_data="ver_catalogo")],
                [InlineKeyboardButton("💳 MIS CRÉDITOS", callback_data="ver_mis_creditos")],
                [InlineKeyboardButton("⚙️ PANEL", callback_data="abrir_panel")]
            ]
            await callback_query.message.edit_text(
                "👋 ¡Bienvenido a **Rayo Store**!\n\nSelecciona una de las opciones del menú:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )

        elif data == "ver_catalogo":
            keyboard = [
                [InlineKeyboardButton("🤖 ANDROID", callback_data="cat_android")],
                [InlineKeyboardButton("🍏 IOS", callback_data="cat_ios")],
                [InlineKeyboardButton("⬅️ Regresar al Inicio", callback_data="inicio")]
            ]
            await callback_query.message.edit_text(
                "📂 **TENEMOS PRODUCTOS FULL PRINCIPAL** 🎮\nSelecciona tu sistema operativo:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )

        elif data == "cat_android":
            keyboard = [
                [InlineKeyboardButton("📦 DRIP CLIENT APK MOD", callback_data="comprar_prod")],
                [InlineKeyboardButton("📦 DRIP CLIENT PROXY", callback_data="comprar_prod")],
                [InlineKeyboardButton("📦 HG CHEATS", callback_data="comprar_prod")],
                [InlineKeyboardButton("📦 HOLO VIP", callback_data="comprar_prod")],
                [InlineKeyboardButton("📦 CUBAN PROXY", callback_data="comprar_prod")],
                [InlineKeyboardButton("📦 CUBAN APK MOD", callback_data="comprar_prod")],
                [InlineKeyboardButton("📦 HG CHEATS PROXY", callback_data="comprar_prod")],
                [InlineKeyboardButton("📦 FFH4X", callback_data="comprar_prod")],
                [InlineKeyboardButton("📦 BR MODS", callback_data="comprar_prod")],
                [InlineKeyboardButton("📦 Strick BR", callback_data="comprar_prod")],
                [InlineKeyboardButton("⬅️ Volver", callback_data="ver_catalogo")]
            ]
            await callback_query.message.edit_text(
                "🤖 **PRODUCTOS ANDROID** 📱\n\nElige tu producto:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )

        elif data == "cat_ios":
            keyboard = [
                [InlineKeyboardButton("📦 MONITE PRO", callback_data="comprar_prod")],
                [InlineKeyboardButton("📦 MONITE BASICO", callback_data="comprar_prod")],
                [InlineKeyboardButton("📦 CERTIFICADOS", callback_data="comprar_prod")],
                [InlineKeyboardButton("📦 PROXY POTATSO", callback_data="comprar_prod")],
                [InlineKeyboardButton("📦 ESIG ANUAL", callback_data="comprar_prod")],
                [InlineKeyboardButton("📦 FLUCK IOS", callback_data="comprar_prod")],
                [InlineKeyboardButton("⬅️ Volver", callback_data="ver_catalogo")]
            ]
            await callback_query.message.edit_text(
                "🍏 **PRODUCTOS IOS** 🍎\n\nElige tu producto:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )

        elif data == "comprar_prod":
            keyboard = [[InlineKeyboardButton("⬅️ Volver al Catálogo", callback_data="ver_catalogo")]]
            await callback_query.message.edit_text(
                "🛒 Para adquirir este producto, contacta con soporte o utiliza tus créditos disponibles.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        elif data == "ver_mis_creditos":
            saldo = USER_CREDITS.get(user_id, 0)
            keyboard = [[InlineKeyboardButton("⬅️ Volver al Inicio", callback_data="inicio")]]
            await callback_query.message.edit_text(
                f"💳 Tu saldo actual es de: **{saldo} créditos**.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )

        elif data == "abrir_panel":
            if user_id == OWNER_ID:
                keyboard = [
                    [InlineKeyboardButton("➕ Agregar Admin", callback_data="owner_add_admin")],
                    [InlineKeyboardButton("📋 Ver Lista de Admins", callback_data="owner_list_admins")],
                    [InlineKeyboardButton("💰 Gestionar Créditos", callback_data="admin_credits_menu")],
                    [InlineKeyboardButton("❌ Cerrar Panel", callback_data="cerrar")]
                ]
                await callback_query.message.edit_text("👑 **PANEL DE OWNER**\n\nSelecciona una opción:", reply_markup=InlineKeyboardMarkup(keyboard))
            elif user_id in ADMINS_IDS:
                keyboard = [
                    [InlineKeyboardButton("📋 Ver Lista de Admins", callback_data="owner_list_admins")],
                    [InlineKeyboardButton("💰 Gestionar Créditos", callback_data="admin_credits_menu")],
                    [InlineKeyboardButton("❌ Cerrar Panel", callback_data="cerrar")]
                ]
                await callback_query.message.edit_text("🛡️ **PANEL DE ADMINISTRADOR**\n\nSelecciona una opción:", reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                await callback_query.answer("❌ No tienes permisos para abrir el panel.", show_alert=True)

        elif data == "owner_add_admin":
            if user_id != OWNER_ID:
                return
            keyboard = [[InlineKeyboardButton("⬅️ Volver al Panel", callback_data="abrir_panel")]]
            await callback_query.message.edit_text(
                "➕ **AGREGAR NUEVO ADMIN**\n\nEnvíame el comando por chat privado:\n`/addadmin ID_DEL_USUARIO`",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        elif data == "owner_list_admins":
            if user_id != OWNER_ID and user_id not in ADMINS_IDS:
                return
            admins_text = "\n".join([str(aid) for aid in ADMINS_IDS]) if ADMINS_IDS else "No hay administradores registrados."
            keyboard = [[InlineKeyboardButton("⬅️ Volver al Panel", callback_data="abrir_panel")]]
            await callback_query.message.edit_text(f"📋 **LISTA DE ADMINISTRADORES:**\n\n{admins_text}", reply_markup=InlineKeyboardMarkup(keyboard))

        elif data == "admin_credits_menu":
            if user_id != OWNER_ID and user_id not in ADMINS_IDS:
                return
            keyboard = [
                [InlineKeyboardButton("➕ Dar Créditos", callback_data="abrir_panel")],
                [InlineKeyboardButton("➖ Quitar Créditos", callback_data="abrir_panel")],
                [InlineKeyboardButton("⬅️ Volver al Panel", callback_data="abrir_panel")]
            ]
            await callback_query.message.edit_text(
                "💰 **GESTIÓN DE CRÉDITOS**\n\nUsa los comandos directos en el chat:\n• `/darcreditos ID MONTO`\n• `/quitarcreditos ID MONTO`",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        elif data == "cerrar":
            await callback_query.message.delete()
            
    except Exception:
        try:
            await callback_query.answer()
        except:
            pass

if __name__ == "__main__":
    print("Iniciando bot con escucha general...")
    app.run()
                                          
