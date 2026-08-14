#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
⚡ LXZ STORE BEST - Bot de Ventas Profesional para Telegram
"""

import logging
import datetime
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from database import Database

# ==========================================
# ⚙️ CONFIGURACIÓN Y LOGS
# ==========================================
TOKEN = "TU_TOKEN_AQUI"  # Reemplazar con el token real de BotFather
OWNER_ID = 123456789     # Reemplazar con tu Telegram ID real (Dueño)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("LXZStoreBest")

# ==========================================
# 🛡️ CAPA DE SEGURIDAD Y PERMISOS
# ==========================================
class Security:
    @staticmethod
    def is_owner(user_id: int) -> bool:
        return user_id == OWNER_ID

    @staticmethod
    def is_admin(user_id: int) -> bool:
        if Security.is_owner(user_id):
            return True
        with Database.get_connection() as conn:
            res = conn.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,)).fetchone()
            return res is not None

    @staticmethod
    def is_banned(user_id: int) -> bool:
        with Database.get_connection() as conn:
            res = conn.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,)).fetchone()
            return res and res["is_banned"] == 1

    @classmethod
    def log_action(cls, user_id: int, action: str, result: str) -> None:
        try:
            with Database.get_connection() as conn:
                conn.execute(
                    "INSERT INTO logs (timestamp, user_id, action, result) VALUES (?, ?, ?, ?)",
                    (datetime.datetime.now().isoformat(), user_id, action, result)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Error registrando log: {e}")

# ==========================================
# 👤 GESTIÓN DE USUARIOS
# ==========================================
class UserManager:
    @staticmethod
    def get_or_create_user(user_id: int, username: str, full_name: str, referred_by = None) -> sqlite3.Row if 'sqlite3' in globals() else object:
        with Database.get_connection() as conn:
            cursor = conn.cursor()
            user = cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
            if not user:
                now = datetime.datetime.now().isoformat()
                ref_valid = None
                if referred_by and referred_by != user_id:
                    parent = cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (referred_by,)).fetchone()
                    if parent:
                        ref_valid = referred_by
                        cursor.execute("UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?", (ref_valid,))
                
                cursor.execute(
                    """INSERT INTO users (user_id, username, full_name, balance, total_spent, is_premium, is_banned, referred_by, referral_count, registered_at)
                       VALUES (?, ?, ?, 0.0, 0.0, 0, 0, ?, 0, ?)""",
                    (user_id, username or "Sin username", full_name, ref_valid, now)
                )
                conn.commit()
                user = cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
                Security.log_action(user_id, "REGISTRO_USUARIO", "EXITOSO")
            return user

# ==========================================
# 🧩 CONSTRUCTOR DE TECLADOS Y NAVEGACIÓN
# ==========================================
class Keyboards:
    @staticmethod
    def main_menu(user_id: int) -> InlineKeyboardMarkup:
        keyboard = [
            [InlineKeyboardButton("🛍️ Catálogo", callback_data="cat_categories"), InlineKeyboardButton("👤 Mi Perfil", callback_data="user_profile")],
            [InlineKeyboardButton("📦 Mis Compras", callback_data="user_purchases"), InlineKeyboardButton("💳 Recargar Saldo", callback_data="wallet_recharge")],
            [InlineKeyboardButton("🎟️ Cupones", callback_data="user_coupons"), InlineKeyboardButton("💎 Premium", callback_data="user_premium")],
            [InlineKeyboardButton("🎁 Referidos", callback_data="user_referrals"), InlineKeyboardButton("📞 Soporte", callback_data="support_info")],
            [InlineKeyboardButton("📢 Canal Oficial", url="https://t.me/TuCanalOficial")]
        ]
        if Security.is_owner(user_id):
            keyboard.append([InlineKeyboardButton("👑 Panel Owner", callback_data="owner_panel")])
        elif Security.is_admin(user_id):
            keyboard.append([InlineKeyboardButton("⚙️ Panel Admin", callback_data="admin_panel")])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def back_to_start() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Inicio", callback_data="main_menu")]])

    @staticmethod
    def back_and_home(back_callback: str) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Atrás", callback_data=back_callback), InlineKeyboardButton("🏠 Inicio", callback_data="main_menu")]
        ])

# ==========================================
# 🚀 CONTROLADORES DE INTERFAZ Y FLUJOS
# ==========================================
class BotHandlers:
    @staticmethod
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if Security.is_banned(user.id):
            if update.message:
                await update.message.reply_text(
                    "🚫 **ACCESO RESTRINGIDO**\n\nTu acceso a **LXZ STORE BEST** se encuentra limitado.",
                    parse_mode="Markdown"
                )
            return

        ref_id = None
        if context.args:
            try:
                ref_id = int(context.args[0])
            except ValueError:
                pass

        UserManager.get_or_create_user(user.id, user.username, user.full_name, ref_id)

        welcome_text = (
            f"⚡ **BIENVENIDO A LXZ STORE BEST** ⚡\n\n"
            f"Hola, **{user.full_name}**.\n"
            f"Tu tienda digital profesional, rápida y segura.\n\n"
            f"Selecciona una opción en el menú inferior:"
        )

        if update.message:
            await update.message.reply_text(
                welcome_text, reply_markup=Keyboards.main_menu(user.id), parse_mode="Markdown"
            )
        elif update.callback_query:
            query = update.callback_query
            await query.answer()
            await query.edit_message_text(
                welcome_text, reply_markup=Keyboards.main_menu(user.id), parse_mode="Markdown"
            )

    @staticmethod
    async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        user = update.effective_user
        data = query.data

        if Security.is_banned(user.id):
            await query.answer("Acceso restringido.", show_alert=True)
            return

        try:
            if data == "main_menu":
                await query.answer()
                await query.edit_message_text(
                    f"⚡ **LXZ STORE BEST** - Menú Principal\n\nSelecciona una opción:",
                    reply_markup=Keyboards.main_menu(user.id),
                    parse_mode="Markdown"
                )

            elif data == "user_profile":
                with Database.get_connection() as conn:
                    u_data = conn.execute("SELECT * FROM users WHERE user_id = ?", (user.id,)).fetchone()
                
                profile_text = (
                    f"👤 **MI PERFIL**\n\n"
                    f"📌 **Nombre:** {u_data['full_name']}\n"
                    f"🔖 **Username:** @{u_data['username']}\n"
                    f"🆔 **ID:** `{u_data['user_id']}`\n"
                    f"💰 **Saldo:** ${u_data['balance']:.2f}\n"
                    f"💎 **Premium:** {'🟢 Activo' if u_data['is_premium'] else '🔴 Inactivo'}\n"
                    f"📦 **Compras:** {u_data['referral_count'] or 0}\n"
                    f"💵 **Total gastado:** ${u_data['total_spent']:.2f}\n"
                    f"🎁 **Referidos:** {u_data['referral_count']}\n"
                    f"📅 **Registro:** {u_data['registered_at'][:10]}\n"
                    f"🚫 **Estado:** Activo"
                )
                await query.answer()
                await query.edit_message_text(profile_text, reply_markup=Keyboards.back_and_home("main_menu"), parse_mode="Markdown")

            elif data == "cat_categories":
                kb = [
                    [InlineKeyboardButton("🤖 Android", callback_data="cat_list_Android"), InlineKeyboardButton("🍎 iOS / iPhone", callback_data="cat_list_iOS")],
                    [InlineKeyboardButton("💻 Windows / PC", callback_data="cat_list_Windows"), InlineKeyboardButton("🌐 Otros", callback_data="cat_list_Otros")],
                    [InlineKeyboardButton("⬅️ Atrás", callback_data="main_menu"), InlineKeyboardButton("🏠 Inicio", callback_data="main_menu")]
                ]
                await query.answer()
                await query.edit_message_text("🛍️ **CATEGORÍAS DE CATÁLOGO**\n\nSelecciona una categoría:", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

            elif data.startswith("cat_list_"):
                category = data.replace("cat_list_", "")
                with Database.get_connection() as conn:
                    prods = conn.execute("SELECT * FROM products WHERE category = ? AND is_active = 1", (category,)).fetchall()
                
                if not prods:
                    kb = [[InlineKeyboardButton("⬅️ Atrás", callback_data="cat_categories"), InlineKeyboardButton("🏠 Inicio", callback_data="main_menu")]]
                    await query.answer()
                    await query.edit_message_text(f"🛍️ **CATÁLOGO: {category}**\n\n❌ No hay productos disponibles en esta categoría actualmente.", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
                    return

                kb = []
                for p in prods:
                    kb.append([InlineKeyboardButton(f"📦 {p['name']} - ${p['price']:.2f}", callback_data=f"prod_view_{p['product_id']}")])
                kb.append([InlineKeyboardButton("⬅️ Atrás", callback_data="cat_categories"), InlineKeyboardButton("🏠 Inicio", callback_data="main_menu")])
                
                await query.answer()
                await query.edit_message_text(f"🛍️ **CATÁLOGO: {category}**\n\nSelecciona un producto para ver detalles:", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

            elif data.startswith("prod_view_"):
                prod_id = int(data.replace("prod_view_", ""))
                with Database.get_connection() as conn:
                    p = conn.execute("SELECT * FROM products WHERE product_id = ?", (prod_id,)).fetchone()
                
                if not p:
                    await query.answer("El producto ya no existe.", show_alert=True)
                    return

                text = (
                    f"📦 **PRODUCTO:** {p['name']}\n\n"
                    f"📝 **Descripción:** {p['description']}\n"
                    f"💵 **Precio:** ${p['price']:.2f}\n"
                    f"📊 **Stock:** {p['stock']}\n"
                    f"🟢 **Estado:** {'Disponible' if p['stock'] > 0 else 'Agotado'}\n"
                    f"💎 **Beneficios:** {p['benefits'] or 'Ninguno'}"
                )
                kb = [
                    [InlineKeyboardButton("🛒 Comprar", callback_data=f"buy_confirm_{prod_id}")],
                    [InlineKeyboardButton("⬅️ Atrás", callback_data=f"cat_list_{p['category']}"), InlineKeyboardButton("🏠 Inicio", callback_data="main_menu")]
                ]
                await query.answer()
                await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

            elif data.startswith("buy_confirm_"):
                prod_id = int(data.replace("buy_confirm_", ""))
                with Database.get_connection() as conn:
                    p = conn.execute("SELECT * FROM products WHERE product_id = ?", (prod_id,)).fetchone()
                    u = conn.execute("SELECT balance FROM users WHERE user_id = ?", (user.id,)).fetchone()

                if not p or p['is_active'] == 0:
                    await query.answer("Producto no disponible.", show_alert=True)
                    return

                if p['stock'] <= 0:
                    await query.answer("Producto agotado.", show_alert=True)
                    return

                balance = u['balance']
                price = p['price']
                missing = price - balance

                if balance < price:
                    text = (
                        f"❌ **SALDO INSUFICIENTE**\n\n"
                        f"📦 **Producto:** {p['name']}\n"
                        f"💵 **Precio:** ${price:.2f}\n"
                        f"💰 **Saldo actual:** ${balance:.2f}\n"
                        f"📉 **Falta:** ${missing:.2f}\n\n"
                        f"Por favor recarga saldo para continuar."
                    )
                    kb = [
                        [InlineKeyboardButton("💳 Recargar Saldo", callback_data="wallet_recharge")],
                        [InlineKeyboardButton("⬅️ Atrás", callback_data=f"prod_view_{prod_id}"), InlineKeyboardButton("🏠 Inicio", callback_data="main_menu")]
                    ]
                    await query.answer()
                    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
                    return

                text = (
                    f"⚠️ **CONFIRMACIÓN DE COMPRA**\n\n"
                    f"📦 **Producto:** {p['name']}\n"
                    f"💵 **Precio:** ${price:.2f}\n"
                    f"📊 **Stock disponible:** {p['stock']}\n"
                    f"💰 **Saldo disponible:** ${balance:.2f}\n"
                    f"💳 **Saldo después de compra:** ${(balance - price):.2f}\n\n"
                    f"¿Deseas confirmar la adquisición?"
                )
                kb = [
                    [InlineKeyboardButton("✅ Confirmar compra", callback_data=f"buy_exec_{prod_id}"), InlineKeyboardButton("❌ Cancelar", callback_data=f"prod_view_{prod_id}")],
                    [InlineKeyboardButton("🏠 Inicio", callback_data="main_menu")]
                ]
                await query.answer()
                await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

            elif data.startswith("buy_exec_"):
                prod_id = int(data.replace("buy_exec_", ""))
                with Database.get_connection() as conn:
                    cursor = conn.cursor()
                    p = cursor.execute("SELECT * FROM products WHERE product_id = ?", (prod_id,)).fetchone()
                    u = cursor.execute("SELECT * FROM users WHERE user_id = ?", (user.id,)).fetchone()

                    if not p or p['stock'] <= 0 or u['balance'] < p['price']:
                        await query.answer("Error en la transacción. Verifique saldo o stock.", show_alert=True)
                        return

                    new_balance = u['balance'] - p['price']
                    new_spent = u['total_spent'] + p['price']
                    new_stock = p['stock'] - 1

                    cursor.execute("UPDATE users SET balance = ?, total_spent = ? WHERE user_id = ?", (new_balance, new_spent, user.id))
                    cursor.execute("UPDATE products SET stock = ? WHERE product_id = ?", (new_stock, prod_id))
                    
                    now = datetime.datetime.now().isoformat()
                    cursor.execute(
                        "INSERT INTO purchases (user_id, product_id, product_name, price, delivery_content, created_at, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (user.id, prod_id, p['name'], p['price'], p['delivery_data'] or "Sin datos adjuntos.", now, "COMPLETADO")
                    )
                    conn.commit()

                success_text = (
                    f"✅ **COMPRA EXITOSA**\n\n"
                    f"📦 **Producto:** {p['name']}\n"
                    f"💵 **Pagado:** ${p['price']:.2f}\n"
                    f"💰 **Saldo restante:** ${new_balance:.2f}\n"
                    f"📅 **Fecha:** {now[:19]}\n\n"
                    f"📦 **DATOS DE ENTREGA:**\n`{p['delivery_data'] or 'Entrega directa coordinada con soporte.'}`"
                )
                Security.log_action(user.id, "COMPRA_PRODUCTO", f"Producto ID {prod_id} comprado por ${p['price']}")
                await query.answer("¡Compra procesada con éxito!", show_alert=True)
                await query.edit_message_text(success_text, reply_markup=Keyboards.back_to_start(), parse_mode="Markdown")

            elif data == "user_purchases":
                with Database.get_connection() as conn:
                    purchases = conn.execute("SELECT * FROM purchases WHERE user_id = ? ORDER BY purchase_id DESC LIMIT 5", (user.id,)).fetchall()
                
                if not purchases:
                    await query.answer()
                    await query.edit_message_text("📦 **HISTORIAL DE COMPRAS**\n\nNo registras compras en este momento.", reply_markup=Keyboards.back_and_home("main_menu"), parse_mode="Markdown")
                    return

                text = "📦 **TUS ÚLTIMAS COMPRAS:**\n\n"
                for pur in purchases:
                    text += f"🧾 **Pedido #{pur['purchase_id']}**\n📦 {pur['product_name']}\n💵 ${pur['price']:.2f} | 📅 {pur['created_at'][:10]}\n\n"
                
                await query.answer()
                await query.edit_message_text(text, reply_markup=Keyboards.back_and_home("main_menu"), parse_mode="Markdown")

            elif data == "wallet_recharge":
                text = (
                    f"💳 **RECARGAR SALDO**\n\n"
                    f"Selecciona el método de pago disponible para enviar tu comprobante:"
                )
                kb = [
                    [InlineKeyboardButton("🇵🇪 Yape / Plin", callback_data="pay_method_yape"), InlineKeyboardButton("💰 Binance USDT", callback_data="pay_method_binance")],
                    [InlineKeyboardButton("⬅️ Atrás", callback_data="main_menu"), InlineKeyboardButton("🏠 Inicio", callback_data="main_menu")]
                ]
                await query.answer()
                await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

            elif data.startswith("pay_method_"):
                method = data.replace("pay_method_", "").upper()
                context.user_data['recharge_method'] = method
                context.user_data['waiting_for_proof'] = True
                
                text = (
                    f"🧾 **MÉTODO SELECCIONADO: {method}**\n\n"
                    f"Por favor realiza el pago correspondiente y **envía la foto de tu comprobante** por este chat para proceder con la verificación administrativa."
                )
                kb = [[InlineKeyboardButton("❌ Cancelar", callback_data="wallet_recharge")]]
                await query.answer()
                await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

                        elif data == "user_coupons":
                await query.answer()
                await query.edit_message_text("🎟️ **SISTEMA DE CUPONES**\n\nActualmente no tienes cupones activos aplicados. Puedes canjear códigos promocionales desde las campañas oficiales.", reply_markup=Keyboards.back_and_home("main_menu"), parse_mode="Markdown")

            elif data == "user_premium":
                with Database.get_connection() as conn:
                    u = conn.execute("SELECT is_premium FROM users WHERE user_id = ?", (user.id,)).fetchone()
                status = "🟢 Activo" if u['is_premium'] else "🔴 Inactivo"
                text = (
                    f"💎 **ESTADO PREMIUM**\n\n"
                    f"Estado actual: {status}\n\n"
                    f"**Beneficios configurados:**\n"
                    f"• Descuentos especiales en catálogo\n"
                    f"• Prioridad de entrega y soporte técnico\n"
                    f"• Acceso a productos exclusivos"
                )
                await query.answer()
                await query.edit_message_text(text, reply_markup=Keyboards.back_and_home("main_menu"), parse_mode="Markdown")

            elif data == "user_referrals":
                with Database.get_connection() as conn:
                    u = conn.execute("SELECT referral_count FROM users WHERE user_id = ?", (user.id,)).fetchone()
                
                bot_username = (await context.bot.get_me()).username
                ref_link = f"https://t.me/{bot_username}?start={user.id}"
                text = (
                    f"🎁 **PROGRAMA DE REFERIDOS**\n\n"
                    f"🔗 **Tu enlace personal:**\n`{ref_link}`\n\n"
                    f"👥 **Invitados totales:** {u['referral_count']}\n"
                    f"🎁 **Recompensas acumuladas:** $0.00"
                )
                await query.answer()
                await query.edit_message_text(text, reply_markup=Keyboards.back_and_home("main_menu"), parse_mode="Markdown")

            elif data == "support_info":
                text = (
                    f"📞 **CENTRO DE SOPORTE OFICIAL**\n\n"
                    f"Si experimentas inconvenientes con tu pago, entrega o activación, comunícate con nuestro equipo autorizado:\n\n"
                    f"👤 Soporte: @TuSoporteLXZ\n"
                    f"📢 Canal: @TuCanalOficial"
                )
                await query.answer()
                await query.edit_message_text(text, reply_markup=Keyboards.back_and_home("main_menu"), parse_mode="Markdown")

            elif data == "admin_panel":
                if not Security.is_admin(user.id):
                    await query.answer("Permisos insuficientes.", show_alert=True)
                    return
                text = "⚙️ **PANEL ADMINISTRATIVO**\n\nSelecciona una herramienta de gestión:"
                kb = [
                    [InlineKeyboardButton("👥 Usuarios", callback_data="adm_users"), InlineKeyboardButton("📦 Productos", callback_data="adm_products")],
                    [InlineKeyboardButton("💳 Pagos Pendientes", callback_data="adm_payments"), InlineKeyboardButton("📊 Estadísticas", callback_data="adm_stats")],
                    [InlineKeyboardButton("⬅️ Atrás", callback_data="main_menu")]
                ]
                await query.answer()
                await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

            elif data == "owner_panel":
                if not Security.is_owner(user.id):
                    await query.answer("Acceso exclusivo del Owner.", show_alert=True)
                    return
                text = "👑 **PANEL OWNER DE MÁXIMO CONTROL**\n\nSelecciona el módulo de administración superior:"
                kb = [
                    [InlineKeyboardButton("📊 Dashboard", callback_data="adm_stats"), InlineKeyboardButton("👥 Administradores", callback_data="own_admins")],
                    [InlineKeyboardButton("📦 Gestión Productos", callback_data="adm_products"), InlineKeyboardButton("💳 Pagos Pendientes", callback_data="adm_payments")],
                    [InlineKeyboardButton("⚙️ Panel Admin", callback_data="admin_panel")],
                    [InlineKeyboardButton("⬅️ Atrás", callback_data="main_menu")]
                ]
                await query.answer()
                await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

            elif data == "adm_payments":
                if not Security.is_admin(user.id):
                    await query.answer("Sin permisos.", show_alert=True)
                    return
                with Database.get_connection() as conn:
                    recharges = conn.execute("SELECT * FROM recharges WHERE status = 'PENDIENTE'").fetchall()
                
                if not recharges:
                    await query.answer()
                    await query.edit_message_text("💳 **SOLICITUDES DE RECARGA**\n\nNo hay solicitudes pendientes de aprobación.", reply_markup=Keyboards.back_and_home("admin_panel"), parse_mode="Markdown")
                    return

                text = f"💳 **SOLICITUDES PENDIENTES ({len(recharges)}):**\nSelecciona una para revisar:"
                kb = []
                for r in recharges:
                    kb.append([InlineKeyboardButton(f"ID: {r['user_id']} - ${r['amount'] or 'N/D'} ({r['method']})", callback_data=f"rev_pay_{r['recharge_id']}")])
                kb.append([InlineKeyboardButton("⬅️ Atrás", callback_data="admin_panel")])
                await query.answer()
                await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

            elif data.startswith("rev_pay_"):
                if not Security.is_admin(user.id):
                    await query.answer("Sin permisos.", show_alert=True)
                    return
                rech_id = int(data.replace("rev_pay_", ""))
                with Database.get_connection() as conn:
                    r = conn.execute("SELECT * FROM recharges WHERE recharge_id = ?", (rech_id,)).fetchone()
                
                if not r or r['status'] != 'PENDIENTE':
                    await query.answer("La solicitud ya fue procesada o no existe.", show_alert=True)
                    return

                text = (
                    f"🧾 **SOLICITUD DE RECARGA #{r['recharge_id']}**\n\n"
                    f"🆔 Usuario ID: `{r['user_id']}`\n"
                    f"💳 Método: {r['method']}\n"
                    f"📅 Fecha: {r['created_at'][:19]}\n"
                    f"📌 Estado: {r['status']}"
                )
                kb = [
                    [InlineKeyboardButton("✅ Aprobar", callback_data=f"apr_pay_{rech_id}"), InlineKeyboardButton("❌ Rechazar", callback_data=f"rej_pay_{rech_id}")],
                    [InlineKeyboardButton("⬅️ Atrás", callback_data="adm_payments")]
                ]
                await query.answer()
                await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

            elif data.startswith("apr_pay_") or data.startswith("rej_pay_"):
                if not Security.is_admin(user.id):
                    await query.answer("Sin permisos.", show_alert=True)
                    return
                
                action, rech_id = data.split("_")[0], int(data.split("_")[2])
                with Database.get_connection() as conn:
                    cursor = conn.cursor()
                    r = cursor.execute("SELECT * FROM recharges WHERE recharge_id = ?", (rech_id,)).fetchone()
                    if not r or r['status'] != 'PENDIENTE':
                        await query.answer("Solicitud no válida.", show_alert=True)
                        return

                    if action == "apr":
                        monto = 10.00 
                        cursor.execute("UPDATE recharges SET status = 'APROBADO' WHERE recharge_id = ?", (rech_id,))
                        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (monto, r['user_id']))
                        conn.commit()
                        
                        try:
                            await context.bot.send_message(
                                chat_id=r['user_id'],
                                text=f"💰 **RECARGA APROBADA**\n\nSe agregaron: +${monto:.2f}\nTu saldo ha sido actualizado con éxito.",
                                parse_mode="Markdown"
                            )
                        except Exception:
                            pass
                        await query.answer("Recarga aprobada y saldo acreditado.", show_alert=True)
                    else:
                        cursor.execute("UPDATE recharges SET status = 'RECHAZADO' WHERE recharge_id = ?", (rech_id,))
                        conn.commit()
                        try:
                            await context.bot.send_message(
                                chat_id=r['user_id'],
                                text=f"🔴 **RECARGA RECHAZADA**\n\nTu comprobante no pudo ser verificado. Contacta a soporte.",
                                parse_mode="Markdown"
                            )
                        except Exception:
                            pass
                        await query.answer("Recarga rechazada.", show_alert=True)
                
                await query.edit_message_text("✅ Operación procesada correctamente.", reply_markup=Keyboards.back_and_home("admin_panel"), parse_mode="Markdown")

            else:
                await query.answer("Función no disponible temporalmente.", show_alert=True)

        except Exception as e:
            logger.error(f"Error procesando callback {data}: {e}")
            try:
                await query.answer("Ocurrió un error interno al procesar la solicitud.", show_alert=True)
            except Exception:
                pass

    @staticmethod
    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if Security.is_banned(user.id):
            return

        if context.user_data.get('waiting_for_proof') and update.message.photo:
            method = context.user_data.get('recharge_method', 'YAPE/PLIN')
            photo_file_id = update.message.photo[-1].file_id

            with Database.get_connection() as conn:
                conn.execute(
                    "INSERT INTO recharges (user_id, amount, method, proof_file_id, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (user.id, 0.0, method, photo_file_id, 'PENDIENTE', datetime.datetime.now().isoformat())
                )
                conn.commit()

            context.user_data['waiting_for_proof'] = False
            Security.log_action(user.id, "ENVIO_COMPROBANTE", f"Método: {method}")

            await update.message.reply_text(
                "✅ **COMPROBANTE ENVIADO EXITOSAMENTE**\n\n"
                "Tu solicitud se encuentra en estado **PENDIENTE** de revisión administrativa. Te notificaremos al ser aprobada.",
                reply_markup=Keyboards.back_to_start(),
                parse_mode="Markdown"
            )

# ==========================================
# 🚀 INICIALIZACIÓN Y ARRANQUE DEL BOT
# ==========================================
def main() -> None:
    Database.initialize(OWNER_ID)

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", BotHandlers.start))
    app.add_handler(CallbackQueryHandler(BotHandlers.handle_callback))
    app.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, BotHandlers.handle_message))

    logger.info("⚡ LXZ STORE BEST iniciado correctamente en modo producción.")
    app.run_polling()

if __name__ == "__main__":
    main()
