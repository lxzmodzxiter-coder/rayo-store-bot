    user_id = message.from_user.id
    first_name = message.from_user.first_name
    ALL_USERS.add(user_id)

    try:
        await message.answer_photo(
            photo=BANNER_PRINCIPAL,
            caption=texto_principal(user_id, first_name),
            reply_markup=menu_principal(user_id),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error enviando banner de inicio: {e}")
        await message.answer(
            texto_principal(user_id, first_name),
            reply_markup=menu_principal(user_id),
            parse_mode="Markdown"
        )

# ==========================================
#        NAVEGACIÓN INSTANTÁNEA (UI)
# ==========================================

@dp.callback_query_handler(lambda c: True)
async def process_callback(callback_query: types.CallbackQuery):
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
                reply_markup=menu_principal(user_id), parse_mode="Markdown"
            )

        elif data == "ver_catalogo":
            keyboard = InlineKeyboardMarkup(row_width=2).add(
                InlineKeyboardButton("🤖 ANDROID", callback_data="cat_android"),
                InlineKeyboardButton("🍏 IOS", callback_data="cat_ios")
            )
            keyboard.add(InlineKeyboardButton("⬅️ Volver al Menú", callback_data="inicio"))
            await bot.edit_message_caption(
                chat_id=chat_id, message_id=message_id,
                caption="📂 **CATÁLOGO OFICIAL - RAYO FIX** 🎮\n\nSelecciona tu sistema operativo compatible:",
                reply_markup=keyboard, parse_mode="Markdown"
            )

        elif data == "cat_android":
            keyboard = InlineKeyboardMarkup(row_width=1).add(
                InlineKeyboardButton("📦 DRIP CLIENT APK MOD", callback_data="comprar_prod"),
                InlineKeyboardButton("📦 DRIP CLIENT PROXY", callback_data="comprar_prod"),
                InlineKeyboardButton("📦 HG CHEATS", callback_data="comprar_prod"),
                InlineKeyboardButton("⬅️ Volver al Catálogo", callback_data="ver_catalogo")
            )
            await bot.edit_message_caption(
                chat_id=chat_id, message_id=message_id,
                caption="🤖 **PRODUCTOS ANDROID DISPONIBLES** 📱\nSelecciona una herramienta:",
                reply_markup=keyboard, parse_mode="Markdown"
            )

        elif data == "cat_ios":
            keyboard = InlineKeyboardMarkup(row_width=1).add(
                InlineKeyboardButton("📦 MONITE PRO", callback_data="comprar_prod"),
                InlineKeyboardButton("📦 CERTIFICADOS", callback_data="comprar_prod"),
                InlineKeyboardButton("⬅️ Volver al Catálogo", callback_data="ver_catalogo")
            )
            await bot.edit_message_caption(
                chat_id=chat_id, message_id=message_id,
                caption="🍏 **PRODUCTOS IOS DISPONIBLES** 🍎\nSelecciona una herramienta:",
                reply_markup=keyboard, parse_mode="Markdown"
            )

        elif data == "comprar_prod":
            keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Volver", callback_data="ver_catalogo"))
            await bot.edit_message_caption(
                chat_id=chat_id, message_id=message_id,
                caption="🛒 Para adquirir este producto, contacta directamente con nuestro soporte oficial.",
                reply_markup=keyboard, parse_mode="Markdown"
            )

        elif data == "recargar_saldo":
            keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Volver al Menú", callback_data="inicio"))
            await bot.edit_message_caption(
                chat_id=chat_id, message_id=message_id,
                caption="💳 **CENTRO DE RECARGAS**\n\nComunícate con soporte para añadir fondos a tu cuenta de forma rápida y segura.",
                reply_markup=keyboard, parse_mode="Markdown"
            )

        elif data == "canjear_cupon":
            keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Volver al Menú", callback_data="inicio"))
            await bot.edit_message_caption(
                chat_id=chat_id, message_id=message_id,
                caption="🎟️ **CANJEAR CUPÓN PROMOCIONAL**\n\nEnvía tu código exacto al chat privado de soporte para activarlo.",
                reply_markup=keyboard, parse_mode="Markdown"
            )

        elif data == "mi_perfil":
            saldo = USER_CREDITS.get(user_id, 0.0)
            rango = "👑 Owner" if user_id == OWNER_ID else ("🛡️ Administrador" if user_id in ADMINS_IDS else "👤 Cliente")
            keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Volver al Menú", callback_data="inicio"))
            await bot.edit_message_caption(
                chat_id=chat_id, message_id=message_id,
                caption=f"👤 **MI PERFIL - RAYO FIX**\n\n"
                        f"• **Nombre:** {first_name}\n"
                        f"• **ID:** `{user_id}`\n"
                        f"• **Rango:** {rango}\n"
                        f"• **Saldo Actual:** `${saldo:.2f} USD`",
                reply_markup=keyboard, parse_mode="Markdown"
            )

        elif data == "comprar_premium":
            keyboard = InlineKeyboardMarkup().add(InlineKeyboardButton("⬅️ Volver al Menú", callback_data="inicio"))
            await bot.edit_message_caption(
                chat_id=chat_id, message_id=message_id,
                caption="💎 **MEMBRESÍA PREMIUM (10% OFF)**\n\nObtén beneficios exclusivos y prioridad total.",
                reply_markup=keyboard, parse_mode="Markdown"
            )

        elif data == "panel_owner":
            if user_id != OWNER_ID:
                return
            keyboard = InlineKeyboardMarkup(row_width=2).add(
                InlineKeyboardButton("💰 Dar Créditos", callback_data="owner_dar_creditos"),
                InlineKeyboardButton("💸 Quitar Créditos", callback_data="owner_quitar_creditos"),
                InlineKeyboardButton("🛡️ Dar Rango", callback_data="owner_dar_rango"),
                InlineKeyboardButton("🔻 Quitar Rango", callback_data="owner_quitarrango")
            )
            keyboard.add(InlineKeyboardButton("⬅️ Volver al Menú Principal", callback_data="inicio"))
            await bot.edit_message_caption(
                chat_id=chat_id, message_id=message_id,
                caption="👑 **PANEL DE OWNER**\n\nSelecciona una opción administrativa:",
                reply_markup=keyboard, parse_mode="Markdown"
            )

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

        elif data == "panel_admin":
            if user_id not in ADMINS_IDS and user_id != OWNER_ID:
                return
            keyboard = InlineKeyboardMarkup(row_width=2).add(
                InlineKeyboardButton("💰 Dar Créditos", callback_data="owner_dar_creditos"),
                InlineKeyboardButton("💸 Quitar Créditos", callback_data="owner_quitar_creditos")
            )
            keyboard.add(InlineKeyboardButton("⬅️ Volver al Menú Principal", callback_data="inicio"))
            await bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption="⚙️ **PANEL DE ADMINISTRADOR**", reply_markup=keyboard, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error procesando botón interactivo: {e}")

# ==========================================
#          COMANDOS ADMINISTRATIVOS
# ==========================================

@dp.message_handler(commands=["darcreditos"])
async def cmd_darcreditos(message: types.Message):
    if message.from_user.id != OWNER_ID and message.from_user.id not in ADMINS_IDS:
        return
    try:
        partes = message.text.split()
        target_id = int(partes[1])
        cantidad = float(partes[2])
        USER_CREDITS[target_id] = USER_CREDITS.get(target_id, 0.0) + cantidad
        await message.reply(f"✅ Se añadieron **${cantidad:.2f} USD** al usuario `{target_id}`.", parse_mode="Markdown")
    except (IndexError, ValueError):
        await message.reply("❌ Formato incorrecto. Uso:\n`/darcreditos 123456789 10`", parse_mode="Markdown")

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
        await message.reply(f"⚠️ Se retiraron **${cantidad:.2f} USD** al usuario `{target_id}`.", parse_mode="Markdown")
    except (IndexError, ValueError):
        await message.reply("❌ Formato incorrecto. Uso:\n`/quitarcreditos 123456789 5`", parse_mode="Markdown")

@dp.message_handler(commands=["darrango"])
async def cmd_darrango(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        target_id = int(message.text.split()[1])
        if target_id not in ADMINS_IDS and target_id != OWNER_ID:
            ADMINS_IDS.append(target_id)
            await message.reply(f"✅ ¡El usuario `{target_id}` ahora es Administrador!", parse_mode="Markdown")
        else:
            await message.reply("⚠️ El usuario ya cuenta con este rango o es el dueño.")
    except (IndexError, ValueError):
        await message.reply("❌ Formato incorrecto. Uso:\n`/darrango 123456789`", parse_mode="Markdown")

@dp.message_handler(commands=["quitarrango"])
async def cmd_quitarrango(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        target_id = int(message.text.split()[1])
        if target_id in ADMINS_IDS:
            ADMINS_IDS.remove(target_id)
            await message.reply(f"🔻 El usuario `{target_id}` ya no es Administrador.", parse_mode="Markdown")
        else:
            await message.reply("⚠️ El usuario no se encuentra en la lista de administradores.")
    except (IndexError, ValueError):
        await message.reply("❌ Formato incorrecto. Uso:\n`/quitarrango 123456789`", parse_mode="Markdown")

# ==========================================
#      INICIO SEGURO CONTRA FLOOD CONTROL
# ==========================================

if __name__ == "__main__":
    from aiogram import executor
    logger.info("Iniciando Bot de Telegram Profesional con control de estabilidad...")
    
    # Bucle inteligente para reintentar la conexión si Telegram banea temporalmente por reinicios de Render
    while True:
        try:
            executor.start_polling(dp, skip_updates=True)
        except Exception as e:
            logger.error(f"Error en el ciclo de polling: {e}. Esperando 20 segundos para reintentar...")
            time.sleep(20)
    
