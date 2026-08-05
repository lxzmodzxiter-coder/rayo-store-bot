from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler

# ⚠️ TU ID DE OWNER DE TELEGRAM
OWNER_ID = 7939709543

# Base de datos en memoria
DB_USUARIOS = {}

def obtener_o_crear_usuario(user):
    user_id = user.id
    if user_id not in DB_USUARIOS:
        nombre_telegram = user.first_name if user.first_name else "Cliente"
        DB_USUARIOS[user_id] = {
            "nombre": nombre_telegram,
            "id_cuenta": str(user_id),
            "saldo": 0.00
        }
    return DB_USUARIOS[user_id]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    datos_usuario = obtener_o_crear_usuario(user)
    
    keyboard = [
        [InlineKeyboardButton("🛒 VER CATALOGO SOCIOS", callback_data="ver_catalogo")],
        [InlineKeyboardButton("💳 Recargar Saldo", callback_data="recargar"),
         InlineKeyboardButton("🎁 Canjear Cupón", callback_data="cupon")],
        [InlineKeyboardButton("👤 Mi Perfil / Historial", callback_data="perfil")],
        [InlineKeyboardButton("💎 Adquirir Premium ( 10% OFF 💰 )", callback_data="premium")],
        [InlineKeyboardButton("👨‍💻 Soporte Directo", url="https://t.me/TuUsuario"),
         InlineKeyboardButton("📢 Canal Oficial", url="https://t.me/TuCanal")]
    ]
    
    if user_id == OWNER_ID:
        keyboard.insert(0, [InlineKeyboardButton("👑 PANEL DE OWNER / ADMIN", callback_data="panel_owner")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    mensaje = (
        f"🤖 **RESELLERS STORE** 🛍️\n\n"
        f"👤 Cliente: {datos_usuario['nombre']}\n"
        f"🆔 ID de Cuenta: {datos_usuario['id_cuenta']}\n"
        f"💰 Saldo Disponible: ${datos_usuario['saldo']:.2f} USD\n\n"
        f"¿Qué vamos a hacer hoy, bb? Elige una opción:"
    )
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(mensaje, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(mensaje, reply_markup=reply_markup, parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    # ⚡ RESPUESTA INMEDIATA para evitar que Telegram caduque el botón
    try:
        await query.answer()
    except Exception:
        pass

    user = query.from_user
    user_id = user.id
    data = query.data
    datos_usuario = obtener_o_crear_usuario(user)

    if data == "panel_owner":
        if user_id != OWNER_ID:
            return
        total_usuarios = len(DB_USUARIOS)
        keyboard = [
            [InlineKeyboardButton("➕ Agregar Saldo (/dar ID MONTO)", callback_data="info_dar")],
            [InlineKeyboardButton("👥 Ver Clientes Registrados", callback_data="ver_clientes")],
            [InlineKeyboardButton("⬅️ Volver al Inicio", callback_data="inicio")]
        ]
        await query.edit_message_text(
            f"👑 **PANEL DE CONTROL - OWNER**\n\n"
            f"📊 Usuarios en la base: {total_usuarios}\n"
            f"Selecciona una opción:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    elif data == "ver_clientes":
        if user_id != OWNER_ID:
            return
        texto_clientes = "👥 **LISTA DE CLIENTES:**\n\n"
        for uid, info in DB_USUARIOS.items():
            texto_clientes += f"• {info['nombre']} (ID: `{info['id_cuenta']}`) - Saldo: ${info['saldo']:.2f}\n"
        
        keyboard = [[InlineKeyboardButton("⬅️ Volver al Panel", callback_data="panel_owner")]]
        await query.edit_message_text(texto_clientes, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "info_dar":
        if user_id != OWNER_ID:
            return
        keyboard = [[InlineKeyboardButton("⬅️ Volver al Panel", callback_data="panel_owner")]]
        await query.edit_message_text(
            "💡 **CÓMO DAR CRÉDITOS:**\n\n"
            "Usa el comando en el chat:\n"
            "`/dar [ID_DE_TELEGRAM] [MONTO]`\n"
            "Ejemplo: `/dar 7939709543 15`",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    elif data == "ver_catalogo":
        keyboard = [
            [InlineKeyboardButton("📁 DRIP CLIENT OFICIAL 🟣", callback_data="cat_drip")],
            [InlineKeyboardButton("📁 PRODUCTOS EXTRAS 🏠", callback_data="cat_extras")],
            [InlineKeyboardButton("⬅️ Regresar al Inicio", callback_data="inicio")]
        ]
        await query.edit_message_text("📂 **CATEGORÍAS DISPONIBLES** 🎮\nSelecciona la categoría de tu interés:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        
    elif data == "cat_drip":
        keyboard = [
            [InlineKeyboardButton("📦 Drip Client Apk 🛍️", callback_data="comprar_apk")],
            [InlineKeyboardButton("📦 Drip Client Proxy 🛍️", callback_data="comprar_proxy")],
            [InlineKeyboardButton("📦 Drip Client Root 🛍️", callback_data="comprar_root")],
            [InlineKeyboardButton("📦 Drip Client Pc 🛍️", callback_data="comprar_pc")],
            [InlineKeyboardButton("⬅️ Volver a las Categorías", callback_data="ver_catalogo")]
        ]
        await query.edit_message_text("📁 **DRIP CLIENT OFICIAL** 🟣\n\n📦 PRODUCTOS DISPONIBLES 🔥\nSelecciona lo que te vas a llevar:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "cat_extras":
        keyboard = [
            [InlineKeyboardButton("📦 CERTIFICADO GBOX 🛍️", callback_data="comprar_gbox")],
            [InlineKeyboardButton("📦 MONITE CHEATS IOS 🛍️", callback_data="comprar_monite")],
            [InlineKeyboardButton("📦 PRIME HOCK APK 🛍️", callback_data="comprar_prime")],
            [InlineKeyboardButton("📦 PROXY CUBAN 🛍️", callback_data="comprar_cuban")],
            [InlineKeyboardButton("📦 CUBAN MODZ APK 🛍️", callback_data="comprar_cubanmodz")],
            [InlineKeyboardButton("⬅️ Volver a las Categorías", callback_data="ver_catalogo")]
        ]
        await query.edit_message_text("📁 **PRODUCTOS EXTRAS** 🏠\n\n📦 PRODUCTOS DISPONIBLES 🔥\nSelecciona lo que te vas a llevar:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "inicio":
        await start(update, context)

    elif data == "perfil":
        keyboard = [[InlineKeyboardButton("⬅️ Volver al Inicio", callback_data="inicio")]]
        await query.edit_message_text(
            f"👤 **TU PERFIL DE COMPRADOR**\n\n"
            f"Nombre: {datos_usuario['nombre']}\n"
            f"🆔 ID de Telegram: `{datos_usuario['id_cuenta']}`\n"
            f"💰 Saldo Actual: ${datos_usuario['saldo']:.2f} USD",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

async def comando_dar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != OWNER_ID:
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text("⚠️ Uso correcto: `/dar [ID_TELEGRAM] [MONTO]`", parse_mode="Markdown")
        return
    
    id_buscado_str = args[0]
    try:
        monto = float(args[1])
        id_buscado = int(id_buscado_str)
    except ValueError:
        await update.message.reply_text("❌ El ID y el monto deben ser numéricos válidos.")
        return

    # Búsqueda directa ultrarrápida por clave de diccionario sin bucles lentos
    if id_buscado in DB_USUARIOS:
        DB_USUARIOS[id_buscado]["saldo"] += monto
        nombre_cliente = DB_USUARIOS[id_buscado]["nombre"]
    else:
        # Si el usuario no ha iniciado el bot, se crea directamente de forma instantánea
        DB_USUARIOS[id_buscado] = {
            "nombre": "Usuario Externo",
            "id_cuenta": id_buscado_str,
            "saldo": monto
        }
        nombre_cliente = "Usuario Externo"

    nuevo_saldo = DB_USUARIOS[id_buscado]["saldo"]
    await update.message.reply_text(
        f"✅ ¡Éxito!\nSe han añadido ${monto:.2f} USD al usuario **{nombre_cliente}** (ID: `{id_buscado_str}`).\nNuevo saldo: ${nuevo_saldo:.2f} USD",
        parse_mode="Markdown"
    )

if __name__ == '__main__':
    app = ApplicationBuilder().token("8717156909:AAFU4M2eeJpgIBCcjzNfdLx-CoQQE6gJr5Y").build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("dar", comando_dar))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("Bot optimizado y ultrarrápido listo...")
    app.run_polling()
