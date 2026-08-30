from __future__ import annotations

import asyncio
import enum
import logging
import math
import secrets
import sys
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from html import escape
from pathlib import Path
from time import monotonic
from typing import Any
from urllib.parse import quote

from aiogram import BaseMiddleware, Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramNetworkError,
)
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    TelegramObject,
)
from openai import AsyncOpenAI, OpenAIError
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    desc,
    func,
    or_,
    select,
    text,
    update,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import (
    inspect as sa_inspect,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# Configuración
class Settings(BaseSettings):
    BOT_TOKEN: str
    OWNER_ID: int
    DATABASE_URL: str = "sqlite+aiosqlite:///./lxz_store.db"
    STORE_NAME: str = "LXZ STORE BEST"
    CURRENCY: str = "USD"
    TIMEZONE: str = "America/Lima"
    OFFICIAL_CHANNEL_URL: str = ""
    SUPPORT_USERNAME: str = "Lxz_Modz"
    SUPPORT_URL: str = "https://t.me/Lxz_Modz"
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = ""
    OPENAI_MODEL: str = "gpt-5-mini"
    OPENAI_FALLBACK_MODEL: str = "gpt-5-nano"
    AI_COOLDOWN_SECONDS: float = 2.0
    YAPE_NUMBER: str = ""
    YAPE_NAME: str = ""
    LIGO_NUMBER: str = ""
    LIGO_NAME: str = ""
    PLIN_NUMBER: str = ""
    PLIN_NAME: str = ""
    ARGENTINA_METHOD_NAME: str = "Mercado Pago"
    ARGENTINA_ACCOUNT: str = ""
    ARGENTINA_HOLDER: str = ""
    COLOMBIA_METHOD_NAME: str = "Nequi"
    COLOMBIA_ACCOUNT: str = ""
    COLOMBIA_HOLDER: str = ""
    VENEZUELA_BANK_NAME: str = ""
    VENEZUELA_PAYMENT_TYPE: str = ""
    VENEZUELA_ID: str = ""
    VENEZUELA_PHONE: str = ""
    BINANCE_USDT_ENABLED: bool = False
    BINANCE_USDT_ADDRESS: str = ""
    BINANCE_USDT_NETWORK: str = "TRC20"
    ADMIN_IDS: str = ""
    REFERRAL_BONUS: float = 0.0
    PAGE_SIZE: int = 6
    BROADCAST_DELAY: float = 0.05
    APP_VERSION: str = "professional-roles-security-inventory-2026-08-26"
    PARTNER_FEE_USD: Decimal = Decimal("10.00")
    PARTNER_DISCOUNT_PERCENT: Decimal = Decimal("20.00")
    PREMIUN_FEE_USD: Decimal = Decimal("5.00")
    PREMIUN_DISCOUNT_PERCENT: Decimal = Decimal("10.00")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def admin_ids(self) -> set[int]:
        result = set()
        for value in self.ADMIN_IDS.split(","):
            try:
                if value.strip():
                    result.add(int(value.strip()))
            except ValueError:
                continue
        result.add(self.OWNER_ID)
        return result


settings = Settings()

# Modelos de datos
class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def migrate_schema(sync_conn) -> None:
    tables = set(sa_inspect(sync_conn).get_table_names())
    if "users" in tables:
        columns = {column["name"] for column in sa_inspect(sync_conn).get_columns("users")}
        if "rank_title" not in columns:
            sync_conn.execute(text("ALTER TABLE users ADD COLUMN rank_title VARCHAR(64)"))
        if "is_partner" not in columns:
            sync_conn.execute(text("ALTER TABLE users ADD COLUMN is_partner BOOLEAN NOT NULL DEFAULT 0"))
        if "partner_since" not in columns:
            sync_conn.execute(text("ALTER TABLE users ADD COLUMN partner_since DATETIME"))
        if "role" in columns:
            # UserRole almacena los nombres de los miembros del enum en SQLite.
            # Convertimos los roles antiguos para que no queden valores huérfanos.
            sync_conn.execute(text("UPDATE users SET role = 'USUARIO' WHERE lower(role) IN ('user', 'usuario')"))
            sync_conn.execute(text("UPDATE users SET role = 'SOCIO' WHERE lower(role) IN ('vip', 'socio')"))
            sync_conn.execute(text("UPDATE users SET role = 'PREMIUN' WHERE lower(role) IN ('premium', 'premiun')"))
            sync_conn.execute(text("UPDATE users SET role = 'ADMIN' WHERE lower(role) IN ('support', 'soporte', 'seller', 'vendedor', 'admin')"))
            sync_conn.execute(text("UPDATE users SET role = 'OWNER' WHERE lower(role) = 'owner'"))
            sync_conn.execute(text("UPDATE users SET role = 'DUENO' WHERE telegram_id = :owner_id"), {"owner_id": settings.OWNER_ID})
            sync_conn.execute(text("UPDATE users SET role = 'OWNER' WHERE role = 'DUENO' AND telegram_id != :owner_id"), {"owner_id": settings.OWNER_ID})


class StoreSetting(Base):
    __tablename__ = "store_settings"
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class UserRole(str, enum.Enum):
    DUENO = "DUEÑO"
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    SOCIO = "SOCIO"
    PREMIUN = "PREMIUN"
    USUARIO = "USUARIO"


class PurchaseStatus(str, enum.Enum):
    PAID = "paid"
    CANCELLED = "cancelled"


class TopupStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class BalanceTransactionType(str, enum.Enum):
    TOPUP = "topup"
    PURCHASE = "purchase"
    CREDIT = "credit"
    DEBIT = "debit"
    REFERRAL = "referral"
    REFUND = "refund"


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(64), index=True)
    first_name: Mapped[str] = mapped_column(String(128), nullable=False, default="Usuario")
    last_name: Mapped[str | None] = mapped_column(String(128))
    balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ban_reason: Mapped[str | None] = mapped_column(String(255))
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    premium_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), default=UserRole.USUARIO, nullable=False)
    rank_title: Mapped[str | None] = mapped_column(String(64))
    is_partner: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    partner_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_spent: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    purchases_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    referrals_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    referral_earnings: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    referred_by: Mapped[int | None] = mapped_column(BigInteger, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    last_activity: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(64), index=True, nullable=False, default="Otros")
    name: Mapped[str] = mapped_column(String(160), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    delivery_data: Mapped[str | None] = mapped_column(Text)
    image_file_id: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sales_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class Auction(Base):
    __tablename__ = "auctions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_name: Mapped[str] = mapped_column(String(160), nullable=False)
    initial_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    current_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    increment: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("2.00"))
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    winner_id: Mapped[int | None] = mapped_column(BigInteger)
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AuctionBid(Base):
    __tablename__ = "auction_bids"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    auction_id: Mapped[int] = mapped_column(ForeignKey("auctions.id"), index=True, nullable=False)
    bidder_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Coupon(Base):
    __tablename__ = "coupons"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    percent_off: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    fixed_off: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    usage_limit: Mapped[int | None] = mapped_column(Integer)
    used_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class CouponRedemption(Base):
    __tablename__ = "coupon_redemptions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    coupon_id: Mapped[int] = mapped_column(ForeignKey("coupons.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    purchase_id: Mapped[int | None] = mapped_column(ForeignKey("purchases.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    __table_args__ = (Index("ix_coupon_user", "coupon_id", "user_id", unique=True),)


class Purchase(Base):
    __tablename__ = "purchases"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"))
    product_name: Mapped[str] = mapped_column(String(160), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    coupon_code: Mapped[str | None] = mapped_column(String(40))
    delivery_data: Mapped[str | None] = mapped_column(Text)
    status: Mapped[PurchaseStatus] = mapped_column(SQLEnum(PurchaseStatus), default=PurchaseStatus.PAID, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class KeyDelivery(Base):
    __tablename__ = "key_deliveries"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    purchase_id: Mapped[int] = mapped_column(ForeignKey("purchases.id"), index=True, nullable=False)
    key_value: Mapped[str] = mapped_column(Text, nullable=False)
    duration: Mapped[str] = mapped_column(String(120), nullable=False)
    delivered_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class TopupRequest(Base):
    __tablename__ = "topup_requests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    method: Mapped[str] = mapped_column(String(160), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    proof_file_id: Mapped[str] = mapped_column(String(255), nullable=False)
    proof_type: Mapped[str] = mapped_column(String(20), default="photo", nullable=False)
    status: Mapped[TopupStatus] = mapped_column(SQLEnum(TopupStatus), default=TopupStatus.PENDING, nullable=False)
    reviewed_by: Mapped[int | None] = mapped_column(BigInteger)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class BalanceTransaction(Base):
    __tablename__ = "balance_transactions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    kind: Mapped[BalanceTransactionType] = mapped_column(SQLEnum(BalanceTransactionType), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(64))
    note: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_telegram_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    target: Mapped[str | None] = mapped_column(String(100))
    result: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


__all__ = [
    "AuditLog",
    "BalanceTransaction",
    "BalanceTransactionType",
    "Base",
    "Coupon",
    "CouponRedemption",
    "KeyDelivery",
    "Product",
    "Purchase",
    "PurchaseStatus",
    "Setting",
    "TopupRequest",
    "TopupStatus",
    "User",
    "UserRole",
    "utcnow",
]


# Motor y sesiones
database_url = settings.DATABASE_URL or "sqlite+aiosqlite:///./lxz_store.db"
engine_options = {"echo": False}
if database_url.startswith("sqlite"):
    engine_options["connect_args"] = {"timeout": 30}
engine = create_async_engine(database_url, **engine_options)
async_session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)


# Teclados inline
def kb(rows):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t, callback_data=c) if c else InlineKeyboardButton(text=t, url=u) for t, c, u in row] for row in rows])


def main_menu(role: UserRole, channel_url: str = "") -> InlineKeyboardMarkup:
    rows = [
        [("🛍️ Catálogo de Productos", "menu:catalog", None)],
        [("🔨 SUBASTAS", "menu:auctions", None)],
        [("💳 Recargar Saldo", "menu:balance", None), ("👤 Mi Perfil", "menu:profile", None)],
        [("💎 PREMIUN (10% OFF)", "menu:premium", None), ("🤝 SOCIO (20% OFF)", "menu:partner", None)],
        [("🎟️ Canjear Cupón", "menu:coupons", None), ("📞 Soporte", None, "https://t.me/Lxz_Modz")],
    ]
    if channel_url:
        rows[-1].append(("📢 Canal Oficial", None, channel_url))
    if role == UserRole.DUENO:
        rows.append([("🏆 Panel DUEÑO", "owner:home", None)])
    elif role == UserRole.OWNER:
        rows.append([("👑 Panel OWNER", "owner:home", None)])
    elif role == UserRole.ADMIN:
        rows.append([("⚙️ Panel ADMIN", "admin:home", None)])
    return kb(rows)


def nav(home: bool = True, back: str = "menu:home") -> InlineKeyboardMarkup:
    rows = []
    if back:
        rows.append([("⬅️ Atrás", back, None)])
    if home:
        rows.append([("🏠 Inicio", "menu:home", None)])
    return kb(rows)


def categories(categories: list[str]) -> InlineKeyboardMarkup:
    rows = [[(CATEGORY_LABELS.get(name, name), f"cat:{name}", None)] for name in categories]
    rows.append([("🏠 Inicio", "menu:home", None)])
    return kb(rows)


def product_list(items, page: int, pages: int, category: str) -> InlineKeyboardMarkup:
    rows = [[(f"📦 {p.name} 📥", f"product:{p.id}", None)] for p in items]
    pager = []
    if page > 0:
        pager.append(("◀️ Anterior", f"products:{category}:{page-1}", None))
    if page + 1 < pages:
        pager.append(("▶️ Siguiente", f"products:{category}:{page+1}", None))
    if pager:
        rows.append(pager)
    rows.append([("⬅️ Categorías", "menu:catalog", None), ("🏠 Inicio", "menu:home", None)])
    return kb(rows)


def product_detail(product_id: int, back: str, can_buy: bool = True, variants: list | None = None) -> InlineKeyboardMarkup:
    rows = []
    if can_buy:
        if variants:
            for v_name, v_price in variants:
                rows.append([(f"⏳ {v_name} | {v_price} USD", f"buy:{product_id}:{v_name}", None)])
        else:
            rows.append([("🛒 Comprar", f"buy:{product_id}:default", None)])
    rows.append([("⬅️ Productos", back, None), ("🏠 Inicio", "menu:home", None)])
    return kb(rows)


def confirm(action: str, cancel: str = "menu:home") -> InlineKeyboardMarkup:
    return kb([[ ("✅ Confirmar", action, None), ("❌ Cancelar", cancel, None) ]])


def partner_menu() -> InlineKeyboardMarkup:
    return kb([
        [("💰 Pagar usando mi saldo", "partner:pay_balance", None)],
        [("🏦 Pagar con depósito / transferencia", "partner:manual", None)],
        [("⬅️ Regresar al menú", "menu:home", None)],
    ])


def premium_menu() -> InlineKeyboardMarkup:
    return kb([
        [("💰 Comprar PREMIUN con mi saldo", "premium:pay_balance", None)],
        [("🏦 Pagar por transferencia", "premium:manual", None)],
        [("⬅️ Regresar al menú", "menu:home", None)],
    ])


def topup_countries() -> InlineKeyboardMarkup:
    rows = []
    for region, countries in TOPUP_REGIONS.items():
        rows.append([(region, "topup:noop", None)])
        for index in range(0, len(countries), 2):
            rows.append([(label, f"topup:country:{code}", None) for code, label in countries[index:index + 2]])
    rows.append([("👤 Contactar para Recarga", "topup:assisted", None)])
    rows.append([("❌ Cancelar", "menu:home", None)])
    return kb(rows)


def payment_methods() -> InlineKeyboardMarkup:
    rows = [[(f"💳 {label}", f"topup:method:{method}", None)] for method, label in TOPUP_METHOD_LABELS.items()]
    rows.append([("👤 Recarga asistida", "topup:assisted", None)])
    rows.append([("📍 Elegir otro país", "menu:balance", None)])
    rows.append([("❌ Cancelar", "menu:home", None)])
    return kb(rows)


def peru_currency_methods() -> InlineKeyboardMarkup:
    return kb([
        [("🇵🇪 Soles (PEN)", "topup:currency:pen", None)],
        [("📍 Elegir otro país", "menu:balance", None)],
        [("❌ Cancelar", "menu:home", None)],
    ])


def crypto_assets() -> InlineKeyboardMarkup:
    return kb([
        [("₮ USDT", "topup:asset:usdt", None), ("$ USDC", "topup:asset:usdc", None)],
        [("👤 Recarga asistida", "topup:assisted", None)],
        [("📍 Elegir otro país", "menu:balance", None)],
        [("❌ Cancelar", "menu:home", None)],
    ])


def crypto_networks(asset: str) -> InlineKeyboardMarkup:
    rows = [[(f"🌐 {config['label']}", f"topup:network:{network}", None)] for network, config in CRYPTO_NETWORK_CONFIG.items()]
    rows.append([("⬅️ Elegir USDC/USDT", "topup:crypto_assets", None)])
    rows.append([("📍 Elegir otro país", "menu:balance", None)])
    rows.append([("❌ Cancelar", "menu:home", None)])
    return kb(rows)


def local_payment_methods(country: str) -> InlineKeyboardMarkup:
    labels = {
        "ar": "🇦🇷 Mercado Pago",
        "co": "🇨🇴 Nequi",
        "ve": "🇻🇪 Bancamiga · Pago móvil",
    }
    return kb([
        [(labels[country], "topup:venezuela_method:bancamiga" if country == "ve" else f"topup:local_method:{country}", None)],
        [("📍 Elegir otro país", "menu:balance", None)],
        [("❌ Cancelar", "menu:home", None)],
    ])

def venezuela_payment_methods() -> InlineKeyboardMarkup:
    return kb([
        [("🏦 Bancamiga · Pago móvil", "topup:venezuela_method:bancamiga", None)],
        [("📍 Elegir otro país", "menu:balance", None)],
        [("❌ Cancelar", "menu:home", None)],
    ])

def peru_payment_methods() -> InlineKeyboardMarkup:
    return kb([
        [("📱 Yape", "topup:peru_method:yape", None), ("📱 Plin", "topup:peru_method:plin", None)],
        [("💳 Takenos (Ligo)", "topup:peru_method:ligo", None)],
        [("🏦 Transferencia bancaria · CCI", "topup:peru_method:bank", None)],
        [("📍 Elegir otra moneda", "topup:country:pe", None)],
        [("❌ Cancelar", "menu:home", None)],
    ])


def topup_amounts(currency: str = "USD", rate: Decimal = Decimal(1), first_topup: bool = False) -> InlineKeyboardMarkup:
    rows = []
    available = [amount for amount in TOPUP_AMOUNTS if not first_topup or Decimal(str(amount)) >= FIRST_TOPUP_MINIMUM_USD]
    for index in range(0, len(available), 3):
        row = []
        for usd_amount in available[index:index + 3]:
            source_amount = money(Decimal(usd_amount) * rate)
            row.append((f"💵 {source_amount} {currency}", f"topup:amount:{source_amount}:{currency}:{usd_amount}", None))
        rows.append(row)
    rows.append([("✍️ Monto personalizado", "topup:custom", None)])
    rows.append([("📍 Elegir otro país", "menu:balance", None)])
    rows.append([("❌ Cancelar", "menu:home", None)])
    return kb(rows)


def admin_home(role: UserRole = UserRole.ADMIN) -> InlineKeyboardMarkup:
    rows = []
    if role in (UserRole.OWNER, UserRole.DUENO):
        rows.append([("👥 Usuarios", "admin:users", None), ("📦 Productos", "admin:products", None)])
    rows.extend([
        [("💳 Pagos", "admin:payments", None), ("📊 Estadísticas", "admin:stats", None)],
    ])
    if role in (UserRole.OWNER, UserRole.DUENO):
        rows.extend([
            [("📢 Difusión", "admin:broadcast", None), ("🎟️ Cupones", "admin:coupons", None)],
            [("💰 Saldo USD", "admin:credits", None), ("🚫 Seguridad", "admin:security", None)],
        ])
    if role == UserRole.DUENO:
        rows.extend([
            [("🔨 Subastas", "owner:auctions", None)],
            [("⚙️ Equipo y Rangos", "owner:admins", None), ("📜 Registros", "owner:logs", None)],
            [("🔧 Configuración", "owner:config", None)],
        ])
    rows.append([("🏠 Inicio", "menu:home", None)])
    return kb(rows)


# Middleware de base de datos
class DatabaseMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]], event: TelegramObject, data: dict[str, Any]) -> Any:
        async with async_session_maker() as session:
            data["session"] = session
            return await handler(event, data)


# Middleware de autenticación
BANNED_TEXT = (
    "❰ ʟxᴢ ꜱᴛᴏʀᴇ ʙᴇꜱᴛ — 𝐀𝐂𝐂𝐄𝐒𝐒 𝐃𝐄𝐍𝐈𝐄𝐃 ❱\n\n"
    "🚫 <b>ACCESO BLOQUEADO</b>\n\n"
    "Tu cuenta tiene una restricción permanente en el sistema.\n"
    "No puedes usar comandos, abrir el menú ni utilizar botones.\n\n"
    "Para solicitar una revisión o desbaneo, contacta a soporte: "
    f"{settings.SUPPORT_URL}"
)
BANNED_MARKUP = kb([[('📞 Contactar soporte', None, settings.SUPPORT_URL)]])


class AuthMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]], event: TelegramObject, data: dict[str, Any]) -> Any:
        session: AsyncSession | None = data.get("session")
        if session is None or not isinstance(event, (Message, CallbackQuery)) or not event.from_user:
            return await handler(event, data)
        user = (await session.execute(select(User).where(User.telegram_id == event.from_user.id))).scalar_one_or_none()
        if user and user.is_banned:
            if isinstance(event, CallbackQuery):
                await event.answer("🚫 Baneo permanente. Contacta a soporte.", show_alert=True)
                if event.message:
                    try:
                        await event.message.edit_text(BANNED_TEXT, reply_markup=BANNED_MARKUP)
                    except TelegramBadRequest:
                        await event.message.answer(BANNED_TEXT, reply_markup=BANNED_MARKUP)
            else:
                await event.answer(BANNED_TEXT, reply_markup=BANNED_MARKUP, disable_web_page_preview=True)
            return
        data["current_user"] = user
        return await handler(event, data)


# Handlers y lógica de negocio
router = Router()
logger = logging.getLogger(__name__)
PAGE_SIZE = max(1, settings.PAGE_SIZE)
CATEGORIES = ["Android", "iOS", "PC", "Otros"]
CATEGORY_LABELS = {"Android": "📁 APK MODZ / ANDROID", "iOS": "📁 IPHONE / IOS", "PC": "💻 WINDOWS / PC", "Otros": "📁 OTROS"}
IMAGE_BY_PRODUCT = {
    "DRIP CLIENT": "assets/drip_client_android.jpg",
    "PRÓXY ANDROID": "assets/drip_client_free_fire.jpg",
    "HG CHEATS": "assets/hg_cheats.jpg",
    "PROXY MENÚ": "assets/proxy_menu_hg_cheats.jpg",
    "PROYECTO HOLOGRAMA VIP": "assets/proyecto_holograma_vip.jpg",
    "PROXY POTATSO": "assets/proxy_potatso_ios.jpg",
    "E-SIGN": "assets/esign.jpg",
    "FLOURITE": "assets/flourite.jpg",
    "CUBAN MODS": "assets/cuban_mods.jpg",
    "PATO TEAM": "assets/pato_team.jpg",
    "BR MODS PC": "assets/br_mods_pc.jpg",
    "BYPASS UID": "assets/bypass_uid.jpg",
    "NUMEROS VIRTUALES (PARA WHATSAPP)": "assets/numeros_virtuales_whatsapp.jpg",
    "PLATAFORMA STREAMING": "assets/plataforma_streaming.jpg",
}


HOME_BANNER = "assets/lxz_store_banner.png"


def image_for_product(name: str) -> str | None:
    return IMAGE_BY_PRODUCT.get(name.strip().upper())


TOPUP_REGIONS = {
    "🌎 PAÍSES DISPONIBLES": [
        ("ar", "🇦🇷 Argentina"),
        ("bo", "🇧🇴 Bolivia"),
        ("br", "🇧🇷 Brasil"),
        ("cl", "🇨🇱 Chile"),
        ("co", "🇨🇴 Colombia"),
        ("cr", "🇨🇷 Costa Rica"),
        ("ec", "🇪🇨 Ecuador"),
        ("sv", "🇸🇻 El Salvador"),
        ("es", "🇪🇸 España"),
        ("us", "🇺🇸 Estados Unidos"),
        ("gt", "🇬🇹 Guatemala"),
        ("hn", "🇭🇳 Honduras"),
        ("mx", "🇲🇽 México"),
        ("ni", "🇳🇮 Nicaragua"),
        ("pa", "🇵🇦 Panamá"),
        ("py", "🇵🇾 Paraguay"),
        ("pe", "🇵🇪 Perú"),
        ("do", "🇩🇴 República Dominicana"),
        ("uy", "🇺🇾 Uruguay"),
        ("ve", "🇻🇪 Venezuela"),
    ],
}
TOPUP_COUNTRIES = [country for countries in TOPUP_REGIONS.values() for country in countries]
TOPUP_AMOUNTS = (3, 5, 10, 15, 20, 30, 50, 100)
TOPUP_METHOD_LABELS = {
    "paypal": "PayPal",
    "binance": "Binance",
    "mercado_pago": "Mercado Pago",
    "yape_plin": "Yape / Plin",
}
PERU_PAYMENT_CONFIG = {
    "phone": "927816593",
    "cci": "92100129860882862046",
    "holder": "Serafin Armando Corahua Fernandez",
    "rate": Decimal("3.40"),
    "minimum": Decimal("3.40"),
    "maximum": Decimal("30000.00"),
}
CRYPTO_NETWORK_CONFIG = {
    "ethereum": {
        "label": "Ethereum (ETH)",
        "network": "Ethereum · Red nativa de Ethereum",
        "address": "0x7CEEC2E1c74500573884C9747CB6B12e0d6a2054",
        "fee": "Costo de red de Ethereum",
        "instruction": "Envía únicamente USDC/USDT en la red Ethereum a esta dirección. De lo contrario, podrías perder tus fondos.",
    },
    "tron": {
        "label": "Tron (TRX)",
        "network": "Tron · Red nativa para transferencias TRON",
        "address": "TFMLUcX41GCvdeAd2raKkDnKXwabfsC7v",
        "fee": "Costo de red: 5 USDC/USDT",
        "instruction": "Envía únicamente USDC/USDT en la red Tron a esta dirección. De lo contrario, podrías perder tus fondos.",
    },
    "bsc": {
        "label": "BNB Smart Chain (BEP20)",
        "network": "BNB Smart Chain (BEP20) · Red nativa de Binance",
        "address": "0x7CEEC2E1c74500573884C9747CB6B12e0d6a2054",
        "fee": "Costo de red de Binance Smart Chain",
        "instruction": "Envía únicamente USDC/USDT en la red BNB Smart Chain (BEP20) a esta dirección. No envíes desde la red OPBNB.",
    },
    "polygon": {
        "label": "Polygon POS",
        "network": "Polygon POS · Red nativa de MATIC",
        "address": "0x7CEEC2E1c74500573884C9747CB6B12e0d6a2054",
        "fee": "Costo de red de Polygon",
        "instruction": "Envía únicamente USDC/USDT en la red Polygon POS a esta dirección. De lo contrario, podrías perder tus fondos.",
    },
}


INITIAL_PRODUCTS = {
    "Android": [
        "PRÓXY ANDROID", "DRIP CLIENT", "BR MODS MÓVIL - ROOT", "PATO TEAM", "CUBAN MODS",
        "HG CHEATS", "PRIME HOCK APK", "PROXY MENÚ", "PROYECTO HOLOGRAMA VIP", "PATO REGEDIT", "BALA MOD ANDROID",
        "PROXY HG CHEATS", "PANEL HOLO VIP", "PROXY DRIP",
    ],
    "iOS": ["PROXY POTATSO", "CERTIFICADO IPHONE", "E-Sign", "FLOURITE", "MONITE CHEATS IPHONE", "MONITE IOS PRO", "MONITE IOS BASIC", "GBOX CERTIFICADO", "MIGUIL MONITE LITE", "MIGUIL MONITE PRO"],
    "PC": ["BYPASS UID", "BR MODS PC", "AIMKILL PC"],
    "Otros": ["NUMEROS VIRTUALES (Para WhatsApp)", "PLATAFORMA STREAMING"],
}

# Prices supplied by the owner. The first variant is also the base display price.
PRICE_CATALOG = {
    "PRÓXY ANDROID": [("1 Día", "2.00"), ("3 Días", "3.00"), ("7 Días", "7.00"), ("30 Días", "12.00")],
    "DRIP CLIENT": [("7 Días", "6.00"), ("30 Días", "12.00"), ("Permanente", "50.00")],
    "BR MODS MÓVIL - ROOT": [("1 Día", "2.00"), ("7 Días", "7.00"), ("30 Días", "12.00")],
    "PATO TEAM": [("3 Días", "3.00"), ("7 Días", "8.00"), ("15 Días", "6.00"), ("30 Días", "15.00")],
    "CUBAN MODS": [("1 Día", "2.00"), ("7 Días", "7.00"), ("30 Días", "12.00")],
    "HG CHEATS": [("1 Día", "3.00"), ("10 Días", "8.00"), ("30 Días", "14.00")],
    "PROXY POTATSO": [("1 Día", "2.00"), ("7 Días", "4.00"), ("30 Días", "18.00"), ("Keis Ilimitadas", "25.00")],
    "CERTIFICADO IPHONE": [("360 Días", "10.00")],
    "FLOURITE": [("1 Día", "5.00"), ("7 Días", "15.00"), ("30 Días", "31.00"), ("Permanente", "100.00")],
    "BR MODS PC": [("1 Día", "3.00"), ("10 Días", "7.00"), ("30 Días", "15.00")],
    "AIMKILL PC": [("1 Día", "3.00"), ("7 Días", "7.00"), ("30 Días", "15.00"), ("365 Días", "30.00")],
    "PATO REGEDIT": [("1 Hora", "1.00"), ("3 Horas", "2.00"), ("6 Horas", "3.00"), ("12 Horas", "5.00"), ("1 Día", "8.00"), ("2 Días", "12.00"), ("3 Días", "15.00"), ("7 Días", "20.00")],
    "BALA MOD ANDROID": [("1 Hora", "1.00"), ("3 Horas", "2.00"), ("6 Horas", "3.00"), ("12 Horas", "5.00"), ("1 Día", "8.00"), ("2 Días", "12.00"), ("3 Días", "15.00"), ("7 Días", "20.00")],
    "PROXY HG CHEATS": [("1 Día", "3.00"), ("10 Días", "6.00"), ("21 Días", "12.00")],
    "PANEL HOLO VIP": [("30 Días", "15.00"), ("Permanente", "40.00")],
    "PROXY DRIP": [("1 Día", "3.00"), ("7 Días", "7.00"), ("30 Días", "15.00")],
    "MIGUIL MONITE LITE": [("1 Día", "3.00"), ("7 Días", "8.00"), ("30 Días", "15.00")],
    "MIGUIL MONITE PRO": [("1 Día", "5.00"), ("7 Días", "15.00"), ("31 Días", "31.00")],
    "MONITE CHEATS IPHONE": [("1 Mes", "25.00"), ("3 Meses", "50.00"), ("Permanente", "150.00")],
    "PROXY MENÚ": [("1 Día", "0.70"), ("10 Días", "8.00")],
    "PROYECTO HOLOGRAMA VIP": [("30 Días", "9.90"), ("Permanente", "29.90")],
    "E-Sign": [("360 Días", "10.00")],
    "BYPASS UID": [("30 Días", "10.00"), ("Permanente", "40.00")],
    "NUMEROS VIRTUALES (Para WhatsApp)": [("Acceso", "10.00")],
    "PLATAFORMA STREAMING": [("Acceso", "25.00")],
    "MONITE IOS PRO": [("1 Día", "5.00"), ("7 Días", "15.00"), ("31 Días", "31.00")],
    "MONITE IOS BASIC": [("1 Día", "3.00"), ("7 Días", "8.00"), ("30 Días", "15.00")],
    "GBOX CERTIFICADO": [("360 Días", "10.00")],
    "PRIME HOCK APK": [("1 Día", "5.00")],
}
PRICE_CATEGORIES = {
    "PATO REGEDIT": "Android", "BALA MOD ANDROID": "Android", "PROXY HG CHEATS": "Android",
    "MIGUIL MONITE LITE": "iOS", "MIGUIL MONITE PRO": "iOS", "MONITE CHEATS IPHONE": "iOS",
}

def price_variants_text(variants: list[tuple[str, str]]) -> str:
    return ", ".join(f"{name} | {price} USD" for name, price in variants)


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


class AuctionFlow(StatesGroup):
    product_name = State()
    initial_price = State()
    duration = State()
    increment = State()


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
def parse_variants(description: str | None) -> list[tuple[str, Decimal]]:
    variants = []
    if not description or "|" not in description:
        return variants
    for part in description.split(","):
        if "|" not in part:
            continue
        name, raw_price = part.split("|", 1)
        price = money(raw_price.strip().replace("$", ""))
        name = name.strip()
        if name and price > 0:
            variants.append((name, price))
    return variants


def selected_price(product: Product, variant: str) -> Decimal | None:
    if variant == "default":
        price = money(product.price)
        return price if price > 0 else None
    for name, price in parse_variants(product.description):
        if name == variant:
            return price
    return None


def purchase_duration(purchase: Purchase) -> str:
    product_name = (purchase.product_name or "").strip()
    if product_name.endswith(")") and "(" in product_name:
        duration = product_name.rsplit("(", 1)[1][:-1].strip()
        if duration:
            return duration
    return "No especificada"
def name_of(user: User) -> str:
    return " ".join(x for x in [user.first_name, user.last_name] if x) or str(user.telegram_id)


_ai_client: AsyncOpenAI | None = None
_ai_last_request: dict[int, float] = {}


async def ai_catalog_context(session: AsyncSession) -> str:
    products = (await session.execute(select(Product).order_by(Product.category, Product.name))).scalars().all()
    if not products:
        return "No hay productos registrados todavía."
    rows = []
    for product in products[:80]:
        status = "disponible" if product.is_active and product.stock > 0 else "no disponible todavía"
        variants = product.description or "sin variantes configuradas"
        rows.append(f"- {product.name} | categoría: {product.category} | estado: {status} | stock: {product.stock} | precios/duraciones: {variants[:300]}")
    return "\n".join(rows)


async def client_ai_answer(message: Message, bot: Bot, session: AsyncSession, user: User) -> None:
    global _ai_client
    prompt = (message.text or "").strip()
    if not prompt or prompt.startswith("/"):
        return
    now = monotonic()
    last = _ai_last_request.get(user.telegram_id, 0.0)
    if now - last < settings.AI_COOLDOWN_SECONDS:
        await message.answer("⏳ Espera un momento antes de enviar otra consulta.")
        return
    _ai_last_request[user.telegram_id] = now
    if not settings.OPENAI_API_KEY:
        await message.answer(f"🤖 El asistente está temporalmente fuera de servicio.\n\n📞 Soporte: {settings.SUPPORT_URL}")
        return
    if _ai_client is None:
        client_options = {"api_key": settings.OPENAI_API_KEY.strip().strip('"').strip("'")}
        if settings.OPENAI_BASE_URL:
            client_options["base_url"] = settings.OPENAI_BASE_URL.rstrip("/")
        _ai_client = AsyncOpenAI(**client_options)
    context = await ai_catalog_context(session)
    system_prompt = ("Eres el asistente de atención al cliente de LXZ STORE. Responde en español, con claridad y máximo 800 caracteres. "
                     "Usa únicamente el catálogo y las reglas de esta instrucción. No inventes precios, stock, cuentas, pagos, claves ni duraciones. "
                     "Nunca apruebes recargas, entregues saldo, confirmes pagos ni reveles datos administrativos. Para pagos, comprobantes, claves, "
                     "errores no resueltos o datos desconocidos, indica que el cliente debe contactar soporte en https://t.me/Lxz_Modz. "
                     "Si el producto está marcado como no disponible todavía, dilo claramente. "
                     "Guía: el cliente puede abrir el catálogo para consultar productos; para recargar debe elegir país y monto, "
                     "en Perú verá PEN con Yape, Plin, Ligo o CCI, y en otros países puede ver USDC/USDT y redes disponibles. "
                     "Toda recarga requiere comprobante y revisión del administrador; nunca digas que un pago fue recibido o aprobado sin esa revisión.\n\nCATÁLOGO ACTUAL:\n" + context)
    models = [settings.OPENAI_MODEL]
    if settings.OPENAI_FALLBACK_MODEL and settings.OPENAI_FALLBACK_MODEL not in models:
        models.append(settings.OPENAI_FALLBACK_MODEL)
    answer = ""
    last_error = None
    for model in models:
        try:
            response = await asyncio.wait_for(
                _ai_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt[:1200]}],
                    max_completion_tokens=450,
                ),
                timeout=18,
            )
            answer = (response.choices[0].message.content or "").strip()
            if not answer:
                raise RuntimeError("La IA devolvió una respuesta vacía")
            break
        except (OpenAIError, TimeoutError, ValueError, RuntimeError) as exc:
            last_error = exc
            status_code = getattr(exc, "status_code", None)
            logger.warning("AI model failed: model=%s error_type=%s status=%s", model, type(exc).__name__, status_code)
    if answer:
        await message.answer("🤖 <b>Asistente LXZ</b>\n\n" + escape(answer[:3500]))
    else:
        status_code = getattr(last_error, "status_code", None)
        logger.error("AI customer response failed after %d model attempts: error_type=%s status=%s", len(models), type(last_error).__name__ if last_error else "unknown", status_code)
        if status_code in (401, 403):
            reason = "La configuración de la IA necesita revisión por el administrador."
        elif status_code == 429:
            reason = "La IA está temporalmente ocupada o alcanzó su cuota."
        else:
            reason = "El asistente está temporalmente fuera de servicio."
        await message.answer(f"🤖 {reason}\n\n📞 Soporte: {settings.SUPPORT_URL}")


def is_dueno(user: User | None) -> bool:
    return bool(user and user.role == UserRole.DUENO)


def is_admin(user: User | None) -> bool:
    return bool(user and user.role in (UserRole.ADMIN, UserRole.OWNER, UserRole.DUENO))


def is_staff(user: User | None) -> bool:
    return bool(user and user.role in (UserRole.ADMIN, UserRole.OWNER, UserRole.DUENO))


def is_owner(user: User | None) -> bool:
    # Solo DUEÑO tiene el panel de control total y puede gestionar rangos.
    return is_dueno(user)


def is_owner_role(user: User | None) -> bool:
    return bool(user and user.role in (UserRole.OWNER, UserRole.DUENO))


def can_manage_products(user: User | None) -> bool:
    return is_owner_role(user)



def balance_display(user: User) -> str:
    return "∞ USD (saldo infinito)" if is_dueno(user) else f"{m(user.balance)} USD"


def socio_discount_percent(user: User) -> Decimal:
    return settings.PARTNER_DISCOUNT_PERCENT if user.role == UserRole.SOCIO or user.is_partner else Decimal("0.00")


def premiun_discount_percent(user: User) -> Decimal:
    return settings.PREMIUN_DISCOUNT_PERCENT if user.role == UserRole.PREMIUN or active_premium(user) else Decimal("0.00")


def membership_discount_percent(user: User) -> Decimal:
    # Si alguien tiene más de un beneficio, se aplica el mayor y no se
    # encadenan descuentos accidentalmente sobre el mismo producto.
    return max(socio_discount_percent(user), premiun_discount_percent(user))


def can_deliver_keys(user: User | None) -> bool:
    return can_manage_products(user)


def now_text(value: datetime | None = None) -> str:
    return (value or utcnow()).strftime("%Y-%m-%d %H:%M UTC")


def active_premium(user: User) -> bool:
    return bool(user.is_premium and (not user.premium_until or user.premium_until > utcnow()))


async def has_approved_topup(session: AsyncSession, user_id: int) -> bool:
    return bool(await session.scalar(select(func.count(TopupRequest.id)).where(TopupRequest.user_id == user_id, TopupRequest.status == TopupStatus.APPROVED)))


FIRST_TOPUP_MINIMUM_USD = Decimal("10.00")
SUBSEQUENT_TOPUP_MINIMUM_USD = Decimal("3.00")


async def get_or_create_user(telegram_user, session: AsyncSession, current: User | None = None, start_arg: str | None = None) -> User:
    user = current or (await session.execute(select(User).where(User.telegram_id == telegram_user.id))).scalar_one_or_none()
    if user:
        user.username = telegram_user.username
        user.first_name = telegram_user.first_name or "Usuario"
        user.last_name = telegram_user.last_name
        user.last_activity = utcnow()
        if not user.rank_title:
            user.rank_title = "Cliente"
        if telegram_user.id == settings.OWNER_ID:
            user.role = UserRole.DUENO
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
    role = UserRole.DUENO if telegram_user.id == settings.OWNER_ID else (UserRole.ADMIN if telegram_user.id in settings.admin_ids else UserRole.USUARIO)
    user = User(telegram_id=telegram_user.id, username=telegram_user.username, first_name=telegram_user.first_name or "Usuario", last_name=telegram_user.last_name, role=role, referred_by=referred_by, rank_title="Cliente Nuevo")
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
        if "message is not modified" in str(exc).lower():
            await callback.answer()
            return
        # Una foto no puede convertirse en texto mediante edit_text. En ese caso
        # eliminamos la tarjeta anterior para no dejar mensajes duplicados.
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            pass
        await callback.message.answer(text, reply_markup=markup)
    await callback.answer()


async def ensure_auction_tables(session: AsyncSession) -> None:
    await session.run_sync(lambda conn: Base.metadata.create_all(conn, tables=[Auction.__table__, AuctionBid.__table__]))


async def log_event(session: AsyncSession, actor: int, action: str, target: str | None, result: str) -> None:
    session.add(AuditLog(actor_telegram_id=actor, action=action, target=target, result=result))


async def notify_staff(bot: Bot, text: str, markup=None) -> None:
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(admin_id, text, reply_markup=markup)
        except Exception:
            logger.exception("No se pudo notificar al administrador %s.", admin_id)
async def show_home(target: Message | CallbackQuery, user: User) -> None:
    admin_commands = ""
    if is_staff(user):
        admin_commands = "\n\n🔐 <b>COMANDOS STAFF</b>\n<code>/stock</code> · <code>/perfil</code>"
    if can_manage_products(user):
        admin_commands += "\n<code>/agregas</code> · <code>/actualizarstock</code> · <code>/key ID KEY</code>"
    if is_owner_role(user):
        admin_commands += "\n<code>/broadcast</code> · <code>/saldo ID CANTIDAD USD</code>"
    role_display = f"\n🗝 𝐏𝐞𝐫𝐦𝐢𝐬𝐨𝐬: {user.role.value} — 𝐀𝐂𝐂𝐄𝐒𝐒"
    benefit_display = "\n♾️ 𝐁𝐞𝐧𝐞𝐟𝐢𝐜𝐢𝐨: Saldo infinito" if is_dueno(user) else ""
    text = (f"❰ ʟxᴢ ꜱᴛᴏʀᴇ ʙᴇꜱᴛ — 𝐂𝐎𝐌𝐌𝐀𝐍𝐃 𝐂𝐄𝐍𝐓𝐄𝐑 ❱\n"
            f"💮 ʟxᴢ • 𝐍𝐞𝐨-𝐒𝐲𝐬𝐭𝐞𝐦 • 𝐍𝐞𝐭𝐰𝐨𝐫𝐤 💮\n\n"
            f"👤 𝐔𝐬𝐮𝐚𝐫𝐢𝐨: {name_of(user)} | <code>{user.telegram_id}</code>{role_display}\n"
            f"💰 𝐒𝐚𝐥𝐝𝐨: {balance_display(user)}{benefit_display}\n\n"
            f"🤖 ʟxᴢ ꜱᴛᴏʀᴇ ʙᴇꜱᴛ — 𝐎𝐍𝐋𝐈𝐍𝐄\n"
            f"⚡ 𝐕𝐞𝐥𝐨𝐜𝐢𝐝𝐚𝐝 • 🛡 𝐒𝐞𝐠𝐮𝐫𝐢𝐝𝐚𝐝 • 🎯 𝐏𝐫𝐞𝐜𝐢𝐬𝐢𝐨́𝐧\n\n"
            f"🔥 「 𝐂𝐨𝐧𝐭𝐫𝐨𝐥𝐚 𝐞𝐥 𝐬𝐢𝐬𝐭𝐞𝐦𝐚 」 🔥{admin_commands}")
    markup = main_menu(user.role, settings.OFFICIAL_CHANNEL_URL)
    try:
        if isinstance(target, CallbackQuery):
            await target.message.delete()
    except TelegramBadRequest:
        pass

    home_image = HOME_BANNER  # Default fallback cover
    if Path(home_image).is_file():
        if isinstance(target, CallbackQuery):
            await target.message.answer_photo(FSInputFile(home_image), caption=text, reply_markup=markup)
            await target.answer()
        else:
            await target.answer_photo(FSInputFile(home_image), caption=text, reply_markup=markup)
    else:
        if isinstance(target, CallbackQuery):
            await edit_or_answer(target, text, markup)
        else:
            await target.answer(text, reply_markup=markup)


LEGACY_CATEGORY_MAP = {
    "🤖 Android": "Android",
    "🍎 iOS / iPhone": "iOS",
    "🍎 iOS": "iOS",
    "💻 Windows / PC": "PC",
    "💻 PC": "PC",
    "🌐 Otros": "Otros",
}


async def activate_initial_inventory_once(session: AsyncSession) -> None:
    marker_key = "initial_inventory_all_products_stock_5_v3"
    if await session.get(StoreSetting, marker_key):
        return
    products = (await session.execute(select(Product))).scalars().all()
    for product in products:
        # La nueva activación universal solo inicializa productos sin ventas.
        # Así los productos vendidos no recuperan unidades en un reinicio.
        if product.sales_count == 0:
            product.stock = 5
            product.is_active = True
    session.add(StoreSetting(key=marker_key, value="all_products_stock_5"))


async def activate_new_catalog_products_once(session: AsyncSession) -> None:
    marker_key = "catalog_prices_drip_holo_proxy_monite_v1"
    if await session.get(StoreSetting, marker_key):
        return
    new_product_names = {"PANEL HOLO VIP", "PROXY DRIP"}
    products = (await session.execute(select(Product).where(Product.name.in_(new_product_names)))).scalars().all()
    for product in products:
        if product.sales_count == 0:
            product.stock = 5
            product.is_active = True
    session.add(StoreSetting(key=marker_key, value="new_catalog_products_stock_5"))


async def seed_initial_products(session: AsyncSession) -> None:
    for legacy, current in LEGACY_CATEGORY_MAP.items():
        await session.execute(update(Product).where(Product.category == legacy).values(category=current))
    for category, names in INITIAL_PRODUCTS.items():
        for name in names:
            existing = (await session.execute(select(Product).where(Product.name == name))).scalar_one_or_none()
            image_path = image_for_product(name)
            price_variants = PRICE_CATALOG.get(name)
            description = price_variants_text(price_variants) if price_variants else "Producto agregado; configura precio, stock y entrega desde /agregas."
            base_price = money(price_variants[0][1]) if price_variants else Decimal("0.00")
            if not existing:
                session.add(Product(category=category, name=name, description=description, price=base_price, stock=0, image_file_id=image_path, is_active=False))
            else:
                existing.category = category
                if price_variants:
                    existing.description = description
                    existing.price = base_price
                if image_path and not existing.image_file_id:
                    existing.image_file_id = image_path
    await session.flush()
    await activate_initial_inventory_once(session)
    await activate_new_catalog_products_once(session)
    await session.commit()


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, current_user: User | None = None, state: FSMContext | None = None):
    if state:
        await state.clear()
    args = (message.text or "").split(maxsplit=1)
    user = await get_or_create_user(message.from_user, session, current_user, args[1] if len(args) > 1 else None)
    await show_home(message, user)


@router.message(Command("id", ignore_case=True))
async def cmd_id(message: Message, session: AsyncSession, current_user: User | None = None):
    user = await event_user(message, session, current_user)
    if user: await message.answer(f"🆔 Tu ID de Telegram es: <code>{user.telegram_id}</code>\nCompártelo solo con el equipo cuando necesites soporte.")


@router.message(Command("rangos", ignore_case=True))
async def cmd_rangos(message: Message):
    await message.answer("❰ ʟxᴢ ꜱᴛᴏʀᴇ ʙᴇꜱᴛ — 𝐑𝐎𝐋𝐄𝐒 𝐘 𝐑𝐀𝐍𝐆𝐎𝐒 ❱\n\n"
                         "🏆 <b>DUEÑO:</b> único propietario; saldo infinito y panel DUEÑO completo.\n"
                         "👑 <b>OWNER:</b> panel OWNER reducido, sin gestión de rangos ni configuración total.\n"
                         "🔐 <b>ADMIN:</b> panel ADMIN operativo, con menos opciones que OWNER y DUEÑO.\n"
                         "🤝 <b>SOCIO:</b> 20% de descuento automático en compras.\n"
                         "💎 <b>PREMIUN:</b> 10% de descuento automático en compras.\n"
                         "👤 <b>USUARIO:</b> compras, recargas y funciones normales.")


@router.message(Command("miscompras", ignore_case=True))
async def cmd_miscompras(message: Message, session: AsyncSession, current_user: User | None = None):
    user = await event_user(message, session, current_user)
    if not user: return
    purchases = (await session.execute(select(Purchase).where(Purchase.user_id == user.id).order_by(Purchase.created_at.desc()).limit(10))).scalars().all()
    if not purchases:
        await message.answer("🛒 Todavía no tienes compras registradas. Abre el catálogo para comenzar."); return
    lines = ["🛒 <b>MIS COMPRAS RECIENTES</b>", ""]
    for purchase in purchases:
        lines.append(f"• <code>{purchase.order_id}</code> · {escape(purchase.product_name)} · {m(purchase.price)} USD · {purchase.status.value} · {now_text(purchase.created_at)}")
    await message.answer("\n".join(lines))


@router.message(Command("comandos", ignore_case=True))
async def cmd_comandos(message: Message, session: AsyncSession, current_user: User | None = None):
    user = await event_user(message, session, current_user)
    if not user: return
    text = ("❰ ʟxᴢ ꜱᴛᴏʀᴇ ʙᴇꜱᴛ — 𝐂𝐎𝐌𝐌𝐀𝐍𝐃 𝐋𝐈𝐒𝐓 ❱\n\n"
            "<code>/start</code> — Menú principal\n"
            "<code>/perfil</code> — Consultar saldo y beneficios\n"
            "<code>/miscompras</code> — Historial de compras\n"
            "<code>/rangos</code> — Ver información de roles")
    if is_staff(user):
        text += "\n\n🔐 <b>𝐂𝐎𝐌𝐀𝐍𝐃𝐎𝐒 𝐒𝐓𝐀𝐅𝐅</b>\n<code>/stock</code> — Consultar inventario"
    if can_manage_products(user):
        text += "\n<code>/agregas</code> — Crear un nuevo producto\n<code>/actualizarstock</code> — Modificar inventario\n<code>/key ID KEY</code> — Entregar una Key manualmente"
    if is_owner_role(user):
        text += "\n<code>/estadisticas</code> — Métricas de la tienda"
    if is_owner(user):
        text += "\n<code>/broadcast</code> — Difusión global\n<code>/saldo ID CANTIDAD USD</code> — Agregar o quitar saldo\n<code>/rol ID ROL</code> — Cambiar rango\n<code>/ban ID MOTIVO</code> — Bloquear acceso\n<code>/desban ID</code> — Restaurar acceso"
    await message.answer(text)


@router.message(Command("rol", ignore_case=True))
async def cmd_rol(message: Message, session: AsyncSession, current_user: User | None = None):
    actor = await event_user(message, session, current_user)
    if not is_owner(actor):         await message.answer("❌ Solo DUEÑO puede cambiar roles."); return
    parts = (message.text or "").split()
    aliases = {
        "dueño": UserRole.DUENO, "dueno": UserRole.DUENO,
        "owner": UserRole.OWNER, "admin": UserRole.ADMIN,
        "socio": UserRole.SOCIO, "premiun": UserRole.PREMIUN,
        "premium": UserRole.PREMIUN, "usuario": UserRole.USUARIO,
    }
    if len(parts) != 3 or parts[2].lower() not in aliases:
        await message.answer("Uso: /rol ID ROL\nRoles: DUEÑO, OWNER, ADMIN, SOCIO, PREMIUN, USUARIO"); return
    try: target_id = int(parts[1])
    except ValueError: await message.answer("❌ ID inválido."); return
    if target_id == settings.OWNER_ID: await message.answer("❌ El Owner está protegido."); return
    target = (await session.execute(select(User).where(User.telegram_id == target_id).with_for_update())).scalar_one_or_none()
    if not target: await message.answer("❌ Usuario no encontrado."); return
    selected_role = aliases[parts[2].lower()]
    if selected_role == UserRole.DUENO:
        await message.answer("❌ DUEÑO solo puede ser el usuario configurado en OWNER_ID."); return
    target.role = selected_role
    await log_event(session, actor.telegram_id, "role_change", str(target_id), target.role.value)
    await session.commit(); await message.answer(f"✅ Rol actualizado.\n\n👤 {name_of(target)}\n🎖️ Rol: {target.role.value}")


@router.message(Command("ban", ignore_case=True))
async def cmd_ban(message: Message, session: AsyncSession, current_user: User | None = None):
    actor = await event_user(message, session, current_user)
    if not is_admin(actor): await message.answer("❌ Solo Administradores u Owner."); return
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 2:
        await message.answer("Uso: /ban ID MOTIVO"); return
    try: target_id = int(parts[1])
    except ValueError: await message.answer("❌ ID inválido."); return
    if target_id == settings.OWNER_ID: await message.answer("❌ El Owner está protegido."); return
    target = (await session.execute(select(User).where(User.telegram_id == target_id).with_for_update())).scalar_one_or_none()
    if not target: await message.answer("❌ Usuario no encontrado."); return
    if target.role in (UserRole.ADMIN, UserRole.OWNER) and not is_owner(actor): await message.answer("❌ Solo DUEÑO puede restringir a un Administrador u Owner."); return
    target.is_banned = True; target.ban_reason = parts[2].strip() if len(parts) == 3 else "Sin motivo especificado"
    await log_event(session, actor.telegram_id, "user_ban_permanent", str(target_id), target.ban_reason)
    await session.commit()
    await message.answer(f"✅ Baneo permanente aplicado a {name_of(target)}.\n\nEl usuario no podrá usar comandos, menú ni botones hasta un /desban explícito.\n📞 Soporte: {settings.SUPPORT_URL}")


@router.message(Command("desban", ignore_case=True))
async def cmd_desban(message: Message, session: AsyncSession, current_user: User | None = None):
    actor = await event_user(message, session, current_user)
    if not is_admin(actor): await message.answer("❌ Solo Administradores u Owner."); return
    parts = (message.text or "").split()
    if len(parts) != 2:
        await message.answer("Uso: /desban ID"); return
    try: target_id = int(parts[1])
    except ValueError: await message.answer("❌ ID inválido."); return
    target = (await session.execute(select(User).where(User.telegram_id == target_id).with_for_update())).scalar_one_or_none()
    if not target: await message.answer("❌ Usuario no encontrado."); return
    target.is_banned = False; target.ban_reason = None
    await log_event(session, actor.telegram_id, "user_unban", str(target_id), "restored")
    await session.commit(); await message.answer(f"✅ Usuario habilitado: {name_of(target)}")


@router.message(Command("estadisticas", ignore_case=True))
async def cmd_estadisticas(message: Message, session: AsyncSession, current_user: User | None = None):
    actor = await event_user(message, session, current_user)
    if not is_admin(actor): await message.answer("❌ Solo Administradores u Owner."); return
    users = await session.scalar(select(func.count(User.id))) or 0
    active_users = await session.scalar(select(func.count(User.id)).where(User.is_banned.is_(False))) or 0
    products = await session.scalar(select(func.count(Product.id))) or 0
    active_products = await session.scalar(select(func.count(Product.id)).where(Product.is_active.is_(True), Product.stock > 0)) or 0
    purchases = await session.scalar(select(func.count(Purchase.id))) or 0
    topups = await session.scalar(select(func.count(TopupRequest.id)).where(TopupRequest.status == TopupStatus.APPROVED)) or 0
    await message.answer(f"📊 <b>ESTADÍSTICAS</b>\n\n👥 Usuarios: {users}\n🟢 Usuarios activos: {active_users}\n📦 Productos: {products}\n🛒 Productos en venta: {active_products}\n💳 Compras: {purchases}\n💰 Recargas aprobadas: {topups}")


@router.message(Command("agregas"))
async def cmd_agregas(message: Message, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    actor = await event_user(message, session, current_user)
    if not can_manage_products(actor):
        await message.answer("❌ Solo OWNER o DUEÑO pueden crear productos.")
        return
    await state.clear()
    await state.set_state(ProductFlow.name)
    await message.answer("➕ <b>NUEVO PRODUCTO</b>\n\nEscribe el nombre del producto o APK:")


@router.message(Command("perfil"))
async def cmd_perfil(message: Message, session: AsyncSession, current_user: User | None = None):
    user = await event_user(message, session, current_user)
    if not user: return
    role_display = f"\n🎖️ <b>Rango:</b> {user.role.value}"
    text = (f"👤 <b>TU PERFIL</b>\n\n"
            f"🆔 <b>ID:</b> <code>{user.telegram_id}</code>{role_display}\n"
            f"💰 <b>Saldo:</b> {balance_display(user)}\n"
            f"🛒 <b>Compras realizadas:</b> {user.purchases_count}\n"
            f"💸 <b>Total gastado:</b> {m(user.total_spent)}\n"
            f"💎 <b>PREMIUN:</b> {'Sí · 10% OFF' if user.role == UserRole.PREMIUN or active_premium(user) else 'No'}\n\n"
            f"Usa el botón de <i>Mi Perfil / Historial</i> en el menú principal para ver tus últimas compras y Keys entregadas.")
    await message.answer(text)

@router.message(Command("stock"))
async def cmd_stock(message: Message, session: AsyncSession, current_user: User | None = None):
    user = await event_user(message, session, current_user)
    products = (await session.execute(select(Product).order_by(Product.category, Product.name))).scalars().all()
    visible = products if is_admin(user) else [p for p in products if p.is_active]
    lines = ["📦 <b>INVENTARIO</b>", ""]
    for category in CATEGORIES:
        group = [p for p in visible if p.category == category]
        if group:
            lines.append(CATEGORY_LABELS.get(category, category))
            lines.extend(f"• {p.name} — stock: {p.stock} — {'activo' if p.is_active else 'pendiente'}" for p in group)
            lines.append("")
    await message.answer("\n".join(lines) if len(lines) > 2 else "📦 No hay productos activos en el inventario.")


@router.message(Command("actualizarstock"))
async def cmd_update_stock(message: Message, session: AsyncSession, current_user: User | None = None):
    actor = await event_user(message, session, current_user)
    if not can_manage_products(actor):
        await message.answer("❌ Solo OWNER o DUEÑO pueden modificar stock.")
        return
    parts = (message.text or "").split()
    if len(parts) < 3:
        await message.answer("Uso: /actualizarstock Nombre del producto Cantidad\nEjemplo: /actualizarstock DRIP CLIENT 10")
        return
    try:
        quantity = int(parts[-1])
    except ValueError:
        await message.answer("❌ La cantidad debe ser un número entero.")
        return
    if quantity < 0:
        await message.answer("❌ El stock no puede ser negativo.")
        return
    product_name = " ".join(parts[1:-1]).strip()
    product = (await session.execute(select(Product).where(Product.name.ilike(product_name)).with_for_update())).scalar_one_or_none()
    if not product:
        await message.answer("❌ Producto no encontrado. Usa /stock para consultar los nombres exactos.")
        return
    product.stock = quantity
    product.is_active = bool(quantity > 0 and product.price > 0)
    await log_event(session, actor.telegram_id, "stock_update", str(product.id), str(quantity))
    await session.commit()
    await message.answer(f"✅ Stock actualizado.\n\n📦 {product.name}\n📊 Nuevo stock: {product.stock}\n🟢 Estado: {'activo' if product.is_active else 'pendiente de precio'}")


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    actor = await event_user(message, session, current_user)
    if not is_owner_role(actor):
        await message.answer("❌ Solo OWNER o DUEÑO pueden hacer difusión.")
        return
    await state.set_state(BroadcastFlow.message)
    await message.answer("📢 Envía ahora el mensaje, foto, vídeo, documento o sticker que deseas difundir. Usa /start para cancelar.")


@router.message(Command("saldo", ignore_case=True))
async def cmd_saldo(message: Message, bot: Bot, session: AsyncSession, current_user: User | None = None):
    actor = await event_user(message, session, current_user)
    if not is_owner_role(actor):
        await message.answer("❌ Permisos insuficientes. Solo OWNER o DUEÑO pueden dar saldo.")
        return
    parts = (message.text or "").split()
    if len(parts) != 4 or parts[3].upper() != "USD":
        await message.answer("Uso: /saldo ID_TELEGRAM CANTIDAD USD\nEjemplo: /saldo 123456789 10 USD")
        return
    try:
        telegram_id = int(parts[1])
        amount = money(parts[2])
    except (ValueError, InvalidOperation):
        await message.answer("❌ El ID debe ser entero y la cantidad debe ser numérica.")
        return
    if amount <= 0:
        await message.answer("❌ La cantidad debe ser mayor que cero.")
        return
    target = (await session.execute(select(User).where(User.telegram_id == telegram_id).with_for_update())).scalar_one_or_none()
    if not target:
        await message.answer("❌ Usuario no encontrado. Debe haber usado /start previamente.")
        return
    if is_dueno(target):
        await message.answer("❌ El saldo del DUEÑO es infinito y no puede modificarse.")
        return
    target.balance = money(target.balance) + amount
    session.add(BalanceTransaction(user_id=target.id, kind=BalanceTransactionType.CREDIT, amount=amount, balance_after=target.balance, reference=str(actor.telegram_id), note="/saldo USD"))
    await log_event(session, actor.telegram_id, "balance_change", str(target.telegram_id), f"+{amount}")
    await session.commit()
    await message.answer(f"✅ <b>SALDO ENTREGADO</b>\n\n👤 {name_of(target)}\n🆔 {target.telegram_id}\n➕ Movimiento: +{m(amount)} USD\n💰 Nuevo saldo: {m(target.balance)} USD")
    if target.telegram_id != actor.telegram_id:
        try:
            await bot.send_message(target.telegram_id, f"💰 <b>SALDO USD RECIBIDO</b>\n\nSe agregaron: <b>+{m(amount)} USD</b>\nSaldo actual: <b>{m(target.balance)} USD</b>")
        except Exception:
            # El saldo ya fue confirmado en la base de datos; un bloqueo o fallo de Telegram no lo revierte.
            logger.exception("No se pudo notificar al usuario %s sobre su saldo USD.", target.telegram_id)


@router.message(Command("key", ignore_case=True))
async def cmd_key(message: Message, bot: Bot, session: AsyncSession, current_user: User | None = None):
    actor = await event_user(message, session, current_user)
    if not can_deliver_keys(actor):
        await message.answer("❌ Solo OWNER o DUEÑO pueden entregar Keys.")
        return
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) != 3 or not parts[2].strip():
        await message.answer("Uso: /key ID_TELEGRAM LA_KEY\nEjemplo: /key 123456789 29387429209")
        return
    try:
        telegram_id = int(parts[1])
    except ValueError:
        await message.answer("❌ El ID de Telegram debe ser un número entero.")
        return
    key_value = parts[2].strip()
    if len(key_value) > 4000:
        await message.answer("❌ La Key es demasiado larga.")
        return
    target = (await session.execute(select(User).where(User.telegram_id == telegram_id).with_for_update())).scalar_one_or_none()
    if not target:
        await message.answer("❌ Usuario no encontrado. Debe haber usado /start previamente.")
        return
    purchase = (await session.execute(select(Purchase).where(Purchase.user_id == target.id, Purchase.status == PurchaseStatus.PAID).order_by(desc(Purchase.created_at), desc(Purchase.id)).limit(1).with_for_update())).scalar_one_or_none()
    if not purchase:
        await message.answer("❌ Este usuario no tiene una compra pagada registrada para asociar la Key.")
        return
    existing_delivery = (await session.execute(select(KeyDelivery).where(KeyDelivery.purchase_id == purchase.id).limit(1))).scalar_one_or_none()
    if existing_delivery:
        await message.answer(f"❌ La compra <code>{purchase.order_id}</code> ya tiene una Key entregada.")
        return
    duration = purchase_duration(purchase)
    session.add(KeyDelivery(user_id=target.id, purchase_id=purchase.id, key_value=key_value, duration=duration, delivered_by=actor.telegram_id))
    await log_event(session, actor.telegram_id, "key_delivery", str(target.telegram_id), f"{purchase.order_id} · {duration}")
    await session.commit()
    safe_key = escape(key_value)
    admin_text = f"✅ <b>KEY ENTREGADA</b>\n\n👤 Usuario: {name_of(target)}\n🆔 ID: <code>{target.telegram_id}</code>\n📦 Producto: {purchase.product_name}\n🔑 <b>KEY:</b> <code>{safe_key}</code>\n⏱️ <b>DURACIÓN:</b> {escape(duration)}"
    await message.answer(admin_text)
    if target.telegram_id != actor.telegram_id:
        try:
            await bot.send_message(target.telegram_id, f"✅ <b>KEY ENTREGADA</b>\n\n📦 Producto: {purchase.product_name}\n🔑 <b>KEY:</b> <code>{safe_key}</code>\n⏱️ <b>DURACIÓN:</b> {escape(duration)}\n\n🙏 GRACIAS POR TU COMPRA Y TU CONFIANZA EN LXZ STORE BEST")
        except Exception:
            logger.exception("No se pudo notificar al usuario %s sobre la Key entregada.", target.telegram_id)


@router.callback_query(F.data == "menu:home")
async def menu_home(callback: CallbackQuery, session: AsyncSession, current_user: User | None = None, state: FSMContext | None = None):
    if state:
        await state.clear()
    user = await event_user(callback, session, current_user)
    if user:
        await show_home(callback, user)


@router.callback_query(F.data == "owner:auctions")
async def owner_auctions(callback: CallbackQuery, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    await ensure_auction_tables(session)
    actor = await check_admin(callback, session, current_user)
    if not actor or not is_dueno(actor):
        await callback.answer("Solo el DUEÑO puede administrar subastas.", show_alert=True)
        return
    auctions = (await session.execute(select(Auction).where(Auction.status == "active").order_by(Auction.ends_at))).scalars().all()
    lines = ["🔨 <b>ADMINISTRACIÓN DE SUBASTAS</b>", ""]
    for auction in auctions:
        if auction.ends_at <= utcnow():
            auction.status = "closed"
            continue
        lines.append(f"• #{auction.id} · {escape(auction.product_name)} · {m(auction.current_price)} USD · termina {now_text(auction.ends_at)}")
    if len(lines) == 2:
        lines.append("No hay subastas activas.")
    await session.commit()
    await state.set_state(AuctionFlow.product_name)
    await edit_or_answer(callback, "\n".join(lines) + "\n\nEscribe el nombre del producto u objeto para crear una nueva subasta, o /start para cancelar.", kb([[("➕ Crear subasta", "owner:auction:create", None)], [("🏠 Inicio", "menu:home", None)]]))

@router.callback_query(F.data == "owner:auction:create")
async def owner_auction_create(callback: CallbackQuery, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    actor = await check_admin(callback, session, current_user)
    if not actor or not is_dueno(actor):
        await callback.answer("Solo el DUEÑO puede crear subastas.", show_alert=True)
        return
    await state.set_state(AuctionFlow.product_name)
    await edit_or_answer(callback, "🔨 <b>NUEVA SUBASTA</b>\n\nEscribe el nombre del producto u objeto.", None)

@router.message(AuctionFlow.product_name, F.text)
async def auction_product_name(message: Message, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    actor = await event_user(message, session, current_user)
    if not is_dueno(actor):
        await state.clear(); return
    name = message.text.strip()
    if not name or len(name) > 160:
        await message.answer("❌ Escribe un nombre válido de hasta 160 caracteres.")
        return
    await state.update_data(auction_product_name=name)
    await state.set_state(AuctionFlow.initial_price)
    await message.answer("💰 Escribe el precio inicial en USD. Ejemplo: 10")

@router.message(AuctionFlow.initial_price, F.text)
async def auction_initial_price(message: Message, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    actor = await event_user(message, session, current_user)
    if not is_dueno(actor):
        await state.clear(); return
    try:
        price = money(message.text.strip())
    except (InvalidOperation, ValueError):
        price = Decimal("0.00")
    if price <= 0:
        await message.answer("❌ El precio inicial debe ser mayor que 0 USD.")
        return
    await state.update_data(auction_initial_price=str(price))
    await state.set_state(AuctionFlow.duration)
    await message.answer("⏱️ Escribe la duración en minutos. Ejemplo: 60")

@router.message(AuctionFlow.duration, F.text)
async def auction_duration(message: Message, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    actor = await event_user(message, session, current_user)
    if not is_dueno(actor):
        await state.clear(); return
    try:
        duration = int(message.text.strip())
    except ValueError:
        duration = 0
    if duration < 1 or duration > 10080:
        await message.answer("❌ La duración debe estar entre 1 y 10080 minutos.")
        return
    await state.update_data(auction_duration=duration)
    await state.set_state(AuctionFlow.increment)
    await message.answer("📈 Escribe el incremento por puja entre 2 y 5 USD. Ejemplo: 2")

@router.message(AuctionFlow.increment, F.text)
async def auction_increment(message: Message, bot: Bot, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    actor = await event_user(message, session, current_user)
    if not is_dueno(actor):
        await state.clear(); return
    increment = money(message.text.strip())
    if increment < Decimal("2.00") or increment > Decimal("5.00"):
        await message.answer("❌ El incremento debe estar entre 2 y 5 USD.")
        return
    data = await state.get_data()
    initial = money(data["auction_initial_price"])
    auction = Auction(product_name=data["auction_product_name"], initial_price=initial, current_price=initial, increment=increment, duration_minutes=int(data["auction_duration"]), ends_at=utcnow() + timedelta(minutes=int(data["auction_duration"])), created_by=actor.telegram_id)
    session.add(auction)
    await session.commit()
    await session.refresh(auction)
    await state.clear()
    notification = ("🔨 <b>NUEVA SUBASTA DISPONIBLE</b>\n\n"
                    f"📦 Producto: <b>{escape(auction.product_name)}</b>\n"
                    f"💰 Precio inicial: <b>{m(auction.initial_price)} USD</b>\n"
                    f"📈 Incremento por puja: <b>{m(auction.increment)} USD</b>\n"
                    f"⏱️ Duración: <b>{auction.duration_minutes} minutos</b>\n\n"
                    "Entra a Subastas para participar.")
    users = (await session.execute(select(User.telegram_id).where(User.is_banned.is_(False)))).scalars().all()
    sent = failed = 0
    for telegram_id in users:
        try:
            await bot.send_message(telegram_id, notification, reply_markup=kb([[("🔨 Ver subasta", f"auction:view:{auction.id}", None)]]))
            sent += 1
        except (TelegramForbiddenError, TelegramBadRequest):
            failed += 1
        await asyncio.sleep(settings.BROADCAST_DELAY)
    await log_event(session, actor.telegram_id, "auction_create", str(auction.id), f"sent={sent};failed={failed}")
    await session.commit()
    await message.answer(f"✅ <b>SUBASTA PUBLICADA</b>\n\n{notification}\n\n📢 Notificaciones enviadas: {sent}\n⚠️ Fallidas: {failed}", reply_markup=nav(True, "owner:auctions"))

@router.callback_query(F.data == "menu:auctions")
async def menu_auctions(callback: CallbackQuery, session: AsyncSession):
    await ensure_auction_tables(session)
    auctions = (await session.execute(select(Auction).where(Auction.status == "active").order_by(Auction.ends_at))).scalars().all()
    rows = []
    lines = ["❰ ʟxᴢ ꜱᴛᴏʀᴇ ʙᴇꜱᴛ — 𝐀𝐔𝐂𝐓𝐈𝐎𝐍 𝐂𝐄𝐍𝐓𝐄𝐑 ❱", "", "🔨 <b>SUBASTAS ACTIVAS</b>", ""]
    for auction in auctions:
        if auction.ends_at <= utcnow():
            auction.status = "closed"
            continue
        lines.append(f"📦 <b>{escape(auction.product_name)}</b> · Puja actual: <b>{m(auction.current_price)} USD</b> · termina: {now_text(auction.ends_at)}")
        rows.append([(f"🔨 Pujar · +{m(auction.increment)}", f"auction:view:{auction.id}", None)])
    if not rows:
        lines.append("📭 Actualmente no hay subastas activas.")
    rows.append([("🏠 Inicio", "menu:home", None)])
    await session.commit()
    await edit_or_answer(callback, "\n".join(lines), kb(rows))

@router.callback_query(F.data.startswith("auction:view:"))
async def auction_view(callback: CallbackQuery, session: AsyncSession, current_user: User | None = None):
    await ensure_auction_tables(session)
    try:
        auction_id = int(callback.data.rsplit(":", 1)[1])
    except ValueError:
        await callback.answer("Subasta inválida.", show_alert=True); return
    auction = (await session.execute(select(Auction).where(Auction.id == auction_id))).scalar_one_or_none()
    if not auction or auction.status != "active" or auction.ends_at <= utcnow():
        if auction: auction.status = "closed"; await session.commit()
        await callback.answer("Esta subasta ya terminó.", show_alert=True); return
    await edit_or_answer(callback, f"🔨 <b>SUBASTA #{auction.id}</b>\n\n📦 Producto: <b>{escape(auction.product_name)}</b>\n💰 Precio inicial: <b>{m(auction.initial_price)} USD</b>\n🔥 Puja actual: <b>{m(auction.current_price)} USD</b>\n📈 Tu próxima puja: <b>{m(auction.current_price + auction.increment)} USD</b>\n⏱️ Termina: <b>{now_text(auction.ends_at)}</b>", kb([[(f"✅ Pujar +{m(auction.increment)}", f"auction:bid:{auction.id}", None)], [("⬅️ Subastas", "menu:auctions", None), ("🏠 Inicio", "menu:home", None)]]))

@router.callback_query(F.data.startswith("auction:bid:"))
async def auction_bid(callback: CallbackQuery, session: AsyncSession, current_user: User | None = None):
    await ensure_auction_tables(session)
    bidder = await event_user(callback, session, current_user)
    if not bidder or bidder.is_banned:
        await callback.answer("No tienes acceso a las subastas.", show_alert=True); return
    try:
        auction_id = int(callback.data.rsplit(":", 1)[1])
    except ValueError:
        await callback.answer("Subasta inválida.", show_alert=True); return
    auction = (await session.execute(select(Auction).where(Auction.id == auction_id).with_for_update())).scalar_one_or_none()
    if not auction or auction.status != "active" or auction.ends_at <= utcnow():
        if auction: auction.status = "closed"; await session.commit()
        await callback.answer("Esta subasta ya terminó.", show_alert=True); return
    amount = money(auction.current_price) + money(auction.increment)
    if not is_dueno(bidder) and money(bidder.balance) < amount:
        await callback.answer(f"Necesitas {m(amount)} USD de saldo para pujar.", show_alert=True); return
    if not is_dueno(bidder):
        bidder.balance = money(bidder.balance) - amount
        session.add(BalanceTransaction(user_id=bidder.id, kind=BalanceTransactionType.DEBIT, amount=amount, balance_after=bidder.balance, reference=f"auction:{auction.id}", note="Puja de subasta"))
    auction.current_price = amount
    auction.winner_id = bidder.telegram_id
    session.add(AuctionBid(auction_id=auction.id, bidder_id=bidder.telegram_id, amount=amount))
    await log_event(session, bidder.telegram_id, "auction_bid", str(auction.id), str(amount))
    await session.commit()
    await callback.answer(f"Puja registrada: {m(amount)} USD")
    await edit_or_answer(callback, f"✅ <b>PUJA REGISTRADA</b>\n\n📦 {escape(auction.product_name)}\n🔥 Nueva puja actual: <b>{m(amount)} USD</b>\n📈 Próxima puja: <b>{m(amount + auction.increment)} USD</b>\n⏱️ Termina: <b>{now_text(auction.ends_at)}</b>", kb([[(f"✅ Pujar +{m(auction.increment)}", f"auction:bid:{auction.id}", None)], [("⬅️ Subastas", "menu:auctions", None), ("🏠 Inicio", "menu:home", None)]]))

@router.callback_query(F.data == "menu:catalog")
async def menu_catalog(callback: CallbackQuery, session: AsyncSession):
    await seed_initial_products(session)
    db_categories = (await session.execute(select(Product.category).distinct())).scalars().all()
    values = list(dict.fromkeys(CATEGORIES + [x for x in db_categories if x not in CATEGORIES]))
    text = "🛒 <b>CATEGORÍAS DISPONIBLES</b> 🎮\nSelecciona la categoría de tu interés, bb:"
    markup = categories(values)
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    home_image = HOME_BANNER
    if Path(home_image).is_file():
        await callback.message.answer_photo(FSInputFile(home_image), caption=text, reply_markup=markup)
        await callback.answer()
    else:
        await edit_or_answer(callback, text, markup)


async def render_products(callback: CallbackQuery, session: AsyncSession, category: str, page: int):
    query = select(Product).where(Product.category == category).order_by(Product.id.desc())
    all_items = (await session.execute(query)).scalars().all()
    pages = max(1, math.ceil(len(all_items) / PAGE_SIZE))
    page = max(0, min(page, pages - 1))
    items = all_items[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
    if not items:
        text = f"📁 <b>{CATEGORY_LABELS.get(category, category)}</b>\n\nNo hay productos disponibles en esta categoría."
    else:
        text = f"📁 <b>{CATEGORY_LABELS.get(category, category)}</b>\n\n📦 <b>PRODUCTOS DISPONIBLES</b> 🔥\nSelecciona lo que te vas a llevar:"
    markup = product_list(items, page, pages, category)
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    cat_image = "assets/proyecto_holograma_vip.jpg" if category == "Android" else ("assets/proxy_potatso_ios.jpg" if category == "iOS" else "assets/br_mods_pc.jpg")
    if Path(cat_image).is_file():
        await callback.message.answer_photo(FSInputFile(cat_image), caption=text, reply_markup=markup)
        await callback.answer()
    else:
        await edit_or_answer(callback, text, markup)


@router.callback_query(F.data.startswith("cat:"))
async def catalog_category(callback: CallbackQuery, session: AsyncSession):
    await render_products(callback, session, callback.data[4:], 0)


@router.callback_query(F.data.startswith("products:"))
async def catalog_page(callback: CallbackQuery, session: AsyncSession):
    _, category, page = callback.data.split(":", 2)
    await render_products(callback, session, category, int(page))


@router.callback_query(F.data.regexp(r"^product:\d+$"))
async def product_info(callback: CallbackQuery, session: AsyncSession):
    product = (await session.execute(select(Product).where(Product.id == int(callback.data.split(":")[1])))).scalar_one_or_none()
    if not product:
        await callback.answer("Producto no encontrado.", show_alert=True)
        return

    variant_options = parse_variants(product.description)
    variants = [(name, m(price)) for name, price in variant_options]
    can_buy = product.is_active and product.stock > 0 and (bool(variant_options) or product.price > 0)

    if variants:
        text = f"📦 <b>{product.name}</b> 📥\n\n⏱️ <b>SELECCIONA LA DURACIÓN DE TU LICENCIA:</b>"
    else:
        stock = "Agotado" if product.stock <= 0 else str(product.stock)
        display_status = "Disponible" if can_buy else ("Agotado" if product.is_active and product.price > 0 else "Pendiente de configuración")
        text = f"📦 <b>{product.name}</b>\n\n📝 {product.description or 'Sin descripción.'}\n💵 Precio: <b>{m(product.price)}</b>\n📊 Stock: {stock}\n🟢 Estado: {display_status}"

    markup = product_detail(product.id, f"cat:{product.category}", can_buy, variants)
    if product.image_file_id:
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            pass
        image_obj = FSInputFile(product.image_file_id) if Path(product.image_file_id).is_file() else product.image_file_id
        await callback.message.answer_photo(image_obj, caption=text, reply_markup=markup)
        await callback.answer()
    else:
        await edit_or_answer(callback, text, markup)


@router.callback_query(F.data.startswith("buy:"))
async def buy_preview(callback: CallbackQuery, session: AsyncSession, current_user: User | None = None, state: FSMContext | None = None):
    user = await event_user(callback, session, current_user)
    product = (await session.execute(select(Product).where(Product.id == int(callback.data.split(":")[1]), Product.is_active.is_(True)))).scalar_one_or_none()
    if not user or not product or product.stock <= 0:
        await callback.answer("Producto agotado o no disponible.", show_alert=True)
        return
    parts = callback.data.split(":", 2)
    variant = parts[2] if len(parts) > 2 else "default"
    price = selected_price(product, variant)
    if price is None:
        await callback.answer("Duración o precio no disponible.", show_alert=True)
        return
    data = await state.get_data() if state else {}
    total = price
    partner_line = ""
    member_percent = membership_discount_percent(user)
    member_discount = money(price * member_percent / Decimal(100)) if member_percent else Decimal("0.00")
    if member_discount:
        total -= member_discount
        label = "SOCIO" if member_percent == settings.PARTNER_DISCOUNT_PERCENT else "PREMIUN"
        partner_line = f"\n🎁 Descuento {label}: -{m(member_discount)}"
    coupon_line = ""
    coupon_code = data.get("coupon_code")
    if coupon_code:
        coupon = (await session.execute(select(Coupon).where(Coupon.code == coupon_code, Coupon.is_active.is_(True)))).scalar_one_or_none()
        discount = coupon_discount(coupon, total, user) if coupon else Decimal("0.00")
        if discount:
            total -= discount
            coupon_line = f"\n🎟️ Descuento ({coupon_code}): -{m(discount)}"
    product_label = f"{product.name} ({variant})" if variant != "default" else product.name
    text = f"🛒 <b>CONFIRMAR COMPRA</b>\n\n📦 Producto: {product_label}\n💵 Precio: {m(price)}{partner_line}{coupon_line}\n💳 Total: <b>{m(total)}</b>\n📊 Stock: {product.stock}\n💰 Saldo disponible: {balance_display(user)}\n💰 Saldo después: {balance_display(user) if is_dueno(user) else m(money(user.balance) - total)}"
    if not is_dueno(user) and money(user.balance) < total:
        await edit_or_answer(callback, text + "\n\n❌ Saldo insuficiente.", confirm("menu:balance", f"product:{product.id}"))
    else:
        await edit_or_answer(callback, text, confirm(f"buyconfirm:{product.id}:{variant}", f"product:{product.id}"))


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
    parts = callback.data.split(":")
    product_id = int(parts[1])
    variant = parts[2] if len(parts) > 2 else "default"
    try:
        user = (await session.execute(select(User).where(User.telegram_id == user.telegram_id).with_for_update())).scalar_one()
        product = (await session.execute(select(Product).where(Product.id == product_id, Product.is_active.is_(True)).with_for_update())).scalar_one_or_none()
        if not product or product.stock <= 0:
            await callback.message.edit_text("❌ El producto ya no está disponible.", reply_markup=nav())
            return

        price = selected_price(product, variant)
        if price is None:
            await callback.message.edit_text("❌ La duración seleccionada ya no está disponible.", reply_markup=nav())
            return
        data = await state.get_data() if state else {}
        coupon_code = data.get("coupon_code")
        coupon = None
        member_percent = membership_discount_percent(user)
        member_discount = money(price * member_percent / Decimal(100)) if member_percent else Decimal("0.00")
        discount = Decimal("0.00")
        if coupon_code:
            coupon = (await session.execute(select(Coupon).where(Coupon.code == coupon_code).with_for_update())).scalar_one_or_none()
            if coupon and (await session.execute(select(CouponRedemption).where(CouponRedemption.coupon_id == coupon.id, CouponRedemption.user_id == user.id))).scalar_one_or_none():
                coupon = None
            discount = coupon_discount(coupon, money(price) - member_discount, user)
        total = money(price) - member_discount - discount
        if not is_dueno(user) and user.balance < total:
            await callback.message.edit_text(f"❌ <b>SALDO INSUFICIENTE</b>\n\nSaldo actual: {m(user.balance)}\nPrecio: {m(total)}\nFalta: {m(total - money(user.balance))}", reply_markup=nav())
            return
        order_id = f"LXZ-{secrets.token_hex(5).upper()}"
        if not is_dueno(user):
            user.balance = money(user.balance) - total
        user.total_spent = money(user.total_spent) + total
        user.purchases_count += 1
        product.stock -= 1
        product.sales_count += 1
        variant_text = f" ({variant})" if variant != "default" else ""
        product_name_full = f"{product.name}{variant_text}"
        purchase = Purchase(order_id=order_id, user_id=user.id, product_id=product.id, product_name=product_name_full, price=total, discount=member_discount + discount, coupon_code=coupon.code if coupon else None, delivery_data=product.delivery_data, delivered_at=utcnow() if product.delivery_data else None)
        session.add(purchase)
        await session.flush()
        session.add(BalanceTransaction(user_id=user.id, kind=BalanceTransactionType.PURCHASE, amount=Decimal("0.00") if is_dueno(user) else -total, balance_after=user.balance, reference=order_id, note=f"{product_name_full} · saldo infinito DUEÑO" if is_dueno(user) else product_name_full))
        if coupon:
            coupon.used_count += 1
            session.add(CouponRedemption(coupon_id=coupon.id, user_id=user.id, purchase_id=purchase.id))
        await log_event(session, user.telegram_id, "purchase", order_id, "approved")
        await session.commit()
        if state:
            await state.clear()
        delivery = f"\n\n📦 <b>DATOS DE ENTREGA:</b>\n<code>{product.delivery_data}</code>" if product.delivery_data else "\n\n📦 Entrega: el administrador procesará tu pedido."
        text = f"✅ <b>COMPRA EXITOSA</b>\n\n📦 Producto: {product_name_full}\n💵 Pagado: {m(total)} USD\n💰 Saldo restante: {balance_display(user)}\n🧾 Pedido: <code>{order_id}</code>\n📅 Fecha: {now_text()}{delivery}"
        await callback.message.edit_text(text, reply_markup=nav())
        await notify_staff(bot, f"🛒 <b>NUEVA VENTA</b>\n👤 {name_of(user)} ({user.telegram_id})\n📦 {product_name_full}\n💵 {m(total)}\n🧾 {order_id}")
    except Exception:
        await session.rollback()
        logger.exception("purchase processing failed")
        await callback.message.edit_text("❌ No pudimos procesar la compra. Inténtalo nuevamente.", reply_markup=nav())


@router.callback_query(F.data == "menu:profile")
async def menu_profile(callback: CallbackQuery, session: AsyncSession, current_user: User | None = None):
    user = await event_user(callback, session, current_user)
    if not user:
        return
    text = (f"❰ ʟxᴢ ꜱᴛᴏʀᴇ ʙᴇꜱᴛ — 𝐔𝐒𝐄𝐑 𝐏𝐑𝐎𝐅𝐈𝐋𝐄 ❱\n\n"
            f"👤 𝐔𝐬𝐮𝐚𝐫𝐢𝐨: {name_of(user)} | <code>{user.telegram_id}</code>\n"
            f"🗝 𝐏𝐞𝐫𝐦𝐢𝐬𝐨𝐬: {user.role.value} — 𝐀𝐂𝐂𝐄𝐒𝐒\n"
            f"💰 𝐒𝐚𝐥𝐝𝐨: {balance_display(user)}\n\n"
            f"📊 <b>𝐄𝐒𝐓𝐀𝐃𝐈́𝐒𝐓𝐈𝐂𝐀𝐒</b>\n"
            f"📦 Compras: {user.purchases_count}\n"
            f"💵 Gastado: {m(user.total_spent)} USD\n"
            f"📅 Registro: {now_text(user.created_at)}\n\n"
            f"🎁 <b>𝐁𝐄𝐍𝐄𝐅𝐈𝐂𝐈𝐎𝐒</b>\n"
            f"💎 PREMIUN: {'Activo · 10% OFF' if user.role == UserRole.PREMIUN or active_premium(user) else 'Inactivo'}\n"
            f"🤝 SOCIO: {'Activo · 20% OFF' if user.role == UserRole.SOCIO or user.is_partner else 'Inactivo'}")
    await edit_or_answer(callback, text, kb([[("📦 Historial de Compras", "menu:purchases", None)], [("🏠 Inicio", "menu:home", None)]]))


async def render_purchases(callback: CallbackQuery, session: AsyncSession, user: User, page: int):
    items = (await session.execute(select(Purchase).where(Purchase.user_id == user.id).order_by(desc(Purchase.created_at)))).scalars().all()
    pages = max(1, math.ceil(len(items) / PAGE_SIZE))
    page = max(0, min(page, pages - 1))
    current = items[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
    text = f"❰ ʟxᴢ ꜱᴛᴏʀᴇ ʙᴇꜱᴛ — 𝐏𝐔𝐑𝐂𝐇𝐀𝐒𝐄 𝐇𝐈𝐒𝐓𝐎𝐑𝐘 ❱\n\n📦 <b>MIS COMPRAS</b> · Página {page + 1}/{pages}\n\n" + ("\n".join(f"🧾 <code>{p.order_id}</code>\n📦 {p.product_name} · {m(p.price)} USD\n" for p in current) if current else "Aún no tienes compras.")
    rows = []
    for p in current:
        rows.append([(f"🔍 Ver {p.order_id}", f"purchase:{p.id}", None)])
    pager = []
    if page > 0: pager.append(("◀️ Anterior", f"purchases:{page-1}", None))
    if page + 1 < pages: pager.append(("▶️ Siguiente", f"purchases:{page+1}", None))
    if pager: rows.append(pager)
    rows.append([("🏠 Inicio", "menu:home", None)])
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
    text = f"❰ ʟxᴢ ꜱᴛᴏʀᴇ ʙᴇꜱᴛ — 𝐏𝐔𝐑𝐂𝐇𝐀𝐒𝐄 𝐃𝐄𝐓𝐀𝐈𝐋 ❱\n\n🧾 <b>DETALLE DE COMPRA</b>\n\nPedido: <code>{purchase.order_id}</code>\nProducto: {purchase.product_name}\nPagado: {m(purchase.price)} USD\nEstado: {purchase.status.value}\nFecha: {now_text(purchase.created_at)}{delivery}"
    markup = kb([[("⬅️ Historial", "menu:purchases", None), ("🏠 Inicio", "menu:home", None)]])
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    home_image = HOME_BANNER
    if Path(home_image).is_file():
        await callback.message.answer_photo(FSInputFile(home_image), caption=text, reply_markup=markup)
        await callback.answer()
    else:
        await edit_or_answer(callback, text, markup)


@router.callback_query(F.data == "menu:balance")
async def menu_balance(callback: CallbackQuery, session: AsyncSession, current_user: User | None = None):
    user = await event_user(callback, session, current_user)
    if user:
        text = f"💳 <b>RECARGAR SALDO USD</b>\n\nSaldo actual: <b>{balance_display(user)}</b>\n\n📌 Primera recarga: mínimo <b>10 USD</b>. Después de una recarga aprobada: mínimo <b>3 USD</b>.\n\n📍 <b>SELECCIONA TU MÉTODO O PAÍS PARA RECARGAR:</b>"
        markup = topup_countries()
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            pass
        home_image = HOME_BANNER
        if Path(home_image).is_file():
            await callback.message.answer_photo(FSInputFile(home_image), caption=text, reply_markup=markup)
            await callback.answer()
        else:
            await edit_or_answer(callback, text, markup)


@router.callback_query(F.data == "topup:noop")
async def topup_noop(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data == "topup:assisted")
async def topup_assisted(callback: CallbackQuery):
    support = f"@{settings.SUPPORT_USERNAME.lstrip('@')}" if settings.SUPPORT_USERNAME else "el administrador de la tienda"
    await edit_or_answer(callback, f"👤 <b>RECARGA ASISTIDA</b>\n\nContacta a {support} indicando tu país y el monto en USD.\n\nUn administrador confirmará la recarga después de revisar el pago.", nav())


@router.callback_query(F.data.startswith("topup:country:"))
async def topup_country(callback: CallbackQuery, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    code = callback.data.rsplit(":", 1)[1]
    country = dict(TOPUP_COUNTRIES).get(code)
    if not country:
        await callback.answer("País no disponible.", show_alert=True)
        return
    await state.update_data(country=code, country_name=country, currency="USD", rate="1.00")
    if code == "pe":
        await edit_or_answer(callback, f"📍 <b>{country}</b>\n\nSelecciona la moneda que recibirás:", peru_currency_methods())
    elif code in {"ar", "co", "ve"}:
        await state.set_state(TopupFlow.amount)
        user = await event_user(callback, session, current_user)
        first_topup = bool(user and not await has_approved_topup(session, user.id))
        await edit_or_answer(callback, f"📍 <b>{country}</b>\n\nSelecciona el monto de la recarga en USD. La primera recarga debe ser mínimo de 10 USD.", topup_amounts("USD", Decimal(1), first_topup))
    else:
        await edit_or_answer(callback, f"📍 <b>{country}</b>\n\nSelecciona el activo digital que recibirás:", crypto_assets())


@router.callback_query(F.data == "topup:crypto_assets")
async def topup_crypto_assets(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get("country_name") or data.get("country") == "pe":
        await callback.answer("Selecciona primero un país internacional.", show_alert=True)
        return
    await edit_or_answer(callback, "💱 <b>ACTIVO DIGITAL</b>\n\nSelecciona USDC o USDT:", crypto_assets())


@router.callback_query(F.data.startswith("topup:asset:"))
async def topup_asset(callback: CallbackQuery, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    asset = callback.data.rsplit(":", 1)[1].upper()
    if asset not in {"USDC", "USDT"}:
        await callback.answer("Activo no disponible.", show_alert=True)
        return
    data = await state.get_data()
    if not data.get("country_name") or data.get("country") == "pe":
        await callback.answer("Selecciona primero un país internacional.", show_alert=True)
        return
    await state.update_data(asset=asset, currency="USD", rate="1.00", minimum="1.00", maximum="10000.00")
    await state.set_state(TopupFlow.amount)
    user = await event_user(callback, session, current_user)
    first_topup = bool(user and not await has_approved_topup(session, user.id))
    await edit_or_answer(callback, f"💱 <b>RECARGAR USD · {asset}</b>\n\nSelecciona el monto en USD. La primera recarga debe ser mínimo de 10 USD.", topup_amounts("USD", Decimal(1), first_topup))


@router.callback_query(F.data.startswith("topup:network:"))
async def topup_network(callback: CallbackQuery, state: FSMContext):
    network = callback.data.rsplit(":", 1)[1]
    config = CRYPTO_NETWORK_CONFIG.get(network)
    data = await state.get_data()
    asset = data.get("asset", "USDT")
    if not config or asset not in {"USDC", "USDT"}:
        await callback.answer("Red o activo no disponible.", show_alert=True)
        return
    data = await state.get_data()
    if not data.get("source_amount"):
        await callback.answer("Primero selecciona el monto.", show_alert=True)
        return
    await state.set_state(TopupFlow.proof)
    await state.update_data(method=f"{asset} · {config['label']}", currency=asset, rate="1.00", minimum="1.00", maximum="10000.00", network=config["network"], wallet=config["address"])
    details = (f"🌐 Red: <b>{config['network']}</b>\n"
               f"📥 Dirección: <code>{config['address']}</code>\n"
               f"💸 Comisión: {config['fee']}")
    data = await state.get_data()
    await edit_or_answer(callback, f"💱 <b>RECARGAR USD · {asset}</b>\n\nMonto: <b>{m(data['amount'])} USD</b>\nRecibirás {asset} en la red seleccionada.\n\n{details}\n\n⚠️ {config['instruction']}\n\n📥 Primera recarga: mínimo 10 USD.\n⏱️ Tiempo estimado: En minutos\n\n📸 Envía ahora el comprobante del pago.", None)


@router.callback_query(F.data == "topup:currency:pen")
async def topup_currency_pen(callback: CallbackQuery, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    data = await state.get_data()
    if data.get("country") != "pe":
        await callback.answer("Primero selecciona Perú.", show_alert=True)
        return
    await state.update_data(currency="USD", rate=str(PERU_PAYMENT_CONFIG["rate"]), minimum="0.00", maximum=str(PERU_PAYMENT_CONFIG["maximum"] / PERU_PAYMENT_CONFIG["rate"]))
    await state.set_state(TopupFlow.amount)
    user = await event_user(callback, session, current_user)
    first_topup = bool(user and not await has_approved_topup(session, user.id))
    await edit_or_answer(callback, "🇵🇪 <b>RECARGAR USD</b>\n\nElige el monto en USD. La primera recarga debe ser mínimo de 10 USD; después podrás usar desde 3 USD. La conversión a PEN se mostrará en el paso de pago.", topup_amounts("USD", Decimal(1), first_topup))


@router.callback_query(F.data.startswith("topup:local_method:"))
async def topup_local_method(callback: CallbackQuery, state: FSMContext):
    country = callback.data.rsplit(":", 1)[1]
    configs = {
        "ar": (settings.ARGENTINA_METHOD_NAME, settings.ARGENTINA_ACCOUNT, settings.ARGENTINA_HOLDER, "Cuenta"),
        "co": (settings.COLOMBIA_METHOD_NAME, settings.COLOMBIA_ACCOUNT, settings.COLOMBIA_HOLDER, "Cuenta"),
    }
    if country not in configs:
        await callback.answer("Método no disponible.", show_alert=True)
        return
    data = await state.get_data()
    if not data.get("amount"):
        await callback.answer("Primero selecciona el monto en USD.", show_alert=True)
        return
    method, account, holder, account_label = configs[country]
    usd_amount = money(data["amount"])
    await state.set_state(TopupFlow.proof)
    await state.update_data(method=f"{method} · {country.upper()}", source_amount=str(usd_amount), amount=str(usd_amount), currency="USD", rate="1.00")
    details = (f"💳 <b>{method}</b>\n"
               f"📌 {account_label}: <code>{account or 'no configurado'}</code>\n"
               f"👤 Titular: <b>{holder or 'no configurado'}</b>")
    share_text = f"Pago {method} · {account_label}: {account or 'no configurado'} · Titular: {holder or 'no configurado'} · Monto {m(usd_amount)} USD"
    share_url = f"https://t.me/share/url?url=&text={quote(share_text)}"
    markup = kb([
        [("🔗 Compartir", None, share_url)],
        [("📋 Copiar datos", "topup:local_copy", None)],
        [("✅ He pagado", "topup:local_paid", None)],
    ])
    await edit_or_answer(callback, f"💳 <b>SELECCIONAR MÉTODO DE PAGO</b>\n\n💵 Monto: <b>{m(usd_amount)} USD</b>\n\n{details}\n\n📝 Una vez realizado el pago, espere la verificación. Después pulsa <b>He pagado</b> y envía el comprobante.\n\n❓ Dudas: <a href=\"{settings.SUPPORT_URL}\">Contactar soporte</a>", markup)

@router.callback_query(F.data == "topup:local_copy")
async def topup_local_copy(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    country = data.get("country")
    configs = {
        "ar": (settings.ARGENTINA_METHOD_NAME, settings.ARGENTINA_ACCOUNT, settings.ARGENTINA_HOLDER),
        "co": (settings.COLOMBIA_METHOD_NAME, settings.COLOMBIA_ACCOUNT, settings.COLOMBIA_HOLDER),
    }
    if country not in configs:
        await callback.answer("Datos no disponibles.", show_alert=True)
        return
    method, account, holder = configs[country]
    await callback.answer(f"{method}\nCuenta: {account or 'no configurado'}\nTitular: {holder or 'no configurado'}", show_alert=True)

@router.callback_query(F.data == "topup:local_paid")
async def topup_local_paid(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get("amount"):
        await callback.answer("Primero selecciona el monto.", show_alert=True)
        return
    await state.set_state(TopupFlow.proof)
    await edit_or_answer(callback, "✅ <b>PAGO REGISTRADO</b>\n\n📸 Envía ahora la fotografía o documento del comprobante para que un administrador verifique la recarga.\n\n❓ Dudas: <a href=\"https://t.me/Lxz_Modz\">Contactar soporte</a>", None)

@router.callback_query(F.data == "topup:venezuela_method:bancamiga")
async def topup_venezuela_method(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get("amount"):
        await callback.answer("Primero selecciona el monto en USD.", show_alert=True)
        return
    usd_amount = money(data["amount"])
    await state.set_state(TopupFlow.proof)
    await state.update_data(method="Bancamiga · Pago Móvil", source_amount=str(usd_amount), amount=str(usd_amount), currency="USD", rate="1.00")
    bank_name = settings.VENEZUELA_BANK_NAME or "no configurado"
    payment_type = settings.VENEZUELA_PAYMENT_TYPE or "Pago móvil"
    identity = settings.VENEZUELA_ID or "no configurado"
    phone = settings.VENEZUELA_PHONE or "no configurado"
    share_text = (f"Pago Venezuela · {bank_name} · {payment_type} · Cédula {identity} · TLF {phone} · "
                  f"Monto {m(usd_amount)} USD")
    share_url = f"https://t.me/share/url?url=&text={quote(share_text)}"
    details = (f"🏦 <b>{bank_name}</b>\n"
               f"📌 Tipo: <b>{payment_type}</b>\n"
               f"🪪 Cédula: <code>{identity}</code>\n"
               f"📞 TLF: <code>{phone}</code>")
    external_prices = ("🚀 <b>PRECIOS DE DRIP CLIENT EXTERNAL</b>\n"
                       "• 1 Día — <b>3 USD</b>\n"
                       "• 3 Días — <b>5 USD</b>\n"
                       "• 7 Días — <b>7 USD</b>\n"
                       "• 30 Días — <b>14 USD</b>")
    markup = kb([
        [("🔗 Compartir", None, share_url)],
        [("📋 Copiar datos", "topup:venezuela_copy", None)],
        [("✅ He pagado", "topup:venezuela_paid", None)],
    ])
    await edit_or_answer(callback, f"💳 <b>SELECCIONAR MÉTODO DE PAGO</b>\n\n💵 Monto: <b>{m(usd_amount)} USD</b>\n\n{details}\n\n{external_prices}\n\n📝 Realiza el pago, comparte o copia los datos y luego pulsa <b>He pagado</b>.\n\n❓ Dudas: <a href=\"{settings.SUPPORT_URL}\">Contactar soporte</a>", markup)

@router.callback_query(F.data == "topup:venezuela_copy")
async def topup_venezuela_copy(callback: CallbackQuery, state: FSMContext):
    await callback.answer(
        f"{settings.VENEZUELA_BANK_NAME or 'Bancamiga'} · {settings.VENEZUELA_PAYMENT_TYPE or 'Pago móvil'}\n"
        f"Cédula: {settings.VENEZUELA_ID or 'no configurado'}\nTLF: {settings.VENEZUELA_PHONE or 'no configurado'}",
        show_alert=True,
    )

@router.callback_query(F.data == "topup:venezuela_paid")
async def topup_venezuela_paid(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data.get("amount"):
        await callback.answer("Primero selecciona el monto.", show_alert=True)
        return
    await state.set_state(TopupFlow.proof)
    await edit_or_answer(callback, "✅ <b>PAGO REGISTRADO</b>\n\n📸 Envía ahora la fotografía o documento del comprobante para que un administrador verifique la recarga.\n\n❓ Dudas: <a href=\"https://t.me/Lxz_Modz\">Contactar soporte</a>", None)

@router.callback_query(F.data.startswith("topup:peru_method:"))
async def topup_peru_method(callback: CallbackQuery, state: FSMContext):
    method = callback.data.rsplit(":", 1)[1]
    method_labels = {"yape": "Yape", "plin": "Plin", "ligo": "Ligo", "bank": "Transferencia bancaria · CCI"}
    if method not in method_labels:
        await callback.answer("Método no disponible.", show_alert=True)
        return
    data = await state.get_data()
    if not data.get("amount"):
        await callback.answer("Primero selecciona el monto en USD.", show_alert=True)
        return
    usd_amount = money(data["amount"])
    pen_amount = money(usd_amount * PERU_PAYMENT_CONFIG["rate"])
    await state.set_state(TopupFlow.proof)
    await state.update_data(source_amount=str(pen_amount), amount=str(usd_amount), currency="PEN", rate=str(PERU_PAYMENT_CONFIG["rate"]), minimum=str(PERU_PAYMENT_CONFIG["minimum"]), maximum=str(PERU_PAYMENT_CONFIG["maximum"]))
    account_details = {
        "yape": ("Yape", settings.YAPE_NUMBER, settings.YAPE_NAME),
        "ligo": ("Takenos (Ligo)", settings.LIGO_NUMBER, settings.LIGO_NAME),
        "plin": ("Plin", settings.PLIN_NUMBER, settings.PLIN_NAME),
    }
    if method in account_details:
        account_label, account_number, account_name = account_details[method]
        details = (f"📱 {account_label}: <code>{account_number or 'no configurado'}</code>\n"
                   f"👤 Nombre: <b>{account_name or 'no configurado'}</b>")
        instructions = "Realiza el pago al número indicado y envía el comprobante junto con tu ID."
    else:
        details = f"👤 Titular: <b>{PERU_PAYMENT_CONFIG['holder']}</b>\n🏦 CCI: <code>{PERU_PAYMENT_CONFIG['cci']}</code>"
        instructions = "Usa el número de CCI en bancos y/o cajas y envía el comprobante junto con tu ID."
    data = await state.get_data()
    await edit_or_answer(callback, f"💳 <b>RECARGAR USD · {method_labels[method]}</b>\n\nMonto: <b>{m(data['amount'])} USD</b>\nPago local aproximado: <b>{money(data['source_amount']):,.2f} PEN</b>\n\n{details}\n\n📝 {instructions}\n\n💱 1 USD = {PERU_PAYMENT_CONFIG['rate']:.2f} PEN\n📸 Envía ahora el comprobante del pago.\n\n❓ Dudas: <a href=\"{settings.SUPPORT_URL}\">Contactar soporte</a>", None)


@router.callback_query(F.data.startswith("topup:method:"))
async def topup_method(callback: CallbackQuery, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    method = callback.data.rsplit(":", 1)[1]
    if method not in TOPUP_METHOD_LABELS:
        await callback.answer("Método no disponible.", show_alert=True)
        return
    data = await state.get_data()
    if not data.get("country_name"):
        await callback.answer("Primero selecciona un país.", show_alert=True)
        return
    await state.set_state(TopupFlow.amount)
    await state.update_data(method=TOPUP_METHOD_LABELS[method])
    if method == "binance" and settings.BINANCE_USDT_ENABLED and settings.BINANCE_USDT_ADDRESS:
        details = f"Red: <b>{settings.BINANCE_USDT_NETWORK}</b>\nDirección: <code>{settings.BINANCE_USDT_ADDRESS}</code>"
    elif method == "yape_plin" and (settings.YAPE_NUMBER or settings.PLIN_NUMBER):
        details = f"Yape: <code>{settings.YAPE_NUMBER or 'no configurado'}</code>\nPlin: <code>{settings.PLIN_NUMBER or 'no configurado'}</code>"
    else:
        details = "Esta recarga se procesa de forma asistida. Contacta al administrador y conserva tu comprobante."
    user = await event_user(callback, session, current_user)
    first_topup = bool(user and not await has_approved_topup(session, user.id))
    await edit_or_answer(callback, f"💳 <b>RECARGAR USD · {TOPUP_METHOD_LABELS[method]}</b>\n📍 País: <b>{data['country_name']}</b>\n\n{details}\n\nSelecciona el monto en USD. Primera recarga: mínimo 10 USD.", topup_amounts("USD", Decimal(1), first_topup))


@router.callback_query(F.data.startswith("topup:amount:"))
async def topup_amount_choice(callback: CallbackQuery, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    parts = callback.data.split(":")
    if len(parts) != 5:
        await callback.answer("Monto inválido.", show_alert=True)
        return
    source_amount = money(parts[2])
    currency = parts[3]
    usd_amount = money(parts[4])
    if source_amount <= 0 or usd_amount <= 0:
        await callback.answer("Monto inválido.", show_alert=True)
        return
    user = await event_user(callback, session, current_user)
    if user and not await has_approved_topup(session, user.id) and usd_amount < FIRST_TOPUP_MINIMUM_USD:
        await callback.answer("La primera recarga debe ser de mínimo 10 USD.", show_alert=True)
        return
    if user and await has_approved_topup(session, user.id) and usd_amount < SUBSEQUENT_TOPUP_MINIMUM_USD:
        await callback.answer("Después de la primera recarga, el mínimo es de 3 USD.", show_alert=True)
        return
    await state.update_data(amount=str(usd_amount), source_amount=str(source_amount), currency=currency)
    conversion = f"{source_amount} {currency} → {m(usd_amount)}" if currency != "USD" else m(usd_amount)
    flow_data = await state.get_data()
    if flow_data.get("country") == "pe":
        await edit_or_answer(callback, f"💵 <b>RECARGAR USD: {m(usd_amount)}</b>\n\nAhora selecciona la cuenta o billetera peruana de destino. El pago local se calculará en PEN.", peru_payment_methods())
    elif flow_data.get("country") in {"ar", "co", "ve"}:
        await edit_or_answer(callback, f"💵 <b>RECARGAR USD: {m(usd_amount)}</b>\n\nSelecciona el método de pago local.", local_payment_methods(flow_data["country"]))
    elif flow_data.get("asset") in {"USDT", "USDC"}:
        await edit_or_answer(callback, f"💵 <b>RECARGAR USD: {m(usd_amount)}</b>\n\nAhora selecciona la red de destino para recibir {flow_data['asset']}.", crypto_networks(flow_data["asset"]))
    else:
        await state.set_state(TopupFlow.proof)
        await edit_or_answer(callback, f"💵 <b>Monto seleccionado: {conversion}</b>\n\nAhora envía la fotografía o documento del comprobante. Usa /start para cancelar.")


@router.callback_query(F.data == "topup:custom")
async def topup_custom(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    currency = data.get("currency", "USD")
    await state.set_state(TopupFlow.amount)
    await edit_or_answer(callback, f"✍️ <b>MONTO PERSONALIZADO</b>\n\nEscribe la cantidad en {currency}. Ejemplo: {'42.50' if currency == 'PEN' else '12.50'}")


@router.message(TopupFlow.amount, F.text)
async def topup_amount(message: Message, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    data = await state.get_data()
    user = await event_user(message, session, current_user)
    if not user:
        return
    source_amount = money(message.text)
    currency = data.get("currency", "USD")
    rate = money(data.get("rate", "1")) or Decimal("1.00")
    if source_amount <= 0:
        await message.answer("❌ Escribe un monto mayor que cero.")
        return
    minimum = money(data.get("minimum", "0"))
    maximum = money(data.get("maximum", "0"))
    if minimum and source_amount < minimum:
        await message.answer(f"❌ El mínimo es {minimum:,.2f} {currency}.")
        return
    if maximum and source_amount > maximum:
        await message.answer(f"❌ El máximo es {maximum:,.2f} {currency}.")
        return
    usd_amount = source_amount if currency == "USD" else money(source_amount / rate)
    if not await has_approved_topup(session, user.id) and usd_amount < FIRST_TOPUP_MINIMUM_USD:
        await message.answer("❌ Tu primera recarga debe ser de mínimo 10 USD. Después de una recarga aprobada podrás usar desde 3 USD.")
        return
    if await has_approved_topup(session, user.id) and usd_amount < SUBSEQUENT_TOPUP_MINIMUM_USD:
        await message.answer("❌ Después de la primera recarga, el mínimo es de 3 USD.")
        return
    await state.update_data(amount=str(usd_amount), source_amount=str(source_amount), currency=currency)
    conversion = f"{source_amount:,.2f} {currency} → {m(usd_amount)}" if currency != "USD" else m(usd_amount)
    if data.get("country") == "pe":
        await message.answer(f"✅ <b>RECARGAR USD: {m(usd_amount)}</b>\n\nAhora selecciona la cuenta o billetera peruana de destino. El pago local se calculará en PEN.", reply_markup=peru_payment_methods())
    elif data.get("country") in {"ar", "co", "ve"}:
        await message.answer(f"✅ <b>RECARGAR USD: {m(usd_amount)}</b>\n\nSelecciona el método de pago local.", reply_markup=local_payment_methods(data["country"]))
    elif currency in {"USDT", "USDC"}:
        await message.answer(f"✅ Monto registrado: <b>{conversion}</b>\n\nAhora selecciona la red de destino:", reply_markup=crypto_networks(currency))
    else:
        await state.set_state(TopupFlow.proof)
        await message.answer(f"✅ Monto registrado: <b>{conversion}</b>\n\n📸 Ahora envía una fotografía del comprobante. También puedes enviar un documento de imagen.")


@router.message(TopupFlow.proof, F.photo)
async def topup_photo(message: Message, state: FSMContext, session: AsyncSession, bot: Bot, current_user: User | None = None):
    await create_topup(message, state, session, bot, message.photo[-1].file_id, "photo", current_user)


@router.message(TopupFlow.proof, F.document)
async def topup_document(message: Message, state: FSMContext, session: AsyncSession, bot: Bot, current_user: User | None = None):
    await create_topup(message, state, session, bot, message.document.file_id, "document", current_user)


async def create_topup(message: Message, state: FSMContext, session: AsyncSession, bot: Bot, file_id: str, proof_type: str, current_user: User | None):
    user = await event_user(message, session, current_user)
    data = await state.get_data()
    country_name = data.get("country_name", "País no indicado")
    method = data.get("method", "Método no indicado")
    network = data.get("network")
    if network:
        method = f"{method} · {network}"
    currency = data.get("currency", "USD")
    usd_amount = money(data["amount"])
    source_amount = money(data.get("source_amount", data["amount"]))
    amount_text = f"{source_amount:,.2f} {currency} → {m(usd_amount)}" if currency != "USD" else m(usd_amount)
    request = TopupRequest(user_id=user.id, method=f"{country_name} · {method}", amount=usd_amount, proof_file_id=file_id, proof_type=proof_type)
    session.add(request); await session.commit(); await session.refresh(request)
    await log_event(session, user.telegram_id, "topup_request", str(request.id), "pending"); await session.commit()
    await state.clear()
    await message.answer(f"🟡 <b>RECARGA PENDIENTE</b>\n\nMonto recibido: {amount_text}\nMétodo: {request.method}\nSolicitud: <code>#{request.id}</code>\n\nUn administrador revisará tu comprobante.", reply_markup=nav())
    markup = kb([[ ("✅ Aprobar", f"topup:approve:{request.id}", None), ("❌ Rechazar", f"topup:reject:{request.id}", None) ]])
    caption = f"🧾 <b>SOLICITUD DE RECARGA #{request.id}</b>\n👤 Usuario: {name_of(user)}\n🆔 ID: <code>{user.telegram_id}</code>\n💵 Monto: {amount_text}\n💳 Método: {request.method}\n📅 Fecha: {now_text()}\n📌 Estado: Pendiente"
    for admin_id in settings.admin_ids:
        try:
            if proof_type == "photo": await bot.send_photo(admin_id, file_id, caption=caption, reply_markup=markup)
            else: await bot.send_document(admin_id, file_id, caption=caption, reply_markup=markup)
        except Exception:
            logger.exception("No se pudo enviar la solicitud de recarga al administrador %s.", admin_id)


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
    try:
        await bot.send_message(user.telegram_id, user_msg, reply_markup=nav())
    except Exception:
        logger.exception("No se pudo notificar al usuario %s sobre la recarga.", user.telegram_id)
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
    await edit_or_answer(callback, "\n".join(lines) + "\n\nEscribe un código para aplicarlo a tu próxima compra, o /start.")


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


@router.callback_query(F.data == "menu:partner")
async def menu_partner(callback: CallbackQuery, session: AsyncSession, current_user: User | None = None):
    user = await event_user(callback, session, current_user)
    if not user:
        return
    if user.is_partner or user.role == UserRole.SOCIO:
        text = "🤝 <b>SOCIO OFICIAL</b>\n\nEstado: 🟢 Activo\nBeneficio: 20% de descuento automático en el catálogo.\nSoporte: atención prioritaria."
    else:
        text = ("🤝 <b>SISTEMA DE ASOCIACIÓN</b>\n\n"
                "Al convertirte en Socio Oficial obtienes:\n"
                "✅ Descuento general del 20% en el catálogo\n"
                "✅ Permiso de reventa según tus acuerdos comerciales\n"
                "✅ Atención prioritaria\n\n"
                f"💵 Inversión única: <b>{m(settings.PARTNER_FEE_USD)}</b>\n\n"
                "Elige cómo deseas pagar:")
    await edit_or_answer(callback, text, partner_menu())


@router.callback_query(F.data == "partner:pay_balance")
async def partner_pay_balance(callback: CallbackQuery, session: AsyncSession, current_user: User | None = None):
    user = await event_user(callback, session, current_user)
    if not user:
        return
    if user.is_partner or user.role == UserRole.SOCIO:
        await edit_or_answer(callback, "✅ Ya tienes activo el estado de Socio Oficial.", nav())
        return
    fee = money(settings.PARTNER_FEE_USD)
    if not is_dueno(user) and money(user.balance) < fee:
        await edit_or_answer(callback, f"❌ Saldo insuficiente.\n\nNecesitas: {m(fee)}\nSaldo actual: {m(user.balance)}\n\nPuedes recargar saldo o pagar por transferencia.", partner_menu())
        return
    balance_after = balance_display(user) if is_dueno(user) else m(money(user.balance) - fee)
    await edit_or_answer(callback, f"🤝 <b>CONFIRMAR SOCIO OFICIAL</b>\n\nInversión única: {m(fee)}\nDescuento permanente: {settings.PARTNER_DISCOUNT_PERCENT}%\nSaldo después: {balance_after}", confirm("partner:confirm", "menu:partner"))


@router.callback_query(F.data == "partner:confirm")
async def partner_confirm(callback: CallbackQuery, session: AsyncSession, current_user: User | None = None):
    user = await event_user(callback, session, current_user)
    if not user:
        return
    user = (await session.execute(select(User).where(User.telegram_id == user.telegram_id).with_for_update())).scalar_one_or_none()
    if not user or user.is_partner or user.role == UserRole.SOCIO:
        await callback.answer("El estado ya está activo o el usuario no existe.", show_alert=True)
        return
    fee = money(settings.PARTNER_FEE_USD)
    if not is_dueno(user) and money(user.balance) < fee:
        await edit_or_answer(callback, "❌ El saldo ya no es suficiente para activar Socio Oficial.", partner_menu())
        return
    if not is_dueno(user):
        user.balance = money(user.balance) - fee
        session.add(BalanceTransaction(user_id=user.id, kind=BalanceTransactionType.DEBIT, amount=-fee, balance_after=user.balance, reference="partner", note="Socio Oficial"))
    user.is_partner = True
    user.partner_since = utcnow()
    if user.role == UserRole.USUARIO:
        user.role = UserRole.SOCIO
    await log_event(session, user.telegram_id, "partner_activate", str(user.telegram_id), f"fee={Decimal('0.00') if is_dueno(user) else fee}")
    await session.commit()
    await edit_or_answer(callback, f"✅ <b>SOCIO OFICIAL ACTIVADO</b>\n\nDescuento aplicado: {settings.PARTNER_DISCOUNT_PERCENT}%\nSaldo restante: {balance_display(user)}", nav())


@router.callback_query(F.data == "partner:manual")
async def partner_manual(callback: CallbackQuery, current_user: User | None = None):
    await edit_or_answer(callback, f"🏦 <b>PAGO MANUAL SOCIO OFICIAL</b>\n\nRealiza un depósito de {m(settings.PARTNER_FEE_USD)} usando los métodos publicados en <b>Recargar Saldo</b>. Después envía el comprobante y tu ID al soporte: {settings.SUPPORT_URL}\n\nEl administrador verificará el pago y activará tu beneficio. No envíes dinero sin conservar tu comprobante.", nav())


@router.callback_query(F.data == "menu:premium")
async def menu_premium(callback: CallbackQuery, session: AsyncSession, current_user: User | None = None):
    user = await event_user(callback, session, current_user)
    if not user:
        return
    active = user.role == UserRole.PREMIUN or active_premium(user)
    status = "🟢 Activo · 10% OFF" if active else "🔴 Inactivo"
    until = f"\nVálido hasta: {now_text(user.premium_until)}" if user.premium_until else ""
    text = f"💎 <b>PREMIUN</b>\n\nEstado: {status}{until}\n\nBeneficio: 10% de descuento automático en compras.\nPrecio de activación: <b>{m(settings.PREMIUN_FEE_USD)}</b>"
    await edit_or_answer(callback, text, nav() if active else premium_menu())


@router.callback_query(F.data == "premium:pay_balance")
async def premium_pay_balance(callback: CallbackQuery, session: AsyncSession, current_user: User | None = None):
    user = await event_user(callback, session, current_user)
    if not user:
        return
    if user.role == UserRole.PREMIUN or active_premium(user):
        await edit_or_answer(callback, "✅ Ya tienes PREMIUN activo y recibes 10% OFF automáticamente.", nav())
        return
    fee = money(settings.PREMIUN_FEE_USD)
    if not is_dueno(user) and money(user.balance) < fee:
        await edit_or_answer(callback, f"❌ Saldo insuficiente.\n\nNecesitas: {m(fee)}\nSaldo actual: {m(user.balance)}", premium_menu())
        return
    balance_after = balance_display(user) if is_dueno(user) else m(money(user.balance) - fee)
    await edit_or_answer(callback, f"💎 <b>CONFIRMAR PREMIUN</b>\n\nPrecio: {m(fee)}\nSaldo después: {balance_after}\nBeneficio: 10% OFF automático en el catálogo.", confirm("premium:confirm", "menu:premium"))


@router.callback_query(F.data == "premium:confirm")
async def premium_confirm(callback: CallbackQuery, session: AsyncSession, current_user: User | None = None):
    user = await event_user(callback, session, current_user)
    if not user:
        return
    user = (await session.execute(select(User).where(User.telegram_id == user.telegram_id).with_for_update())).scalar_one_or_none()
    if not user:
        await callback.answer("Usuario no encontrado.", show_alert=True)
        return
    if user.role == UserRole.PREMIUN or active_premium(user):
        await edit_or_answer(callback, "✅ PREMIUN ya está activo.", nav())
        return
    fee = money(settings.PREMIUN_FEE_USD)
    if not is_dueno(user) and money(user.balance) < fee:
        await edit_or_answer(callback, "❌ El saldo ya no es suficiente para activar PREMIUN.", premium_menu())
        return
    if not is_dueno(user):
        user.balance = money(user.balance) - fee
        session.add(BalanceTransaction(user_id=user.id, kind=BalanceTransactionType.DEBIT, amount=-fee, balance_after=user.balance, reference="premiun", note="Activación PREMIUN"))
        user.total_spent = money(user.total_spent) + fee
    user.is_premium = True
    user.premium_until = None
    if user.role in (UserRole.USUARIO, UserRole.SOCIO):
        user.role = UserRole.PREMIUN
    await log_event(session, user.telegram_id, "premiun_activate", str(user.telegram_id), f"fee={fee}")
    await session.commit()
    await edit_or_answer(callback, f"✅ <b>PREMIUN ACTIVADO</b>\n\nDescuento automático: 10% OFF\nSaldo restante: {balance_display(user)}", nav())


@router.callback_query(F.data == "premium:manual")
async def premium_manual(callback: CallbackQuery):
    await edit_or_answer(callback, f"🏦 <b>ACTIVAR PREMIUN POR PAGO MANUAL</b>\n\nPrecio: {m(settings.PREMIUN_FEE_USD)}\n\nRealiza el pago usando los métodos publicados en <b>Recargar Saldo</b> y envía el comprobante junto con tu ID a soporte: {settings.SUPPORT_URL}\n\nEl administrador verificará el pago y activará el rango PREMIUN.", nav())


@router.callback_query(F.data == "menu:referrals")
async def menu_referrals(callback: CallbackQuery, bot: Bot, session: AsyncSession, current_user: User | None = None):
    user = await event_user(callback, session, current_user)
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start=ref_{user.telegram_id}"
    await edit_or_answer(callback, f"🎁 <b>PROGRAMA DE REFERIDOS</b>\n\n🔗 Tu enlace:\n<code>{link}</code>\n\n👥 Invitados: {user.referrals_count}\n🎁 Recompensas: configuradas por administración\n💰 Ganado: {m(user.referral_earnings)}", nav())


@router.callback_query(F.data == "menu:support")
async def menu_support(callback: CallbackQuery):
    contact = f"@{settings.SUPPORT_USERNAME.lstrip('@')}" if settings.SUPPORT_USERNAME else "el administrador de la tienda"
    support_markup = kb([[("📞 Abrir soporte", None, settings.SUPPORT_URL)], [("⬅️ Volver", "menu:home", None)]])
    await edit_or_answer(callback, f"📞 <b>SOPORTE</b>\n\nPara recibir ayuda, contacta a {contact}.", support_markup)


async def check_admin(callback: CallbackQuery, session: AsyncSession, current_user: User | None) -> User | None:
    user = await event_user(callback, session, current_user)
    if not is_staff(user): await callback.answer("Permisos insuficientes.", show_alert=True); return None
    return user


@router.callback_query(F.data == "admin:home")
async def admin_menu(callback: CallbackQuery, session: AsyncSession, current_user: User | None = None):
    user = await check_admin(callback, session, current_user)
    if user:
        if is_dueno(user):
            await edit_or_answer(callback, "❰ ʟxᴢ ꜱᴛᴏʀᴇ ʙᴇꜱᴛ — 𝐃𝐔𝐄𝐍̃𝐎 𝐂𝐄𝐍𝐓𝐄𝐑 ❱\n\n🏆 <b>PANEL DUEÑO</b>\nControl total de la tienda:", admin_home(UserRole.DUENO))
        elif user.role == UserRole.OWNER:
            await edit_or_answer(callback, "❰ ʟxᴢ ꜱᴛᴏʀᴇ ʙᴇꜱᴛ — 𝐎𝐖𝐍𝐄𝐑 𝐂𝐄𝐍𝐓𝐄𝐑 ❱\n\n👑 <b>PANEL OWNER</b>\nPanel operativo reducido:", admin_home(UserRole.OWNER))
        elif user.role == UserRole.ADMIN:
            await edit_or_answer(callback, "❰ ʟxᴢ ꜱᴛᴏʀᴇ ʙᴇꜱᴛ — 𝐀𝐃𝐌𝐈𝐍 𝐂𝐄𝐍𝐓𝐄𝐑 ❱\n\n🔐 <b>PANEL ADMIN</b>\nPanel operativo básico:", admin_home(UserRole.ADMIN))


@router.callback_query(F.data == "owner:home")
async def owner_menu(callback: CallbackQuery, session: AsyncSession, current_user: User | None = None):
    user = await check_admin(callback, session, current_user)
    if user and is_owner_role(user):
        if is_dueno(user):
            await edit_or_answer(callback, "❰ ʟxᴢ ꜱᴛᴏʀᴇ ʙᴇꜱᴛ — 𝐃𝐔𝐄𝐍̃𝐎 𝐂𝐄𝐍𝐓𝐄𝐑 ❱\n\n🏆 <b>PANEL DUEÑO</b>\nControl total de la tienda:", admin_home(UserRole.DUENO))
        else:
            await edit_or_answer(callback, "❰ ʟxᴢ ꜱᴛᴏʀᴇ ʙᴇꜱᴛ — 𝐎𝐖𝐍𝐄𝐑 𝐂𝐄𝐍𝐓𝐄𝐑 ❱\n\n👑 <b>PANEL OWNER</b>\nPanel operativo reducido:", admin_home(UserRole.OWNER))


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


def user_record_text(user: User, position: int) -> str:
    premium = f"Activo hasta {now_text(user.premium_until)}" if active_premium(user) and user.premium_until else ("Activo" if active_premium(user) else "Inactivo")
    status = f"Baneado: {escape(user.ban_reason or 'sin motivo')}" if user.is_banned else "Activo"
    return (f"<b>#{position} · {escape(name_of(user))}</b>\n"
            f"🆔 ID: <code>{user.telegram_id}</code> · @{escape(user.username or '—')}\n"
            f"🎭 Rol: {escape(user.role.value)} · Estado: {status}\n"
            f"💰 Saldo: {balance_display(user)} · PREMIUN: {premium}\n"
            f"🛒 Compras: {user.purchases_count} · Gastado: {m(user.total_spent)}\n"
            f"👥 Referidos: {user.referrals_count} · Ganado: {m(user.referral_earnings)}\n"
            f"📅 Registro: {now_text(user.created_at)}\n"
            f"🕘 Última actividad: {now_text(user.last_activity)}")


async def render_users_page(callback: CallbackQuery, session: AsyncSession, page: int = 0):
    page_size = 6
    total = await session.scalar(select(func.count(User.id))) or 0
    pages = max(1, math.ceil(total / page_size))
    page = max(0, min(page, pages - 1))
    users = (await session.execute(select(User).order_by(User.created_at.desc(), User.id.desc()).offset(page * page_size).limit(page_size))).scalars().all()
    start = page * page_size + 1
    body = "\n\n".join(user_record_text(user, start + index) for index, user in enumerate(users)) or "No hay usuarios registrados todavía."
    rows = [[(f"👤 {escape(name_of(user))} · {user.telegram_id}", f"admin:user:{user.telegram_id}", None)] for user in users]
    navigation = []
    if page > 0:
        navigation.append(("⬅️ Anteriores", f"admin:users:page:{page - 1}", None))
    if page < pages - 1:
        navigation.append(("Siguientes ➡️", f"admin:users:page:{page + 1}", None))
    if navigation:
        rows.append(navigation)
    rows.append([("🔎 Buscar usuario", "admin:users:search", None)])
    rows.append([("⚙️ Panel Admin", "admin:home", None)])
    await edit_or_answer(callback, f"👥 <b>USUARIOS REGISTRADOS</b>\nOrden: más recientes primero · Página {page + 1}/{pages}\nTotal: {total}\n\n{body}", kb(rows))


@router.callback_query(F.data.startswith("admin:users:page:"))
async def admin_users_page(callback: CallbackQuery, session: AsyncSession, current_user: User | None = None):
    actor = await check_admin(callback, session, current_user)
    if not is_owner_role(actor): return
    try:
        page = int(callback.data.rsplit(":", 1)[1])
    except ValueError:
        await callback.answer("Página inválida.", show_alert=True)
        return
    await render_users_page(callback, session, page)


@router.callback_query(F.data == "admin:users:search")
async def admin_users_search_prompt(callback: CallbackQuery, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    actor = await check_admin(callback, session, current_user)
    if not is_owner_role(actor): return
    await state.set_state(UserSearch.waiting)
    await edit_or_answer(callback, "🔎 <b>BUSCAR USUARIO</b>\n\nEscribe ID, username o nombre. /start para salir.", nav(True, "admin:users"))


@router.callback_query(F.data == "admin:users")
async def admin_users(callback: CallbackQuery, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    actor = await check_admin(callback, session, current_user)
    if not is_owner_role(actor): return
    await state.clear()
    await render_users_page(callback, session)


@router.message(UserSearch.waiting, F.text)
async def admin_user_search(message: Message, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    actor = await event_user(message, session, current_user)
    if not is_owner_role(actor): await state.clear(); return
    query = message.text.strip().lstrip("@")
    filters = [User.username.ilike(f"%{query}%"), User.first_name.ilike(f"%{query}%"), User.last_name.ilike(f"%{query}%")]
    try: filters.append(User.telegram_id == int(query))
    except ValueError: pass
    users = (await session.execute(select(User).where(or_(*filters)).limit(10))).scalars().all()
    rows = [[(f"{name_of(u)} · {u.telegram_id}", f"admin:user:{u.telegram_id}", None)] for u in users]
    rows.append([("⚙️ Panel Admin", "admin:home", None)])
    await message.answer("🔎 Resultados:\n\n" + ("\n".join(f"• {name_of(u)} · {u.telegram_id}" for u in users) if users else "No encontramos usuarios."), reply_markup=kb(rows))
    await state.clear()


@router.callback_query(F.data.startswith("admin:user:"))
async def admin_user_detail(callback: CallbackQuery, session: AsyncSession, current_user: User | None = None):
    actor = await check_admin(callback, session, current_user)
    if not is_owner_role(actor): return
    target = (await session.execute(select(User).where(User.telegram_id == int(callback.data.split(":")[2])))).scalar_one_or_none()
    if not target: await callback.answer("Usuario no encontrado.", show_alert=True); return
    rows = []
    if is_admin(actor) and not is_dueno(target):
        rows.extend([[ ("💰 Dar saldo USD", f"admin:balance:add:{target.telegram_id}", None), ("➖ Quitar saldo USD", f"admin:balance:sub:{target.telegram_id}", None)], [ ("💎 Activar PREMIUN", f"admin:premium:on:{target.telegram_id}", None), ("❌ Quitar PREMIUN", f"admin:premium:off:{target.telegram_id}", None)]])
        if target.telegram_id != settings.OWNER_ID and (is_owner(actor) or target.role != UserRole.ADMIN):
            rows.append([( "✅ Desbanear" if target.is_banned else "🚫 Banear", f"admin:ban:{'off' if target.is_banned else 'on'}:{target.telegram_id}", None)])
    rows.append([("⬅️ Volver", "admin:users", None), ("⚙️ Panel Admin", "admin:home", None)])
    await edit_or_answer(callback, f"👤 <b>USUARIO</b>\n\nNombre: {name_of(target)}\nUsername: @{target.username or '—'}\nID: <code>{target.telegram_id}</code>\nRango: {target.role.value}\nSaldo: {balance_display(target)}\nPREMIUN: {active_premium(target) or target.role == UserRole.PREMIUN}\nCompras: {target.purchases_count}\nEstado: {'Baneado' if target.is_banned else 'Activo'}", kb(rows))


@router.callback_query(F.data.startswith("admin:balance:"))
async def admin_balance_prompt(callback: CallbackQuery, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    actor = await check_admin(callback, session, current_user)
    if not is_owner_role(actor): await callback.answer("Solo OWNER o DUEÑO.", show_alert=True); return
    _, _, kind, target = callback.data.split(":")
    await state.set_state(BalanceFlow.amount); await state.update_data(kind=kind, target=int(target))
    await edit_or_answer(callback, f"💰 Escribe la cantidad a {'agregar' if kind == 'add' else 'quitar'} para <code>{target}</code>. Debe ser mayor que cero.")


@router.message(BalanceFlow.amount, F.text)
async def admin_balance_amount(message: Message, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    actor = await event_user(message, session, current_user)
    if not is_owner_role(actor): await state.clear(); return
    amount = money(message.text)
    if amount <= 0: await message.answer("❌ Cantidad inválida."); return
    data = await state.get_data(); target = (await session.execute(select(User).where(User.telegram_id == data["target"]))).scalar_one_or_none()
    if not target: await message.answer("❌ Usuario inexistente."); await state.clear(); return
    if is_dueno(target): await message.answer("❌ El saldo del DUEÑO es infinito y no puede modificarse."); await state.clear(); return
    sign = 1 if data["kind"] == "add" else -1
    if sign < 0 and money(target.balance) < amount: await message.answer("❌ El saldo no puede quedar negativo."); return
    await state.update_data(amount=str(amount))
    await message.answer(f"⚠️ <b>CONFIRMACIÓN</b>\n\n👤 Usuario: {name_of(target)}\n💰 Saldo actual: {m(target.balance)}\n{'➕' if sign > 0 else '➖'} Cantidad: {m(amount)}\n💰 Nuevo saldo: {m(money(target.balance) + sign * amount)}", reply_markup=kb([[ ("✅ Confirmar", "admin:balance:confirm", None), ("❌ Cancelar", "admin:home", None) ]]))


@router.callback_query(F.data == "admin:balance:confirm")
async def admin_balance_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot, session: AsyncSession, current_user: User | None = None):
    actor = await check_admin(callback, session, current_user)
    if not is_owner_role(actor): await callback.answer("Solo OWNER o DUEÑO.", show_alert=True); return
    data = await state.get_data(); amount = money(data.get("amount")); sign = 1 if data.get("kind") == "add" else -1
    target = (await session.execute(select(User).where(User.telegram_id == data.get("target")).with_for_update())).scalar_one_or_none()
    if not target or is_dueno(target) or amount <= 0 or (sign < 0 and money(target.balance) < amount): await callback.answer("Operación inválida.", show_alert=True); return
    target.balance = money(target.balance) + sign * amount
    session.add(BalanceTransaction(user_id=target.id, kind=BalanceTransactionType.CREDIT if sign > 0 else BalanceTransactionType.DEBIT, amount=sign * amount, balance_after=target.balance, reference=str(actor.telegram_id)))
    await log_event(session, actor.telegram_id, "balance_change", str(target.telegram_id), f"{sign * amount}"); await session.commit(); await state.clear()
    try:
        await bot.send_message(target.telegram_id, f"💰 <b>{'SALDO USD RECIBIDO' if sign > 0 else 'SALDO USD DESCONTADO'}</b>\n\nMovimiento: {'+' if sign > 0 else '-'}{m(amount)} USD\nNuevo saldo: {m(target.balance)} USD")
    except (TelegramForbiddenError, TelegramBadRequest):
        logger.warning("No se pudo notificar al usuario %s sobre el cambio de saldo.", target.telegram_id)
    await edit_or_answer(callback, f"✅ <b>{'SALDO USD ENTREGADO' if sign > 0 else 'SALDO USD DESCONTADO'}</b>.\n\nNuevo saldo: {m(target.balance)} USD", nav(True, "admin:home"))


@router.callback_query(F.data.startswith("admin:premium:"))
async def admin_premium(callback: CallbackQuery, bot: Bot, session: AsyncSession, current_user: User | None = None):
    actor = await check_admin(callback, session, current_user)
    if not is_owner_role(actor): await callback.answer("Solo OWNER o DUEÑO.", show_alert=True); return
    _, _, action, raw = callback.data.split(":")
    target = (await session.execute(select(User).where(User.telegram_id == int(raw)).with_for_update())).scalar_one_or_none()
    if not target: await callback.answer("Usuario no encontrado.", show_alert=True); return
    target.is_premium = action == "on"; target.premium_until = None
    if action == "on":
        target.role = UserRole.PREMIUN
    elif target.role == UserRole.PREMIUN:
        target.role = UserRole.SOCIO if target.is_partner else UserRole.USUARIO
    await log_event(session, actor.telegram_id, "premium_change", raw, action); await session.commit()
    await bot.send_message(target.telegram_id, f"💎 PREMIUN {'activado' if action == 'on' else 'desactivado'} · {'10% OFF' if action == 'on' else 'beneficio retirado'}.")
    await edit_or_answer(callback, "✅ Estado Premium actualizado.", nav(True, "admin:home"))


@router.callback_query(F.data.startswith("admin:ban:"))
async def admin_ban_confirm(callback: CallbackQuery, session: AsyncSession, current_user: User | None = None):
    actor = await check_admin(callback, session, current_user)
    if not is_owner_role(actor): await callback.answer("Solo OWNER o DUEÑO.", show_alert=True); return
    _, _, action, raw = callback.data.split(":")
    await edit_or_answer(callback, f"⚠️ ¿Confirmar {'baneo' if action == 'on' else 'desbaneo'} del usuario <code>{raw}</code>?", kb([[ ("✅ Confirmar", f"admin:banconfirm:{action}:{raw}", None), ("❌ Cancelar", "admin:home", None) ]]))


@router.callback_query(F.data.startswith("admin:banconfirm:"))
async def admin_ban_apply(callback: CallbackQuery, bot: Bot, session: AsyncSession, current_user: User | None = None):
    actor = await check_admin(callback, session, current_user)
    if not is_owner_role(actor): await callback.answer("Solo OWNER o DUEÑO.", show_alert=True); return
    _, _, action, raw = callback.data.split(":")
    target = (await session.execute(select(User).where(User.telegram_id == int(raw)).with_for_update())).scalar_one_or_none()
    if not target: await callback.answer("Usuario no encontrado.", show_alert=True); return
    if target.telegram_id == settings.OWNER_ID or (target.role in (UserRole.ADMIN, UserRole.OWNER, UserRole.DUENO) and not is_owner(actor)):
        await callback.answer("Ese usuario está protegido.", show_alert=True); return
    target.is_banned = action == "on"; target.ban_reason = "Restricción administrativa permanente" if target.is_banned else None
    await log_event(session, actor.telegram_id, "user_ban_permanent" if target.is_banned else "user_unban", raw, action); await session.commit()
    if target.is_banned:
        await bot.send_message(target.telegram_id, BANNED_TEXT, reply_markup=BANNED_MARKUP, disable_web_page_preview=True)
    else:
        await bot.send_message(target.telegram_id, "✅ Tu acceso a LXZ STORE ha sido restablecido.")
    await edit_or_answer(callback, "✅ Estado de seguridad actualizado.", nav(True, "admin:home"))


@router.callback_query(F.data == "admin:products")
async def admin_products(callback: CallbackQuery, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    actor = await check_admin(callback, session, current_user)
    if not is_owner_role(actor): return
    products = (await session.execute(select(Product).order_by(Product.id.desc()).limit(20))).scalars().all()
    rows = [[(f"{'🟢' if p.is_active else '🔴'} {p.name[:28]} · {m(p.price)} · stock {p.stock}", f"admin:product:{p.id}", None)] for p in products]
    rows.append([("➕ Crear producto", "admin:product:new", None), ("⬅️ Panel", "admin:home", None)] if can_manage_products(actor) else [("⬅️ Panel", "admin:home", None)])
    await edit_or_answer(callback, "📦 <b>ADMINISTRACIÓN DE PRODUCTOS</b>\n\nSelecciona un producto:", kb(rows))


@router.callback_query(F.data == "admin:product:new")
async def product_new(callback: CallbackQuery, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    actor = await check_admin(callback, session, current_user)
    if not can_manage_products(actor): await callback.answer("Solo ADMIN, OWNER o DUEÑO.", show_alert=True); return
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
    if not can_manage_products(actor): await state.clear(); return
    data = await state.get_data();     product = Product(name=data["name"], category=data["category"], description=data["description"], price=money(data["price"]), stock=int(data["stock"]), image_file_id=image_for_product(data["name"]), delivery_data=None if message.text.strip() == "-" else message.text.strip())
    session.add(product); await log_event(session, actor.telegram_id, "product_create", data["name"], "created"); await session.commit(); await state.clear(); await message.answer("✅ Producto creado correctamente.", reply_markup=nav(True, "admin:products"))


@router.callback_query(F.data.startswith("admin:product:stock:"))
async def product_stock_prompt(callback: CallbackQuery, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    actor = await check_admin(callback, session, current_user)
    if not can_manage_products(actor): await callback.answer("Solo ADMIN, OWNER o DUEÑO.", show_alert=True); return
    await state.set_state(ProductEdit.value); await state.update_data(edit="stock", product_id=int(callback.data.split(":")[3]))
    await edit_or_answer(callback, "📊 Escribe el nuevo stock entero (0 o más):")


@router.callback_query(F.data.startswith("admin:product:price:"))
async def product_price_prompt(callback: CallbackQuery, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    actor = await check_admin(callback, session, current_user)
    if not can_manage_products(actor): await callback.answer("Solo ADMIN, OWNER o DUEÑO.", show_alert=True); return
    await state.set_state(ProductEdit.value); await state.update_data(edit="price", product_id=int(callback.data.split(":")[3]))
    await edit_or_answer(callback, "💵 Escribe el nuevo precio mayor que cero:")


@router.callback_query(F.data.startswith("admin:product:image:"))
async def product_image_prompt(callback: CallbackQuery, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    actor = await check_admin(callback, session, current_user)
    if not can_manage_products(actor): await callback.answer("Solo ADMIN, OWNER o DUEÑO.", show_alert=True); return
    await state.set_state(ProductEdit.value); await state.update_data(edit="image", product_id=int(callback.data.split(":")[3]))
    await edit_or_answer(callback, "🖼️ Envía la nueva imagen para este producto (o envía '-' para eliminar la imagen actual):")


@router.callback_query(F.data.startswith("admin:product:delivery:"))
async def product_delivery_prompt(callback: CallbackQuery, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    actor = await check_admin(callback, session, current_user)
    if not can_manage_products(actor): await callback.answer("Solo ADMIN, OWNER o DUEÑO.", show_alert=True); return
    await state.set_state(ProductEdit.value); await state.update_data(edit="delivery", product_id=int(callback.data.split(":")[3]))
    await edit_or_answer(callback, "📦 Escribe los nuevos datos de entrega (cuentas, enlaces, instrucciones) o envía '-' para dejarlos vacíos:")


@router.message(ProductEdit.value)
async def product_edit_value(message: Message, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    actor = await event_user(message, session, current_user)
    if not can_manage_products(actor): await state.clear(); return
    data = await state.get_data(); product = (await session.execute(select(Product).where(Product.id == data.get("product_id")).with_for_update())).scalar_one_or_none()
    if not product: await state.clear(); await message.answer("❌ Producto inexistente."); return
    edit_type = data.get("edit")
    if edit_type == "stock":
        if not message.text: await message.answer("❌ Formato inválido."); return
        try: value = int(message.text.strip())
        except ValueError: await message.answer("❌ Stock inválido."); return
        if value < 0: await message.answer("❌ El stock no puede ser negativo."); return
        product.stock = value
        product.is_active = bool(value > 0 and product.price > 0)
    elif edit_type == "price":
        if not message.text: await message.answer("❌ Formato inválido."); return
        value = money(message.text)
        if value <= 0: await message.answer("❌ Precio inválido."); return
        product.price = value
    elif edit_type == "delivery":
        if not message.text: await message.answer("❌ Formato inválido."); return
        product.delivery_data = None if message.text.strip() == "-" else message.text.strip()
    elif edit_type == "image":
        if message.text and message.text.strip() == "-":
            product.image_file_id = None
        elif message.photo:
            product.image_file_id = message.photo[-1].file_id
        else:
            await message.answer("❌ Debes enviar una imagen válida o '-'.")
            return
    await log_event(session, actor.telegram_id, "product_edit", str(product.id), edit_type or "value")
    await session.commit(); await state.clear(); await message.answer("✅ Producto actualizado.", reply_markup=nav(True, "admin:products"))


@router.callback_query(F.data.regexp(r"^admin:product:\d+$"))
async def admin_product_detail(callback: CallbackQuery, session: AsyncSession, current_user: User | None = None):
    actor = await check_admin(callback, session, current_user)
    if not actor: return
    raw = callback.data.split(":")[2]
    if raw == "new": return
    product = (await session.execute(select(Product).where(Product.id == int(raw)))).scalar_one_or_none()
    if not product: await callback.answer("Producto inexistente.", show_alert=True); return
    rows = []
    if can_manage_products(actor):
        rows.extend([
            [("🟢 Activar" if not product.is_active else "🔴 Desactivar", f"admin:product:toggle:{product.id}", None), ("🗑️ Eliminar", f"admin:product:delete:{product.id}", None)],
            [("📊 Modificar stock", f"admin:product:stock:{product.id}", None), ("💵 Cambiar precio", f"admin:product:price:{product.id}", None)],
            [("🖼️ Cambiar imagen", f"admin:product:image:{product.id}", None), ("📦 Cambiar entrega", f"admin:product:delivery:{product.id}", None)],
        ])
    rows.append([ ("⬅️ Productos", "admin:products", None) ])
    await edit_or_answer(callback, f"📦 <b>{product.name}</b>\n\nCategoría: {product.category}\nDescripción: {product.description}\nPrecio: {m(product.price)}\nStock: {product.stock}\nEstado: {'Activo' if product.is_active else 'Inactivo'}\nVentas: {product.sales_count}", kb(rows))


@router.callback_query(F.data.startswith("admin:product:toggle:"))
async def product_toggle(callback: CallbackQuery, session: AsyncSession, current_user: User | None = None):
    actor = await check_admin(callback, session, current_user)
    if not can_manage_products(actor): await callback.answer("Solo ADMIN, OWNER o DUEÑO.", show_alert=True); return
    product = (await session.execute(select(Product).where(Product.id == int(callback.data.split(":")[3])).with_for_update())).scalar_one_or_none()
    if not product:
        await callback.answer("Producto inexistente.", show_alert=True)
        return
    if not product.is_active and (product.stock <= 0 or product.price <= 0):
        await callback.answer("No se puede activar sin stock y precio válidos.", show_alert=True)
        return
    product.is_active = not product.is_active
    new_state = "activado" if product.is_active else "desactivado"
    await log_event(session, actor.telegram_id, "product_toggle", str(product.id), str(product.is_active))
    await session.commit()
    await edit_or_answer(callback, f"✅ Producto {new_state} correctamente.\n\n📦 {product.name}\n💰 Precio: {m(product.price)}\n📊 Stock: {product.stock}", nav(True, "admin:products"))


@router.callback_query(F.data.startswith("admin:product:delete:"))
async def product_delete(callback: CallbackQuery, session: AsyncSession, current_user: User | None = None):
    actor = await check_admin(callback, session, current_user)
    if not can_manage_products(actor): await callback.answer("Solo ADMIN, OWNER o DUEÑO.", show_alert=True); return
    product = (await session.execute(select(Product).where(Product.id == int(callback.data.split(":")[3])).with_for_update())).scalar_one_or_none()
    if product: product.is_active = False; await log_event(session, actor.telegram_id, "product_delete", str(product.id), "archived"); await session.commit()
    await edit_or_answer(callback, "✅ Producto archivado. Las compras históricas se conservan.", nav(True, "admin:products"))


@router.callback_query(F.data.startswith("admin:payments"))
async def admin_payments(callback: CallbackQuery, session: AsyncSession, current_user: User | None = None):
    if not await check_admin(callback, session, current_user): return
    requests = (await session.execute(select(TopupRequest).where(TopupRequest.status == TopupStatus.PENDING).order_by(TopupRequest.created_at).limit(10))).scalars().all()
    rows = [[(f"🟡 #{r.id} · {m(r.amount)} · {r.method}", f"topup:view:{r.id}", None)] for r in requests]
    rows.append([("⬅️ Panel Admin", "admin:home", None)])
    await edit_or_answer(callback, "💳 <b>PAGOS PENDIENTES</b>\n\n" + ("\n".join(f"#{r.id} · {m(r.amount)} · {r.method}" for r in requests) if requests else "No hay solicitudes pendientes."), kb(rows))


@router.callback_query(F.data.startswith("topup:view:"))
async def topup_view(callback: CallbackQuery, session: AsyncSession, current_user: User | None = None):
    actor = await check_admin(callback, session, current_user)
    if not actor: return
    request = (await session.execute(select(TopupRequest).where(TopupRequest.id == int(callback.data.split(":")[2])))).scalar_one_or_none()
    if not request: await callback.answer("Solicitud inexistente.", show_alert=True); return
    rows = [[("⬅️ Pagos", "admin:payments", None)]]
    if is_admin(actor): rows.insert(0, [("✅ Aprobar", f"topup:approve:{request.id}", None), ("❌ Rechazar", f"topup:reject:{request.id}", None)])
    await edit_or_answer(callback, f"🧾 <b>SOLICITUD #{request.id}</b>\n\nMonto: {m(request.amount)}\nMétodo: {request.method}\nEstado: {request.status.value}\nFecha: {now_text(request.created_at)}\n\nEl comprobante fue enviado al canal administrativo al registrarse.", kb(rows))


@router.callback_query(F.data == "admin:coupons")
async def admin_coupons(callback: CallbackQuery, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    actor = await check_admin(callback, session, current_user)
    if not is_owner_role(actor): await callback.answer("Solo OWNER o DUEÑO.", show_alert=True); return
    coupons = (await session.execute(select(Coupon).order_by(Coupon.id.desc()).limit(15))).scalars().all()
    await state.set_state(CouponAdminFlow.code)
    await edit_or_answer(callback, "🎟️ <b>CUPONES</b>\n\n" + ("\n".join(f"{c.code} · {'activo' if c.is_active else 'inactivo'} · {c.used_count}/{c.usage_limit or '∞'}" for c in coupons) if coupons else "No hay cupones.") + "\n\nEscribe un código nuevo para crearlo, o /start.")


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
    if not is_owner_role(actor): await state.clear(); return
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
    actor = await check_admin(callback, session, current_user)
    if not actor or not is_owner_role(actor): await callback.answer("Solo OWNER o DUEÑO.", show_alert=True); return
    await state.set_state(BroadcastFlow.message); await edit_or_answer(callback, "📢 <b>DIFUSIÓN</b>\n\nEnvía el texto, foto, vídeo, documento o sticker que deseas copiar a usuarios no baneados. Usa /start para salir.")


@router.message(BroadcastFlow.message)
async def broadcast_preview(message: Message, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    actor = await event_user(message, session, current_user)
    if not is_owner_role(actor): await state.clear(); return
    await state.update_data(source_chat=message.chat.id, source_message=message.message_id)
    await message.answer("⚠️ ¿Confirmar difusión a todos los usuarios activos?", reply_markup=kb([[ ("✅ Confirmar", "admin:broadcast:confirm", None), ("❌ Cancelar", "admin:home", None) ]]))


@router.callback_query(F.data == "admin:broadcast:confirm")
async def broadcast_confirm(callback: CallbackQuery, bot: Bot, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    actor = await check_admin(callback, session, current_user)
    if not actor or not is_owner_role(actor): await callback.answer("Solo OWNER o DUEÑO.", show_alert=True); return
    data = await state.get_data(); users = (await session.execute(select(User.telegram_id).where(User.is_banned.is_(False)))).scalars().all(); sent = failed = 0
    await callback.answer("Difusión iniciada")
    for telegram_id in users:
        try:
            await bot.copy_message(telegram_id, data["source_chat"], data["source_message"]); sent += 1
        except (TelegramForbiddenError, TelegramBadRequest): failed += 1
        await asyncio.sleep(settings.BROADCAST_DELAY)
    await log_event(session, actor.telegram_id, "broadcast", None, f"sent={sent};failed={failed}"); await session.commit(); await state.clear()
    await callback.message.edit_text(f"📢 <b>DIFUSIÓN FINALIZADA</b>\n\n✅ Enviados: {sent}\n❌ Fallidos: {failed}", reply_markup=nav(True, "admin:home"))


class RankFlow(StatesGroup):
    target = State()
    role = State()

@router.callback_query(F.data == "owner:admins")
async def owner_admins(callback: CallbackQuery, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    actor = await check_admin(callback, session, current_user)
    if not actor or not is_owner(actor): return
    staff = (await session.execute(select(User).where(User.role.in_([UserRole.ADMIN, UserRole.OWNER, UserRole.DUENO, UserRole.SOCIO, UserRole.PREMIUN, UserRole.USUARIO])))).scalars().all()
    await state.set_state(RankFlow.target)
    await edit_or_answer(callback, "⚙️ <b>EQUIPO Y RANGOS</b>\n\n" + ("\n".join(f"• {name_of(a)} · {a.telegram_id} · {a.role.value}" for a in staff)) + "\n\nEscribe el ID de Telegram del usuario al que deseas cambiarle el rol o rango, o /start.")


@router.message(RankFlow.target, F.text)
async def owner_rank_target(message: Message, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    actor = await event_user(message, session, current_user)
    if not is_owner(actor): await state.clear(); return
    try: target_id = int(message.text.strip())
    except ValueError: await message.answer("❌ ID inválido."); return
    if target_id == settings.OWNER_ID: await message.answer("❌ No puedes modificar al Owner."); return
    target = (await session.execute(select(User).where(User.telegram_id == target_id))).scalar_one_or_none()
    if not target: await message.answer("❌ Usuario no encontrado."); return
    await state.update_data(target=target_id)
    await state.set_state(RankFlow.role)
    roles = kb([[('OWNER', 'role:owner', None), ('ADMIN', 'role:admin', None)], [('SOCIO', 'role:socio', None), ('PREMIUN', 'role:premiun', None)], [("USUARIO", "role:usuario", None)]])
    await message.answer(f"👤 {name_of(target)}\nRol actual: {target.role.value}\n\nSelecciona el nuevo rol del sistema:", reply_markup=roles)

@router.callback_query(F.data.startswith("role:"))
async def owner_rank_role(callback: CallbackQuery, state: FSMContext, session: AsyncSession, current_user: User | None = None):
    actor = await event_user(callback, session, current_user)
    if not is_owner(actor): await callback.answer("Solo Owner.", show_alert=True); return
    data = await state.get_data()
    if not data.get("target"): await callback.answer("Expirado.", show_alert=True); return
    role_key = callback.data.split(":")[1]
    role_options = {
        "dueno": UserRole.DUENO, "owner": UserRole.OWNER,
        "admin": UserRole.ADMIN, "socio": UserRole.SOCIO,
        "premiun": UserRole.PREMIUN, "usuario": UserRole.USUARIO,
    }
    selected_role = role_options.get(role_key)
    if selected_role is None:
        await callback.answer("Rol inválido.", show_alert=True); return
    target = (await session.execute(select(User).where(User.telegram_id == data["target"]).with_for_update())).scalar_one_or_none()
    if not target:
        await callback.answer("Usuario no encontrado.", show_alert=True)
        return
    if selected_role == UserRole.DUENO:
        await callback.answer("DUEÑO solo puede ser el usuario configurado en OWNER_ID.", show_alert=True)
        return
    target.role = selected_role
    await log_event(session, actor.telegram_id, "role_change", str(target.telegram_id), target.role.value)
    await session.commit()
    await state.clear()
    await edit_or_answer(callback, f"✅ Rol actualizado para {name_of(target)}.\n\n🎖️ Rango: {target.role.value}", nav(True, "owner:home"))

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
    if callback.data == "owner:config" and not is_owner(actor): await callback.answer("Solo Owner.", show_alert=True); return
    if not actor or not is_admin(actor): await callback.answer("Solo Administradores.", show_alert=True); return
    if callback.data == "admin:security": text = "🛡️ <b>SEGURIDAD</b>\n\nTodas las acciones administrativas vuelven a verificar el rol. Las compras y aprobaciones usan bloqueo de fila y estados para evitar duplicados."
    elif callback.data == "admin:credits": text = "💰 <b>SALDO USD</b>\n\nBusca un usuario desde Usuarios para agregar o quitar saldo con confirmación y registro de auditoría."
    else: text = f"🔧 <b>CONFIGURACIÓN</b>\n\nTienda: {settings.STORE_NAME}\nMoneda: {settings.CURRENCY}\nZona horaria: {settings.TIMEZONE}\nYape/Plin: {'configurado' if settings.YAPE_NUMBER or settings.PLIN_NUMBER else 'no configurado'}\nBinance: {'habilitado' if settings.BINANCE_USDT_ENABLED else 'deshabilitado'}"
    await edit_or_answer(callback, text, nav(True, "owner:home" if callback.data == "owner:config" else "admin:home"))


@router.callback_query(F.data == "product:search")
async def product_search_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ProductSearch.waiting); await edit_or_answer(callback, "🔎 Escribe el nombre del producto que buscas. /start para salir.")


@router.message(ProductSearch.waiting, F.text)
async def product_search(message: Message, state: FSMContext, session: AsyncSession):
    query = message.text.strip(); products = (await session.execute(select(Product).where(Product.is_active.is_(True), Product.name.ilike(f"%{query}%")).limit(10))).scalars().all()
    rows = [[(f"📦 {p.name} · {m(p.price)}", f"product:{p.id}", None)] for p in products]; rows.append([("⬅️ Catálogo", "menu:catalog", None)])
    await state.clear(); await message.answer(("🔎 <b>RESULTADOS</b>\n\n" + "\n".join(f"• {p.name} — {m(p.price)}" for p in products)) if products else "❌ No encontramos productos relacionados.", reply_markup=kb(rows))


@router.message(F.text)
async def client_ai(message: Message, bot: Bot, session: AsyncSession, current_user: User | None = None):
    user = await event_user(message, session, current_user)
    if user:
        await client_ai_answer(message, bot, session, user)


@router.callback_query()
async def fallback_callback(callback: CallbackQuery):
    await callback.answer("Esta opción ya no está disponible. Abre el menú principal.", show_alert=True)


# Arranque
# Importamos nuestros propios archivos y modelos

# Configuración para ver errores y mensajes en la consola de Railway
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

async def main() -> None:
    # Creamos las tablas SQLite automáticamente si no existen.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(migrate_schema)
    logger.info("📦 Tablas y migraciones de la base de datos verificadas/creadas con éxito.")
    async with async_session_maker() as seed_session:
        await seed_initial_products(seed_session)

    # FSM en memoria: no requiere Redis y reduce el consumo del plan gratuito.
    storage = MemoryStorage()

    # 2. Inicializamos el Bot de Telegram
    bot = Bot(
        token=settings.BOT_TOKEN,
        session=AiohttpSession(timeout=120),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=storage)

    # 3. Activamos los guardias de seguridad (Middlewares)
    dp.update.middleware(DatabaseMiddleware())
    dp.update.middleware(AuthMiddleware())

    # 4. Registramos los comandos (nuestro archivo start.py)
    dp.include_router(router)

    logger.info("⚡ LXZ STORE BEST iniciado correctamente en modo producción. version=%s", settings.APP_VERSION)

    try:
        # 5. Ponemos al bot a escuchar; Railway puede tener cortes transitorios.
        while True:
            try:
                await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
                break
            except (TelegramNetworkError, asyncio.TimeoutError) as exc:
                logger.warning("Conexión temporal con Telegram perdida: %s. Reintentando en 10 segundos.", exc)
                await asyncio.sleep(10)
    finally:
        # Apagado seguro si se reinicia el servidor
        await bot.session.close()
        await engine.dispose()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot detenido manualmente.")
