from __future__ import annotations

import asyncio
import logging
import math
import secrets
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from inline import (
    admin_home,
    categories,
    confirm,
    main_menu,
    nav,
    payment_methods,
    product_detail,
    product_list,
)
from user import (
    AuditLog,
    BalanceTransaction,
    BalanceTransactionType,
    Coupon,
    CouponRedemption,
    Product,
    Purchase,
    PurchaseStatus,
    TopupRequest,
    TopupStatus,
    User,
    UserRole,
    utcnow,
)

router = Router()
logger = logging.getLogger(__name__)
PAGE_SIZE = max(1, settings.PAGE_SIZE)
CATEGORIES = ["🤖 Android", "🍎 iOS / iPhone", "💻 Windows / PC", "🌐 Otros"]


class ProductSearch(StatesGroup):
    waiting = State()


class TopupFlow(StatesGroup):
    amount = State()
    proof = State()


class CouponFlow(StatesGroup):
    code = State()


class ProductFlow(StatesGroup):
    name = State()
    category = State()
    description = State()
    price = State()
    stock = State()
    delivery = State()


class ProductEdit(StatesGroup):
    value = State()


class UserSearch(StatesGroup):
    waiting = State()


class BalanceFlow(StatesGroup):
    amount = State()


class BroadcastFlow(StatesGroup):
    message = State()


class CouponAdminFlow(StatesGroup):
    code = State()
    discount = State()
    limit = State()
    expiry = State()


class AdminIdFlow(StatesGroup):
    waiting = State()


def money(value: object) -> Decimal:
    try:
        return Decimal(str(value or "0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        return Decimal("0.00")


def m(value: object) -> str:
    return f"{money(value):,.2f} {settings.CURRENCY}"


def name_of(user: User) -> str:
    return " ".join(x for x in [user.first_name, user.last_name] if x) or str(user.telegram_id)


def is_admin(user: User | None) -> bool:
    return bool(user and user.role in (UserRole.ADMIN, UserRole.OWNER))


def is_owner(user: User | None) -> bool:
    return bool(user and user.role == UserRole.OWNER)


def now_text(value: datetime | None = None) -> str:
    return (value or utcnow()).strftime("%Y-%m-%d %H:%M UTC")


def active_premium(user: User) -> bool:
    return bool(user.is_premium and (not user.premium_until or user.premium_until > utcnow()))


async def get_or_create_user(telegram_user, session: AsyncSession, current: User | None = None, start_arg: str | None = None) -> User:
    user = current or (await session.execute(select(User).where(User.telegram_id == telegram_user.id))).scalar_one_or_none()
    if user:
        user.username = telegram_user.username
        user.first_name = telegram_user.first_name or "Usuario"
        user.last_name = telegram_user.last_name
        user.last_activity = utcnow()
        if telegram_user.id == settings.OWNER_ID:
            user.role = UserRole.OWNER
        await session.commit()
        return user
    referred_by = None
    if start_arg and start_arg.startswith("ref_"):
        try:
            candidate = int(start_arg[4:])
            if candidate != telegram_user.id:
                ref = (await session.execute(select(User).where(User.telegram_id == candidate))).scalar_one_or_none()
                if ref:
                    referred_by = candidate
                    ref.referrals_count += 1
        except ValueError:
            pass
    role = UserRole.OWNER if telegram_user.id == settings.OWNER_ID else (UserRole.ADMIN if telegram_user.id in settings.admin_ids else UserRole.USER)
    user = User(telegram_id=telegram_user.id, username=telegram_user.username, first_name=telegram_user.first_name or "Usuario", last_name=telegram_user.last_name, role=role, referred_by=referred_by)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def event_user(event: Message | CallbackQuery, session: AsyncSession, current: User | None = None) -> User | None:
    if not event.from_user:
        return None
    return await get_or_create_user(event.from_user, session, current)


async def edit_or_answer(callback: CallbackQuery, text: str, markup=None) -> None:
    try:
        await callback.message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc).lower():
            await callback.message.answer(text, reply_markup=markup)
    await callback.answer()


async def log_event(session: AsyncSession, actor: int, action: str, target: str | None, result: str) -> None:
    session.add(AuditLog(actor_telegram_id=actor, action=action, target=target, result=result))


async def notify_staff(bot: Bot, text: str, markup=None) -> None:
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(admin_id, text, reply_markup=markup)
        except (TelegramForbiddenError, TelegramBadRequest):
            continue


async def show_home(target: Message | CallbackQuery, user: User) -> None:
    text = f"⚡ <b>{settings.STORE_NAME}</b>\n\nTienda digital rápida, segura y profesional.\n\nSelecciona una opción para continuar:"
    markup = main_menu(user.role, settings.OFFICIAL_CHANNEL_URL)
    if isinstance(target, CallbackQuery):
        await edit_or_answer(target, text, markup)
    else:
        await target.answer(text, reply_markup=markup)


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, current_user: User | None = None, state: FSMContext | None = None):
    if state:
        await state.clear()
    args = (message.text or "").split(maxsplit=1)
    user = await get_or_create_user(message.from_user, session, current_user, args[1] if len(args) > 1 else None)
    await show_home(message, user)


@router.message(Command("cancelar"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Operación cancelada.")


@router.callback_query(F.data == "menu:home")
async def menu_home(callback: CallbackQuery, session: AsyncSession, current_user: User | None = None, state: FSMContext | None = None):
    if state:
        await state.clear()
    user = await event_user(callback, session, current_user)
    if user:
        await show_home(callback, user)


@router.callback_query(F.data == "menu:catalog")
async def menu_catalog(callback: CallbackQuery, session: AsyncSession):
    db_categories = (await session.execute(select(Product.category).where(Product.is_active.is_(True)).distinct())).scalars().all()
    values = list(dict.fromkeys(CATEGORIES + [x for x in db_categories if x not in CATEGORIES]))
    await edit_or_answer(callback, "🛍️ <b>CATÁLOGO</b>\n\nSelecciona una categoría:", categories(values))


async def render_products(callback: CallbackQuery, session: AsyncSession, category: str, page: int):
    query = select(Product).where(Product.is_active.is_(True), Product.category == category).order_by(Product.id.desc())
    all_items = (await session.execute(query)).scalars().all()
    pages = max(1, math.ceil(len(all_items) / PAGE_SIZE))
    page = max(0, min(page, pages - 1))
    items = all_items[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
    if not items:
        text = f"📦 <b>{category}</b>\n\nNo hay productos disponibles en esta categoría."
    else:
        lines = [f"📦 <b>{category}</b> · Página {page + 1}/{pages}", ""]
        for p in items:
            stock = "Agotado" if p.stock <= 0 else str(p.stock)
            lines.append(f"• <b>{p.name}</b> — {m(p.price)} · Stock: {stock}")
        text = "\n".join(lines)
    await edit_or_answer(callback, text, product_list(items, page, pages, category))


@router.callback_query(F.data.startswith("cat:"))
async def catalog_category(callback: CallbackQuery, session: AsyncSession):
    await render_products(callback, session, callback.data[4:], 0)


@router.callback_query(F.data.startswith("products:"))
async def catalog_page(callback: CallbackQuery, session: AsyncSession):
    _, category, page = callback.data.split(":", 2)
    await render_products(callback, session, category, int(page))


@router.callback_query(F.data.regexp(r"^product:\d+$"))
async def product_info(callback: CallbackQuery, session: AsyncSession):
    product = (await session.execute(select(Product).where(Product.id == int(callback.data.split(":")[1]), Product.is_active.is_(True)))).scalar_one_or_none()
    if not product:
        await callback.answer("Producto no disponible.", show_alert=True)
        return
    stock = "Agotado" if product.stock <= 0 else str(product.stock)
    text = f"📦 <b>{product.name}</b>\n\n📝 {product.description or 'Sin descripción.'}\n💵 Precio: <b>{m(product.price)}</b>\n📊 Stock: {stock}\n🟢 Estado: {'Disponible' if product.stock > 0 else 'Agotado'}"
    await edit_or_answer(callback, text, product_detail(product.id, f"cat:{product.category}"))


@router.callback_query(F.data.startswith("buy:"))
async def buy_preview(callback: CallbackQuery, session: AsyncSession, current_user: User | None = None, state: FSMContext | None = None):
    user = await event_user(callback, session, current_user)
    product = (await session.execute(select(Product).where(Product.id == int(callback.data.split(":")[1]), Product.is_active.is_(True)))).scalar_one_or_none()
    if not user or not product or product.stock <= 0:
        await callback.answer("Producto agotado o no disponible.", show_alert=True)
        return
    data = await state.get_data() if state else {}
    total = money(product.price)
    coupon_line = ""
    coupon_code = data.get("coupon_code")
    if coupon_code:
        coupon = (await session.execute(select(Coupon).where(Coupon.code == coupon_code, Coupon.is_active.is_(True)))).scalar_one_or_none()
        discount = coupon_discount(coupon, total, user) if coupon else Decimal("0.00")
        if discount:
            total -= discount
            coupon_line = f"\n🎟️ Descuento ({coupon_code}): -{m(discount)}"
    text = f"🛒 <b>CONFIRMAR COMPRA</b>\n\n📦 Producto: {product.name}\n💵 Precio: {m(product.price)}{coupon_line}\n💳 Total: <b>{m(total)}</b>\n📊 Stock: {product.stock}\n💰 Saldo disponible: {m(user.balance)}\n💰 Saldo después: {m(money(user.balance) - total)}"
    if money(user.balance) < total:
        await edit_or_answer(callback, text + "\n\n❌ Saldo insuficiente.", confirm("menu:balance", f"product:{product.id}"))
    else:
        await edit_or_answer(callback, text, confirm(f"buyconfirm:{product.id}", f"product:{product.id}"))


def coupon_discount(coupon: Coupon | None, price: Decimal, user: User) -> Decimal:
    if not coupon or not coupon.is_active or (coupon.expires_at and coupon.expires_at <= utcnow()):
        return Decimal("0.00")
    if coupon.usage_limit is not None and coupon.used_count >= coupon.usage_limit:
        return Decimal("0.00")
    if coupon.percent_off:
        discount = price * money(coupon.percent_off) / Decimal(100)
    else:
        discount = money(coupon.fixed_off)
    return min(price, discount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@router.callback_query(F.data.startswith("buyconfirm:"))
async def buy_confirm(callback: CallbackQuery, bot: Bot, session: AsyncSession, current_user: User | None = None, state: FSMContext | None = None):
    await callback.answer("Procesando compra...")
    user = await event_user(callback, session, current_user)
    if not user:
        return
    product_id = int(callback.data.split(":")[1])
    try:
        user = (await session.execute(select(User).where(User.telegram_id == user.telegram_id).with_for_update())).scalar_one()
        product = (await session.execute(select(Product).where(Product.id == product_id, Product.is_active.is_(True)).with_for_update())).scalar_one_or_none()
        if not product or product.stock <= 0:
            await callback.message.edit_text("❌ El producto ya no está disponible.", reply_markup=nav())
            return
        data = await state.get_data() if state else {}
        coupon_code = data.get("coupon_code")
        coupon = None
        discount = Decimal("0.00")
        if coupon_code:
            coupon = (await session.execute(select(Coupon).where(Coupon.code == coupon_code).with_for_update())).scalar_one_or_none()
            if coupon and (await session.execute(select(CouponRedemption).where(CouponRedemption.coupon_id == coupon.id, CouponRedemption.user_id == user.id))).scalar_one_or_none():
                coupon = None
            discount = coupon_discount(coupon, money(product.price), user)
        total = money(product.price) - discount
        if user.balance < total:
            await callback.message.edit_text(f"❌ <b>SALDO INSUFICIENTE</b>\n\nSaldo actual: {m(user.balance)}\nPrecio: {m(total)}\nFalta: {m(total - money(user.balance))}", reply_markup=nav())
            return
        order_id = f"LXZ-{secrets.token_hex(5).upper()}"
        user.balance = money(user.balance) - total
        user.total_spent = money(user.total_spent) + total
        user.purchases_count += 1
        product.stock -= 1
        product.sales_count += 1
        purchase = Purchase(order_id=order_id, user_id=user.id, product_id=product.id, product_name=product.name, price=total, discount=discount, coupon_code=coupon.code if coupon else None, delivery_data=product.delivery_data, delivered_at=utcnow() if product.delivery_data else None)
        session.add(purchase)
        await session.flush()
        session.add(BalanceTransaction(user_id=user.id, kind=BalanceTransactionType.PURCHASE, amount=-total, balance_after=user.balance, reference=order_id, note=product.name))
        if coupon:
            coupon.used_count += 1
            session.add(CouponRedemption(coupon_id=coupon.id, user_id=user.id, purchase_id=purchase.id))
        await log_event(session, user.telegram_id, "purchase", order_id, "approved")
        await session.commit()
        if state:
            await state.clear()
        delivery = f"\n\n📦 <b>DATOS DE ENTREGA:</b>\n<code>{product.delivery_data}</code>" if product.delivery_data else "\n\n📦 Entrega: el administrador procesará tu pedido."
        text = f"✅ <b>COMPRA EXITOSA</b>\n\n📦 Producto: {product.name}\n💵 Pagado: {m(total)}\n💰 Saldo restante: {m(user.balance)}\n🧾 Pedido: <code>{order_id}</code>\n📅 Fecha: {now_text()}{delivery}"
        await callback.message.edit_text(text, reply_markup=nav())
        await notify_staff(bot, f"🛒 <b>NUEVA VENTA</b>\n👤 {name_of(user)} ({user.telegram_id})\n📦 {product.name}\n💵 {m(total)}\n🧾 {order_id}")
    except Exception:
        await session.rollback()
        logger.exception("purchase processing failed")
        await callback.message.edit_text("❌ No pudimos procesar la compra. Inténtalo nuevamente.", reply_markup=nav())


@router.callback_query(F.data == "menu:profile")
async def menu_profile(callback: CallbackQuery, session: AsyncSession, current_user: User | None = None):
    user = await event_user(callback, session, current_user)
    if not user:
        return
    text = f"👤 <b>MI PERFIL</b>\n\n📌 Nombre: {name_of(user)}\n🔖 Username: @{user.username or '—'}\n🆔 ID: <code>{user.telegram_id}</code>\n💰 Saldo: <b>{m(user.balance)}</b>\n💎 Premium: {'Activo' if active_premium(user) else 'Inactivo'}\n📦 Compras: {user.purchases_count}\n💵 Total gastado: {m(user.total_spent)}\n🎁 Referidos: {user.referrals_count}\n📅 Registro: {now_text(user.created_at)}\n🚫 Estado: {'Restringido' if user.is_banned else 'Activo'}"
    await edit_or_answer(callback, text, nav())


async def render_purchases(callback: CallbackQuery, session: AsyncSession, user: User, page: int):
    items = (await session.execute(select(Purchase).where(Purchase.user_id == user.id).order_by(desc(Purchase.created_at)))).scalars().all()
    pages = max(1, math.ceil(len(items) / PAGE_SIZE))
    page = max(0, min(page, pages - 1))
    current = items[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
    text = f"📦 <b>MIS COMPRAS</b> · Página {page + 1}/{pages}\n\n" + ("\n".join(f"🧾 <code>{p.order_id}</code> · {p.product_name} · {m(p.price)}" for p in current) if current else "Aún no tienes compras.")
    rows = []
    for p in current:
        rows.append([(f"🧾 {p.order_id} · {p.product_name[:24]}", f"purchase:{p.id}", None)])
    pager = []
    if page > 0: pager.append(("◀️ Anterior", f"purchases:{page-1}", None))
    if page + 1 < pages: pager.append(("▶️ Siguiente", f"purchases:{page+1}", None))
    if pager: rows.append(pager)
    rows.append([("🏠 Inicio", "menu:home", None)])
    from inline import kb
    await edit_or_answer(callback, text, kb(rows))


@router.callback_query(F.data == "menu:purchases")
async def menu_purchases(callback: CallbackQuery, session: AsyncSession, current_user: User | None = None):
    user = await event_user(callback, session, current_user)
    if user: await render_purchases(callback, session, user, 0)


@router.callback_query(F.data.startswith("purchases:"))
async def purchases_page(callback: CallbackQuery, session: AsyncSession, current_user: User | None = None):
    user = await event_user(callback, session, current_user)
    if user: await render_purchases(callback, session, user, int(callback.data.split(":")[1]))


@router.callback_query(F.data.startswith("purchase:"))
async def purchase_detail_view(callback: CallbackQuery, session: AsyncSession, current_user: User | None = None):
    user = await event_user(callback, session, current_user)
    purchase = (await session.execute(select(Purchase).where(Purchase.id == int(callback.data.split(":")[1]), Purchase.user_id == user.id if user else False))).scalar_one_or_none()
    if not purchase:
        await callback.answer("Compra no encontrada.", show_alert=True); return
    delivery = f"\n\n📦 Datos: <code>{purchase.delivery_data}</code>" if purchase.delivery_data else ""
    await edit_or_answer(callback, f"🧾 <b>DETALLE DE COMPRA</b>\n\nPedido: <code>{purchase.order_id}</code>\nProducto: {purchase.product_name}\nPagado: {m(purchase.price)}\nEstado: {purchase.status.value}\nFecha: {now_text(purchase.created_at)}{delivery}", nav("", "menu:purchases"))


@router.callback_query(F.data == "menu:balance")
async def menu_balance(callback: CallbackQuery, session: AsyncSession, current_user: User | None = None):
    user = await event_user(callback, session, current_user)
    if user: await edit_or_answer(callback, f"💳 <b>RECARGAR SALDO</b>\n\nSaldo actual: <b>{m(user.balance)}</b>\n\nSelecciona un método:", payment_methods(bool(settings.YAPE_NUMBER or settings.PLIN_NUMBER), settings.BINANCE_USDT_ENABLED and bool(settings.BINANCE_USDT_ADDRESS)))


@router.callback_query(F.data.startswith("topup:method:"))
async def topup_method(callback: CallbackQuery, state: FSMContext):
    method = callback.data.rsplit(":", 1)[1]
    if method == "binance" and not settings.BINANCE_USDT_ENABLED:
        await callback.answer("Binance USDT no está habilitado.", show_alert=True); return
    if method == "yape" and not (settings.YAPE_NUMBER or settings.PLIN_NUMBER):
        await callback.answer("Yape / Plin aún no está configurado.", show_alert=True); return
    await state.set_state(TopupFlow.amount)
    await state.update_data(method=method)
    details = (f"Yape: <code>{settings.YAPE_NUMBER or 'no configurado'}</code>\nPlin: <code>{settings.PLIN_NUMBER or 'no configurado'}</code>" if method == "yape" else f"Red: <b>{settings.BINANCE_USDT_NETWORK}</b>\nDirección: <code>{settings.BINANCE_USDT_ADDRESS}</code>")
    await edit_or_answer(callback, f"💳 <b>RECARGA · {method.upper()}</b>\n\n{details}\n\nEscribe el monto a recargar. Usa /cancelar para salir.")


@router.message(TopupFlow.amount, F.text)
async def topup_amount(message: Message, state: FSMContext):
    amount = money(message.text)
    if amount <= 0:
        await message.answer("❌ Escribe un monto mayor que cero."); return
    await state.update_data(amount=str(amount))
    await state.set_state(TopupFlow.proof)
    await message.answer("📸 Ahora envía una fotografía del comprobante. También puedes enviar un documento de imagen.")


@router.message(TopupFlow.proof, F.photo)
async def topup_photo(message: Message, state: FSMContext, session: AsyncSession, bot: Bot, current_user: User | None = None):
    await create_topup(message, state, session, bot, message.photo[-1].file_id, "photo", current_user)


@router.message(TopupFlow.proof, F.document)
async def topup_document(message: Message, state: FSMContext, session: AsyncSession, bot: Bot, current_user: User | None = None):
    await create_topup(message, state, session, bot, message.document.file_id, "document", current_user)


async def create_topup(message: Message, state: FSMContext, session: AsyncSession, bot: Bot, file_id: str, proof_type: str, current_user: User | None):
    user = await event_user(message, session, current_user)
    data = await state.get_data()
    request = TopupRequest(user_id=user.id, method=data["method"], amount=money(data["amount"]), proof_file_id=file_id, proof_type=proof_type)
    session.add(request); await session.commit(); await session.refresh(request)
    await log_event(session, user.telegram_id, "topup_request", str(request.id), "pending"); await session.commit()
    await state.clear()
    await message.answer(f"🟡 <b>RECARGA PENDIENTE</b>\n\nMonto: {m(request.amount)}\nMétodo: {request.method}\nSolicitud: <code>#{request.id}</code>\n\nUn administrador revisará tu comprobante.", reply_markup=nav())
    from inline import kb
    markup = kb([[ ("✅ Aprobar", f"topup:approve:{request.id}", None), ("❌ Rechazar", f"topup:reject:{request.id}", None) ]])
    caption = f"🧾 <b>SOLICITUD DE RECARGA #{request.id}</b>\n👤 Usuario: {name_of(user)}\n🆔 ID: <code>{user.telegram_id}</code>\n💵 Monto: {m(request.amount)}\n💳 Método: {request.method}\n📅 Fecha: {now_text()}\n📌 Estado: Pendiente"
    for admin_id in settings.admin_ids:
        try:
            if proof_type == "photo": await bot.send_photo(admin_id, file_id, caption=caption, reply_markup=markup)
            else: await bot.send_document(admin_id, file_id, caption=caption, reply_markup=markup)
        except (TelegramForbiddenError, TelegramBadRequest): pass


@router.callback_query(F.data.regexp(r"^topup:(approve|reject):\d+$"))
async def review_topup(callback: CallbackQuery, bot: Bot, session: AsyncSession, current_user: User | None = None):
    reviewer = await event_user(callback, session, current_user)
    if not is_admin(reviewer): await callback.answer("Permisos insuficientes.", show_alert=True); return
    _, action, raw_id = callback.data.split(":")
    request = (await session.execute(select(TopupRequest).where(TopupRequest.id == int(raw_id)).with_for_update())).scalar_one_or_none()
    if not request or request.status != TopupStatus.PENDING:
        await callback.answer("Esta solicitud ya fue procesada.", show_alert=True); return
    user = (await session.execute(select(User).where(User.id == request.user_id).with_for_update())).scalar_one_or_none()
    request.reviewed_by = reviewer.telegram_id; request.reviewed_at = utcnow()
    if action == "approve":
        request.status = TopupStatus.APPROVED; user.balance = money(user.balance) + money(request.amount)
        session.add(BalanceTransaction(user_id=user.id, kind=BalanceTransactionType.TOPUP, amount=request.amount, balance_after=user.balance, reference=str(request.id), note=request.method))
        result = "approved"; user_msg = f"💰 <b>RECARGA APROBADA</b>\n\nSe agregaron: +{m(request.amount)}\n💰 Nuevo saldo: {m(user.balance)}"
    else:
        request.status = TopupStatus.REJECTED; result = "rejected"; user_msg = "🔴 <b>RECARGA RECHAZADA</b>\n\nTu comprobante no fue aprobado. Contacta a soporte si necesitas ayuda."
    await log_event(session, reviewer.telegram_id, f"topup_{action}", str(request.id), result); await session.commit()
    await bot.send_message(user.telegram_id, user_msg, reply_markup=nav())
    await edit_or_answer(callback, f"✅ Solicitud #{request.id} procesada como <b>{result}</b>.")


@router.callback_query(F.data == "menu:coupons")
async def menu_coupons(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    coupons = (await session.execute(select(Coupon).where(Coupon.is_active.is_(True)).order_by(Coupon.id.desc()).limit(10))).scalars().all()
    lines = ["🎟️ <b>CUPONES DISPONIBLES</b>", ""]
    for c in coupons:
        value = f"{c.percent_off}%" if c.percent_off is not None else m(c.fixed_off)
        expires = now_text(c.expires_at) if c.expires_at else "Sin expiración"
        lines.append(f"🎟️ <code>{c.code}</code> · {value} · Usos: {c.used_count}/{c.usage_limit or '∞'} · {expires}")
    if not coupons: lines.append("No hay cupones activos en este momento.")
    await state.set_state(CouponFlow.code)
    await edit_or_answer(callback, "\n".join(lines) + "\n\nEscribe un código para aplicarlo a tu próxima compra, o /cancelar.")


@router.message(CouponFlow.code, F.text)
async def coupon_apply(message: Message, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    user = await event_user(message, session, current_user)
    code = message.text.strip().upper()
    coupon = (await session.execute(select(Coupon).where(Coupon.code == code, Coupon.is_active.is_(True)))).scalar_one_or_none()
    if not coupon or coupon_discount(coupon, Decimal("100.00"), user) <= 0:
        await message.answer("❌ Cupón inválido, expirado, agotado o inactivo."); return
    redeemed = (await session.execute(select(CouponRedemption).where(CouponRedemption.coupon_id == coupon.id, CouponRedemption.user_id == user.id))).scalar_one_or_none()
    if redeemed:
        await message.answer("❌ Ya utilizaste este cupón."); return
    await state.update_data(coupon_code=code)
    await message.answer(f"✅ Cupón <code>{code}</code> aplicado. Se calculará el ahorro al confirmar la compra.", reply_markup=nav())


@router.callback_query(F.data == "menu:premium")
async def menu_premium(callback: CallbackQuery, session: AsyncSession, current_user: User | None = None):
    user = await event_user(callback, session, current_user)
    status = "🟢 Activo" if active_premium(user) else "🔴 Inactivo"
    until = f"\nVálido hasta: {now_text(user.premium_until)}" if user.premium_until else ""
    await edit_or_answer(callback, f"💎 <b>PREMIUM</b>\n\nEstado: {status}{until}\n\nLos beneficios se mostrarán aquí únicamente cuando estén habilitados por la administración.", nav())


@router.callback_query(F.data == "menu:referrals")
async def menu_referrals(callback: CallbackQuery, bot: Bot, session: AsyncSession, current_user: User | None = None):
    user = await event_user(callback, session, current_user)
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start=ref_{user.telegram_id}"
    await edit_or_answer(callback, f"🎁 <b>PROGRAMA DE REFERIDOS</b>\n\n🔗 Tu enlace:\n<code>{link}</code>\n\n👥 Invitados: {user.referrals_count}\n🎁 Recompensas: configuradas por administración\n💰 Ganado: {m(user.referral_earnings)}", nav())


@router.callback_query(F.data == "menu:support")
async def menu_support(callback: CallbackQuery):
    contact = f"@{settings.SUPPORT_USERNAME.lstrip('@')}" if settings.SUPPORT_USERNAME else "el administrador de la tienda"
    await edit_or_answer(callback, f"📞 <b>SOPORTE</b>\n\nPara recibir ayuda, contacta a {contact}.", nav())


async def check_admin(callback: CallbackQuery, session: AsyncSession, current_user: User | None) -> User | None:
    user = await event_user(callback, session, current_user)
    if not is_admin(user): await callback.answer("Permisos insuficientes.", show_alert=True); return None
    return user


@router.callback_query(F.data == "admin:home")
async def admin_menu(callback: CallbackQuery, session: AsyncSession, current_user: User | None = None):
    user = await check_admin(callback, session, current_user)
    if user: await edit_or_answer(callback, "⚙️ <b>PANEL ADMIN</b>\n\nSelecciona una función:", admin_home(user.role == UserRole.OWNER))


@router.callback_query(F.data == "owner:home")
async def owner_menu(callback: CallbackQuery, session: AsyncSession, current_user: User | None = None):
    user = await check_admin(callback, session, current_user)
    if user and is_owner(user): await edit_or_answer(callback, "👑 <b>PANEL OWNER</b>\n\nControl total de la tienda:", admin_home(True))


@router.callback_query(F.data == "admin:stats")
async def admin_stats(callback: CallbackQuery, session: AsyncSession, current_user: User | None = None):
    if not await check_admin(callback, session, current_user): return
    users = await session.scalar(select(func.count(User.id))) or 0
    active = await session.scalar(select(func.count(User.id)).where(User.is_banned.is_(False))) or 0
    premium = await session.scalar(select(func.count(User.id)).where(User.is_premium.is_(True))) or 0
    banned = await session.scalar(select(func.count(User.id)).where(User.is_banned.is_(True))) or 0
    products = await session.scalar(select(func.count(Product.id)).where(Product.is_active.is_(True))) or 0
    stock = await session.scalar(select(func.coalesce(func.sum(Product.stock), 0)).where(Product.is_active.is_(True))) or 0
    sales = await session.scalar(select(func.count(Purchase.id)).where(Purchase.status == PurchaseStatus.PAID)) or 0
    revenue = await session.scalar(select(func.coalesce(func.sum(Purchase.price), 0)).where(Purchase.status == PurchaseStatus.PAID)) or 0
    pending = await session.scalar(select(func.count(TopupRequest.id)).where(TopupRequest.status == TopupStatus.PENDING)) or 0
    top = (await session.execute(select(Product.name, Product.sales_count).where(Product.is_active.is_(True)).order_by(desc(Product.sales_count)).limit(3))).all()
    ranking = "\n".join(f"{i}. {name} — {count} ventas" for i, (name, count) in enumerate(top, 1)) or "Sin ventas todavía."
    text = f"📊 <b>DASHBOARD</b>\n\n👥 Usuarios: {users}\n🟢 Activos: {active}\n💎 Premium: {premium}\n🚫 Baneados: {banned}\n📦 Productos: {products}\n📊 Stock: {stock}\n🛒 Ventas: {sales}\n💰 Ingresos: {m(revenue)}\n💳 Pagos pendientes: {pending}\n\n🔥 <b>PRODUCTOS MÁS VENDIDOS</b>\n{ranking}"
    await edit_or_answer(callback, text, nav(True, "admin:home"))


@router.callback_query(F.data == "admin:users")
async def admin_users(callback: CallbackQuery, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    if not await check_admin(callback, session, current_user): return
    await state.set_state(UserSearch.waiting)
    await edit_or_answer(callback, "👥 <b>USUARIOS</b>\n\nEscribe ID, username o nombre para buscar. /cancelar para salir.")


@router.message(UserSearch.waiting, F.text)
async def admin_user_search(message: Message, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    actor = await event_user(message, session, current_user)
    if not is_admin(actor): await state.clear(); return
    query = message.text.strip().lstrip("@")
    filters = [User.username.ilike(f"%{query}%"), User.first_name.ilike(f"%{query}%"), User.last_name.ilike(f"%{query}%")]
    try: filters.append(User.telegram_id == int(query))
    except ValueError: pass
    users = (await session.execute(select(User).where(or_(*filters)).limit(10))).scalars().all()
    from inline import kb
    rows = [[(f"{name_of(u)} · {u.telegram_id}", f"admin:user:{u.telegram_id}", None)] for u in users]
    rows.append([("⚙️ Panel Admin", "admin:home", None)])
    await message.answer("🔎 Resultados:\n\n" + ("\n".join(f"• {name_of(u)} · {u.telegram_id}" for u in users) if users else "No encontramos usuarios."), reply_markup=kb(rows))
    await state.clear()


@router.callback_query(F.data.startswith("admin:user:"))
async def admin_user_detail(callback: CallbackQuery, session: AsyncSession, current_user: User | None = None):
    actor = await check_admin(callback, session, current_user)
    if not actor: return
    target = (await session.execute(select(User).where(User.telegram_id == int(callback.data.split(":")[2])))).scalar_one_or_none()
    if not target: await callback.answer("Usuario no encontrado.", show_alert=True); return
    from inline import kb
    rows = [[("💰 Dar créditos", f"admin:balance:add:{target.telegram_id}", None), ("➖ Quitar créditos", f"admin:balance:sub:{target.telegram_id}", None)], [("💎 Activar Premium", f"admin:premium:on:{target.telegram_id}", None), ("❌ Quitar Premium", f"admin:premium:off:{target.telegram_id}", None)]]
    rows.append([("✅ Desbanear" if target.is_banned else "🚫 Banear", f"admin:ban:{'off' if target.is_banned else 'on'}:{target.telegram_id}", None), ("⚙️ Panel Admin", "admin:home", None)])
    await edit_or_answer(callback, f"👤 <b>USUARIO</b>\n\nNombre: {name_of(target)}\nUsername: @{target.username or '—'}\nID: <code>{target.telegram_id}</code>\nSaldo: {m(target.balance)}\nPremium: {active_premium(target)}\nCompras: {target.purchases_count}\nEstado: {'Baneado' if target.is_banned else 'Activo'}", kb(rows))


@router.callback_query(F.data.startswith("admin:balance:"))
async def admin_balance_prompt(callback: CallbackQuery, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    if not await check_admin(callback, session, current_user): return
    _, _, kind, target = callback.data.split(":")
    await state.set_state(BalanceFlow.amount); await state.update_data(kind=kind, target=int(target))
    await edit_or_answer(callback, f"💰 Escribe la cantidad a {'agregar' if kind == 'add' else 'quitar'} para <code>{target}</code>. Debe ser mayor que cero.")


@router.message(BalanceFlow.amount, F.text)
async def admin_balance_amount(message: Message, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    actor = await event_user(message, session, current_user)
    if not is_admin(actor): await state.clear(); return
    amount = money(message.text)
    if amount <= 0: await message.answer("❌ Cantidad inválida."); return
    data = await state.get_data(); target = (await session.execute(select(User).where(User.telegram_id == data["target"]))).scalar_one_or_none()
    if not target: await message.answer("❌ Usuario inexistente."); await state.clear(); return
    sign = 1 if data["kind"] == "add" else -1
    if sign < 0 and money(target.balance) < amount: await message.answer("❌ El saldo no puede quedar negativo."); return
    await state.update_data(amount=str(amount))
    from inline import kb
    await message.answer(f"⚠️ <b>CONFIRMACIÓN</b>\n\n👤 Usuario: {name_of(target)}\n💰 Saldo actual: {m(target.balance)}\n{'➕' if sign > 0 else '➖'} Cantidad: {m(amount)}\n💰 Nuevo saldo: {m(money(target.balance) + sign * amount)}", reply_markup=kb([[ ("✅ Confirmar", "admin:balance:confirm", None), ("❌ Cancelar", "admin:home", None) ]]))


@router.callback_query(F.data == "admin:balance:confirm")
async def admin_balance_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot, session: AsyncSession, current_user: User | None = None):
    actor = await check_admin(callback, session, current_user)
    if not actor: return
    data = await state.get_data(); amount = money(data.get("amount")); sign = 1 if data.get("kind") == "add" else -1
    target = (await session.execute(select(User).where(User.telegram_id == data.get("target")).with_for_update())).scalar_one_or_none()
    if not target or amount <= 0 or (sign < 0 and money(target.balance) < amount): await callback.answer("Operación inválida.", show_alert=True); return
    target.balance = money(target.balance) + sign * amount
    session.add(BalanceTransaction(user_id=target.id, kind=BalanceTransactionType.CREDIT if sign > 0 else BalanceTransactionType.DEBIT, amount=sign * amount, balance_after=target.balance, reference=str(actor.telegram_id)))
    await log_event(session, actor.telegram_id, "balance_change", str(target.telegram_id), f"{sign * amount}"); await session.commit(); await state.clear()
    await bot.send_message(target.telegram_id, f"💰 <b>{'CRÉDITOS AGREGADOS' if sign > 0 else 'CRÉDITOS DESCONTADOS'}</b>\n\nMovimiento: {'+' if sign > 0 else '-'}{m(amount)}\nNuevo saldo: {m(target.balance)}")
    await edit_or_answer(callback, "✅ Operación completada.", nav(True, "admin:home"))


@router.callback_query(F.data.startswith("admin:premium:"))
async def admin_premium(callback: CallbackQuery, bot: Bot, session: AsyncSession, current_user: User | None = None):
    actor = await check_admin(callback, session, current_user)
    if not actor: return
    _, _, action, raw = callback.data.split(":")
    target = (await session.execute(select(User).where(User.telegram_id == int(raw)).with_for_update())).scalar_one_or_none()
    if not target: await callback.answer("Usuario no encontrado.", show_alert=True); return
    target.is_premium = action == "on"; target.premium_until = None
    await log_event(session, actor.telegram_id, "premium_change", raw, action); await session.commit()
    await bot.send_message(target.telegram_id, f"💎 Premium {'activado' if action == 'on' else 'desactivado'}.")
    await edit_or_answer(callback, "✅ Estado Premium actualizado.", nav(True, "admin:home"))


@router.callback_query(F.data.startswith("admin:ban:"))
async def admin_ban_confirm(callback: CallbackQuery, session: AsyncSession, current_user: User | None = None):
    actor = await check_admin(callback, session, current_user)
    if not actor: return
    _, _, action, raw = callback.data.split(":")
    from inline import kb
    await edit_or_answer(callback, f"⚠️ ¿Confirmar {'baneo' if action == 'on' else 'desbaneo'} del usuario <code>{raw}</code>?", kb([[ ("✅ Confirmar", f"admin:banconfirm:{action}:{raw}", None), ("❌ Cancelar", "admin:home", None) ]]))


@router.callback_query(F.data.startswith("admin:banconfirm:"))
async def admin_ban_apply(callback: CallbackQuery, bot: Bot, session: AsyncSession, current_user: User | None = None):
    actor = await check_admin(callback, session, current_user)
    if not actor: return
    _, _, action, raw = callback.data.split(":")
    target = (await session.execute(select(User).where(User.telegram_id == int(raw)).with_for_update())).scalar_one_or_none()
    if not target: await callback.answer("Usuario no encontrado.", show_alert=True); return
    target.is_banned = action == "on"; target.ban_reason = "Restricción administrativa" if target.is_banned else None
    await log_event(session, actor.telegram_id, "ban_change", raw, action); await session.commit()
    await bot.send_message(target.telegram_id, "🚫 Tu acceso a LXZ STORE BEST ha sido restringido." if target.is_banned else "✅ Tu acceso a LXZ STORE BEST ha sido restablecido.")
    await edit_or_answer(callback, "✅ Estado de seguridad actualizado.", nav(True, "admin:home"))


@router.callback_query(F.data == "admin:products")
async def admin_products(callback: CallbackQuery, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    if not await check_admin(callback, session, current_user): return
    products = (await session.execute(select(Product).order_by(Product.id.desc()).limit(20))).scalars().all()
    from inline import kb
    rows = [[(f"{'🟢' if p.is_active else '🔴'} {p.name[:28]} · {m(p.price)} · stock {p.stock}", f"admin:product:{p.id}", None)] for p in products]
    rows.append([("➕ Crear producto", "admin:product:new", None), ("⬅️ Panel", "admin:home", None)])
    await edit_or_answer(callback, "📦 <b>ADMINISTRACIÓN DE PRODUCTOS</b>\n\nSelecciona un producto:", kb(rows))


@router.callback_query(F.data == "admin:product:new")
async def product_new(callback: CallbackQuery, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    if not await check_admin(callback, session, current_user): return
    await state.clear(); await state.set_state(ProductFlow.name); await edit_or_answer(callback, "➕ <b>NUEVO PRODUCTO</b>\n\nEscribe el nombre:")


@router.message(ProductFlow.name, F.text)
async def product_name(message: Message, state: FSMContext): await state.update_data(name=message.text.strip()); await state.set_state(ProductFlow.category); await message.answer("Categoría (Android, iOS / iPhone, Windows / PC u Otros):")
@router.message(ProductFlow.category, F.text)
async def product_category(message: Message, state: FSMContext): await state.update_data(category=message.text.strip() or "Otros"); await state.set_state(ProductFlow.description); await message.answer("Descripción del producto:")
@router.message(ProductFlow.description, F.text)
async def product_description(message: Message, state: FSMContext): await state.update_data(description=message.text.strip()); await state.set_state(ProductFlow.price); await message.answer("Precio numérico:")
@router.message(ProductFlow.price, F.text)
async def product_price(message: Message, state: FSMContext):
    price = money(message.text)
    if price <= 0: await message.answer("❌ Precio inválido."); return
    await state.update_data(price=str(price)); await state.set_state(ProductFlow.stock); await message.answer("Stock inicial (entero):")
@router.message(ProductFlow.stock, F.text)
async def product_stock(message: Message, state: FSMContext):
    try: stock = int(message.text)
    except ValueError: await message.answer("❌ Stock inválido."); return
    if stock < 0: await message.answer("❌ El stock no puede ser negativo."); return
    await state.update_data(stock=stock); await state.set_state(ProductFlow.delivery); await message.answer("Datos de entrega por unidad (o escribe '-' si no aplica):")
@router.message(ProductFlow.delivery, F.text)
async def product_delivery(message: Message, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    actor = await event_user(message, session, current_user)
    if not is_admin(actor): await state.clear(); return
    data = await state.get_data(); product = Product(name=data["name"], category=data["category"], description=data["description"], price=money(data["price"]), stock=int(data["stock"]), delivery_data=None if message.text.strip() == "-" else message.text.strip())
    session.add(product); await log_event(session, actor.telegram_id, "product_create", data["name"], "created"); await session.commit(); await state.clear(); await message.answer("✅ Producto creado correctamente.", reply_markup=nav(True, "admin:products"))


@router.callback_query(F.data.startswith("admin:product:stock:"))
async def product_stock_prompt(callback: CallbackQuery, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    if not await check_admin(callback, session, current_user): return
    await state.set_state(ProductEdit.value); await state.update_data(edit="stock", product_id=int(callback.data.split(":")[3]))
    await edit_or_answer(callback, "📊 Escribe el nuevo stock entero (0 o más):")


@router.callback_query(F.data.startswith("admin:product:price:"))
async def product_price_prompt(callback: CallbackQuery, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    if not await check_admin(callback, session, current_user): return
    await state.set_state(ProductEdit.value); await state.update_data(edit="price", product_id=int(callback.data.split(":")[3]))
    await edit_or_answer(callback, "💵 Escribe el nuevo precio mayor que cero:")


@router.message(ProductEdit.value, F.text)
async def product_edit_value(message: Message, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    actor = await event_user(message, session, current_user)
    if not is_admin(actor): await state.clear(); return
    data = await state.get_data(); product = (await session.execute(select(Product).where(Product.id == data.get("product_id")).with_for_update())).scalar_one_or_none()
    if not product: await state.clear(); await message.answer("❌ Producto inexistente."); return
    if data.get("edit") == "stock":
        try: value = int(message.text.strip())
        except ValueError: await message.answer("❌ Stock inválido."); return
        if value < 0: await message.answer("❌ El stock no puede ser negativo."); return
        product.stock = value
    else:
        value = money(message.text)
        if value <= 0: await message.answer("❌ Precio inválido."); return
        product.price = value
    await log_event(session, actor.telegram_id, "product_edit", str(product.id), data.get("edit", "value")); await session.commit(); await state.clear(); await message.answer("✅ Producto actualizado.", reply_markup=nav(True, "admin:products"))


@router.callback_query(F.data.startswith("admin:product:"))
async def admin_product_detail(callback: CallbackQuery, session: AsyncSession, current_user: User | None = None):
    if not await check_admin(callback, session, current_user): return
    raw = callback.data.split(":")[2]
    if raw == "new": return
    product = (await session.execute(select(Product).where(Product.id == int(raw)))).scalar_one_or_none()
    if not product: await callback.answer("Producto inexistente.", show_alert=True); return
    from inline import kb
    rows = [[("🟢 Activar" if not product.is_active else "🔴 Desactivar", f"admin:product:toggle:{product.id}", None), ("🗑️ Eliminar", f"admin:product:delete:{product.id}", None)], [("📊 Modificar stock", f"admin:product:stock:{product.id}", None), ("💵 Cambiar precio", f"admin:product:price:{product.id}", None)], [("⬅️ Productos", "admin:products", None)]]
    await edit_or_answer(callback, f"📦 <b>{product.name}</b>\n\nCategoría: {product.category}\nDescripción: {product.description}\nPrecio: {m(product.price)}\nStock: {product.stock}\nEstado: {'Activo' if product.is_active else 'Inactivo'}\nVentas: {product.sales_count}", kb(rows))


@router.callback_query(F.data.startswith("admin:product:toggle:"))
async def product_toggle(callback: CallbackQuery, session: AsyncSession, current_user: User | None = None):
    actor = await check_admin(callback, session, current_user)
    if not actor: return
    product = (await session.execute(select(Product).where(Product.id == int(callback.data.split(":")[3])).with_for_update())).scalar_one_or_none()
    if product: product.is_active = not product.is_active; await log_event(session, actor.telegram_id, "product_toggle", str(product.id), str(product.is_active)); await session.commit()
    await edit_or_answer(callback, "✅ Estado del producto actualizado.", nav(True, "admin:products"))


@router.callback_query(F.data.startswith("admin:product:delete:"))
async def product_delete(callback: CallbackQuery, session: AsyncSession, current_user: User | None = None):
    actor = await check_admin(callback, session, current_user)
    if not actor: return
    product = (await session.execute(select(Product).where(Product.id == int(callback.data.split(":")[3])).with_for_update())).scalar_one_or_none()
    if product: product.is_active = False; await log_event(session, actor.telegram_id, "product_delete", str(product.id), "archived"); await session.commit()
    await edit_or_answer(callback, "✅ Producto archivado. Las compras históricas se conservan.", nav(True, "admin:products"))


@router.callback_query(F.data.startswith("admin:payments"))
async def admin_payments(callback: CallbackQuery, session: AsyncSession, current_user: User | None = None):
    if not await check_admin(callback, session, current_user): return
    requests = (await session.execute(select(TopupRequest).where(TopupRequest.status == TopupStatus.PENDING).order_by(TopupRequest.created_at).limit(10))).scalars().all()
    from inline import kb
    rows = [[(f"🟡 #{r.id} · {m(r.amount)} · {r.method}", f"topup:view:{r.id}", None)] for r in requests]
    rows.append([("⬅️ Panel Admin", "admin:home", None)])
    await edit_or_answer(callback, "💳 <b>PAGOS PENDIENTES</b>\n\n" + ("\n".join(f"#{r.id} · {m(r.amount)} · {r.method}" for r in requests) if requests else "No hay solicitudes pendientes."), kb(rows))


@router.callback_query(F.data.startswith("topup:view:"))
async def topup_view(callback: CallbackQuery, session: AsyncSession, current_user: User | None = None):
    if not await check_admin(callback, session, current_user): return
    request = (await session.execute(select(TopupRequest).where(TopupRequest.id == int(callback.data.split(":")[2])))).scalar_one_or_none()
    if not request: await callback.answer("Solicitud inexistente.", show_alert=True); return
    from inline import kb
    await edit_or_answer(callback, f"🧾 <b>SOLICITUD #{request.id}</b>\n\nMonto: {m(request.amount)}\nMétodo: {request.method}\nEstado: {request.status.value}\nFecha: {now_text(request.created_at)}\n\nEl comprobante fue enviado al canal administrativo al registrarse.", kb([[ ("✅ Aprobar", f"topup:approve:{request.id}", None), ("❌ Rechazar", f"topup:reject:{request.id}", None) ], [("⬅️ Pagos", "admin:payments", None) ]]))


@router.callback_query(F.data == "admin:coupons")
async def admin_coupons(callback: CallbackQuery, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    if not await check_admin(callback, session, current_user): return
    coupons = (await session.execute(select(Coupon).order_by(Coupon.id.desc()).limit(15))).scalars().all()
    await state.set_state(CouponAdminFlow.code)
    await edit_or_answer(callback, "🎟️ <b>CUPONES</b>\n\n" + ("\n".join(f"{c.code} · {'activo' if c.is_active else 'inactivo'} · {c.used_count}/{c.usage_limit or '∞'}" for c in coupons) if coupons else "No hay cupones.") + "\n\nEscribe un código nuevo para crearlo, o /cancelar.")


@router.message(CouponAdminFlow.code, F.text)
async def admin_coupon_code(message: Message, state: FSMContext): await state.update_data(code=message.text.strip().upper()); await state.set_state(CouponAdminFlow.discount); await message.answer("Descuento: escribe 10% para porcentaje o 5.00 para descuento fijo:")
@router.message(CouponAdminFlow.discount, F.text)
async def admin_coupon_discount(message: Message, state: FSMContext): await state.update_data(discount=message.text.strip()); await state.set_state(CouponAdminFlow.limit); await message.answer("Usos máximos (entero) o 0 para ilimitado:")
@router.message(CouponAdminFlow.limit, F.text)
async def admin_coupon_limit(message: Message, state: FSMContext):
    try: limit = int(message.text)
    except ValueError: await message.answer("❌ Límite inválido."); return
    await state.update_data(limit=limit or None); await state.set_state(CouponAdminFlow.expiry); await message.answer("Expiración en formato YYYY-MM-DD o '-' para sin expiración:")
@router.message(CouponAdminFlow.expiry, F.text)
async def admin_coupon_expiry(message: Message, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    actor = await event_user(message, session, current_user)
    if not is_admin(actor): await state.clear(); return
    data = await state.get_data(); raw = data["discount"]; percent = money(raw[:-1]) if raw.endswith("%") else None; fixed = None if percent is not None else money(raw)
    if (percent is not None and not 0 < percent <= 100) or (fixed is not None and fixed <= 0): await message.answer("❌ Descuento inválido."); return
    expires = None
    if message.text.strip() != "-":
        try: expires = datetime.strptime(message.text.strip(), "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError: await message.answer("❌ Fecha inválida."); return
    coupon = Coupon(code=data["code"], percent_off=percent, fixed_off=fixed, usage_limit=data["limit"], expires_at=expires)
    session.add(coupon); await log_event(session, actor.telegram_id, "coupon_create", coupon.code, "created"); await session.commit(); await state.clear(); await message.answer("✅ Cupón creado.", reply_markup=nav(True, "admin:home"))


@router.callback_query(F.data == "admin:broadcast")
async def admin_broadcast(callback: CallbackQuery, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    if not await check_admin(callback, session, current_user): return
    await state.set_state(BroadcastFlow.message); await edit_or_answer(callback, "📢 <b>DIFUSIÓN</b>\n\nEnvía el texto, foto, vídeo, documento o sticker que deseas copiar a usuarios no baneados. Usa /cancelar para salir.")


@router.message(BroadcastFlow.message)
async def broadcast_preview(message: Message, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    actor = await event_user(message, session, current_user)
    if not is_admin(actor): await state.clear(); return
    await state.update_data(source_chat=message.chat.id, source_message=message.message_id)
    from inline import kb
    await message.answer("⚠️ ¿Confirmar difusión a todos los usuarios activos?", reply_markup=kb([[ ("✅ Confirmar", "admin:broadcast:confirm", None), ("❌ Cancelar", "admin:home", None) ]]))


@router.callback_query(F.data == "admin:broadcast:confirm")
async def broadcast_confirm(callback: CallbackQuery, bot: Bot, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    actor = await check_admin(callback, session, current_user)
    if not actor: return
    data = await state.get_data(); users = (await session.execute(select(User.telegram_id).where(User.is_banned.is_(False)))).scalars().all(); sent = failed = 0
    await callback.answer("Difusión iniciada")
    for telegram_id in users:
        try:
            await bot.copy_message(telegram_id, data["source_chat"], data["source_message"]); sent += 1
        except (TelegramForbiddenError, TelegramBadRequest): failed += 1
        await asyncio.sleep(settings.BROADCAST_DELAY)
    await log_event(session, actor.telegram_id, "broadcast", None, f"sent={sent};failed={failed}"); await session.commit(); await state.clear()
    await callback.message.edit_text(f"📢 <b>DIFUSIÓN FINALIZADA</b>\n\n✅ Enviados: {sent}\n❌ Fallidos: {failed}", reply_markup=nav(True, "admin:home"))


@router.callback_query(F.data == "owner:admins")
async def owner_admins(callback: CallbackQuery, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    actor = await check_admin(callback, session, current_user)
    if not actor or not is_owner(actor): return
    admins = (await session.execute(select(User).where(User.role.in_([UserRole.ADMIN, UserRole.OWNER])))).scalars().all()
    await state.set_state(AdminIdFlow.waiting)
    await edit_or_answer(callback, "⚙️ <b>ADMINISTRADORES</b>\n\n" + ("\n".join(f"• {name_of(a)} · {a.telegram_id} · {a.role.value}" for a in admins)) + "\n\nEscribe el ID de Telegram para alternar Admin, o /cancelar.")


@router.message(AdminIdFlow.waiting, F.text)
async def owner_toggle_admin(message: Message, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    actor = await event_user(message, session, current_user)
    if not is_owner(actor): await state.clear(); return
    try: target_id = int(message.text.strip())
    except ValueError: await message.answer("❌ ID inválido."); return
    target = (await session.execute(select(User).where(User.telegram_id == target_id).with_for_update())).scalar_one_or_none()
    if not target or target.telegram_id == settings.OWNER_ID: await message.answer("❌ Usuario inexistente o Owner protegido."); return
    target.role = UserRole.USER if target.role == UserRole.ADMIN else UserRole.ADMIN
    await log_event(session, actor.telegram_id, "admin_role_change", str(target_id), target.role.value); await session.commit(); await state.clear(); await message.answer(f"✅ Rol actualizado: {target.role.value}.", reply_markup=nav(True, "owner:home"))


@router.callback_query(F.data == "owner:logs")
async def owner_logs(callback: CallbackQuery, session: AsyncSession, current_user: User | None = None):
    actor = await check_admin(callback, session, current_user)
    if not actor or not is_owner(actor): return
    logs = (await session.execute(select(AuditLog).order_by(desc(AuditLog.created_at)).limit(20))).scalars().all()
    text = "📜 <b>REGISTROS RECIENTES</b>\n\n" + ("\n".join(f"{now_text(x.created_at)} · {x.actor_telegram_id} · {x.action} · {x.result}" for x in logs) if logs else "Sin registros.")
    await edit_or_answer(callback, text[:4000], nav(True, "owner:home"))


@router.callback_query(F.data.in_({"admin:credits", "admin:security", "owner:config"}))
async def admin_secondary(callback: CallbackQuery, session: AsyncSession, current_user: User | None = None):
    actor = await check_admin(callback, session, current_user)
    if not actor: return
    if callback.data == "admin:security": text = "🛡️ <b>SEGURIDAD</b>\n\nTodas las acciones administrativas vuelven a verificar el rol. Las compras y aprobaciones usan bloqueo de fila y estados para evitar duplicados."
    elif callback.data == "admin:credits": text = "💰 <b>CRÉDITOS</b>\n\nBusca un usuario desde Usuarios para agregar o quitar saldo con confirmación y registro de auditoría."
    else: text = f"🔧 <b>CONFIGURACIÓN</b>\n\nTienda: {settings.STORE_NAME}\nMoneda: {settings.CURRENCY}\nZona horaria: {settings.TIMEZONE}\nYape/Plin: {'configurado' if settings.YAPE_NUMBER or settings.PLIN_NUMBER else 'no configurado'}\nBinance: {'habilitado' if settings.BINANCE_USDT_ENABLED else 'deshabilitado'}"
    await edit_or_answer(callback, text, nav(True, "owner:home" if callback.data == "owner:config" else "admin:home"))


@router.callback_query(F.data == "product:search")
async def product_search_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ProductSearch.waiting); await edit_or_answer(callback, "🔎 Escribe el nombre del producto que buscas. /cancelar para salir.")


@router.message(ProductSearch.waiting, F.text)
async def product_search(message: Message, state: FSMContext, session: AsyncSession):
    query = message.text.strip(); products = (await session.execute(select(Product).where(Product.is_active.is_(True), Product.name.ilike(f"%{query}%")).limit(10))).scalars().all()
    from inline import kb
    rows = [[(f"📦 {p.name} · {m(p.price)}", f"product:{p.id}", None)] for p in products]; rows.append([("⬅️ Catálogo", "menu:catalog", None)])
    await state.clear(); await message.answer(("🔎 <b>RESULTADOS</b>\n\n" + "\n".join(f"• {p.name} — {m(p.price)}" for p in products)) if products else "❌ No encontramos productos relacionados.", reply_markup=kb(rows))


@router.callback_query()
async def fallback_callback(callback: CallbackQuery):
    await callback.answer("Esta opción ya no está disponible. Abre el menú principal.", show_alert=True)
