from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from database import (
    register_user,
    get_balance,
    get_user,
    is_admin,
    total_users
)

router = Router()

SUPPORT_URL = "https://t.me/StoreFixersXiters"
CHANNEL_URL = "https://t.me/StoreFixersXiters"

OWNER_ID = 7939709543

BANNER = "https://i.ibb.co/3m20gX28/51614.jpg"


# =========================
# MENÚ PRINCIPAL
# =========================

def main_menu(user_id: int):

    keyboard = [
        [
            InlineKeyboardButton(
                text="🛍️ Catálogo",
                callback_data="catalog"
            ),
            InlineKeyboardButton(
                text="👤 Mi Perfil",
                callback_data="profile"
            )
        ],

        [
            InlineKeyboardButton(
                text="💳 Recargar",
                callback_data="recharge"
            ),
            InlineKeyboardButton(
                text="🎟️ Cupones",
                callback_data="coupon"
            )
        ],

        [
            InlineKeyboardButton(
                text="💎 Premium",
                callback_data="premium"
            ),
            InlineKeyboardButton(
                text="📦 Compras",
                callback_data="history"
            )
        ],

        [
            InlineKeyboardButton(
                text="📞 Soporte",
                url=SUPPORT_URL
            ),
            InlineKeyboardButton(
                text="📢 Canal",
                url=CHANNEL_URL
            )
        ]
    ]

    if user_id == OWNER_ID:

        keyboard.append([
            InlineKeyboardButton(
                text="👑 Panel Owner",
                callback_data="owner"
            )
        ])

    elif is_admin(user_id):

        keyboard.append([
            InlineKeyboardButton(
                text="⚙️ Panel Admin",
                callback_data="admin"
            )
        ])

    return InlineKeyboardMarkup(
        inline_keyboard=keyboard
    )


# =========================
# TEXTO PRINCIPAL
# =========================

def home_text(message: Message):

    balance = get_balance(message.from_user.id)

    return f"""
<b>⚡ RAYO FIX STORE</b>

👋 Bienvenido <b>{message.from_user.first_name}</b>

🆔 <code>{message.from_user.id}</code>

💰 Saldo:
<b>${balance:.2f}</b>

💎 Membresía:
<b>Estándar</b>

━━━━━━━━━━━━━━━━━━

Selecciona una opción.
"""


# =========================
# START
# =========================

@router.message(CommandStart())
async def start(message: Message):

    register_user(
        message.from_user.id,
        message.from_user.first_name,
        message.from_user.username
    )

    await message.answer_photo(
        photo=BANNER,
        caption=home_text(message),
        reply_markup=main_menu(
            message.from_user.id
        )
    )


# =========================
# PERFIL
# =========================

@router.callback_query(F.data == "profile")
async def profile(callback: CallbackQuery):

    user = get_user(
        callback.from_user.id
    )

    premium = "Sí" if user["premium"] else "No"

    text = f"""
<b>👤 MI PERFIL</b>

👤 Nombre:
{user["first_name"]}

📛 Usuario:
@{user["username"] or "Sin username"}

🆔 ID:
<code>{user["user_id"]}</code>

💰 Saldo:
${user["balance"]:.2f}

💎 Premium:
{premium}

📅 Registro:
{user["register_date"]}
"""

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🏠 Inicio",
                    callback_data="home"
                )
            ]
        ]
    )

    await callback.answer()

    await callback.message.edit_caption(
        caption=text,
        reply_markup=keyboard
            )
# ==========================================
# CATÁLOGO
# ==========================================

ANDROID_PRODUCTS = [
    "🔥 DRIP CLIENT APK MOD",
    "🌐 DRIP CLIENT PROXY",
    "⚡ HG CHEATS",
    "🌍 HG CHEATS PROXY",
    "🎯 BR MODS",
    "🎮 Strick BR",
    "📦 CUBAN APK MOD",
    "🌎 CUBAN PROXY",
    "🚀 FFH4X"
]

IOS_PRODUCTS = [
    "💎 MONITE PRO",
    "⭐ MONITE BÁSICO",
    "📜 CERTIFICADOS",
    "🔒 PROXY POTATSO",
    "🍏 FLUCK IOS",
    "👑 HOLO VIP",
    "📱 ESIG ANUAL"
]


def catalog_menu():

    return InlineKeyboardMarkup(
        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text="📱 Android",
                    callback_data="android"
                )
            ],

            [
                InlineKeyboardButton(
                    text="🍎 iPhone / iOS",
                    callback_data="ios"
                )
            ],

            [
                InlineKeyboardButton(
                    text="🖥️ Windows / PC",
                    callback_data="windows"
                )
            ],

            [
                InlineKeyboardButton(
                    text="🏠 Inicio",
                    callback_data="home"
                )
            ]
        ]
    )


@router.callback_query(F.data == "catalog")
async def catalog(callback: CallbackQuery):

    await callback.answer()

    await callback.message.edit_caption(
        caption="""
<b>🛍️ CATÁLOGO OFICIAL</b>

Selecciona la plataforma que deseas visualizar.
""",
        reply_markup=catalog_menu()
    )


def back_catalog():

    return InlineKeyboardMarkup(
        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text="⬅️ Volver",
                    callback_data="catalog"
                )
            ],

            [
                InlineKeyboardButton(
                    text="🏠 Inicio",
                    callback_data="home"
                )
            ]

        ]
    )


@router.callback_query(F.data == "android")
async def android(callback: CallbackQuery):

    await callback.answer()

    text = "<b>📱 PRODUCTOS ANDROID</b>\n\n"

    for product in ANDROID_PRODUCTS:
        text += f"• {product}\n"

    await callback.message.edit_caption(
        caption=text,
        reply_markup=back_catalog()
    )


@router.callback_query(F.data == "ios")
async def ios(callback: CallbackQuery):

    await callback.answer()

    text = "<b>🍎 PRODUCTOS iPhone / iOS</b>\n\n"

    for product in IOS_PRODUCTS:
        text += f"• {product}\n"

    await callback.message.edit_caption(
        caption=text,
        reply_markup=back_catalog()
    )


@router.callback_query(F.data == "windows")
async def windows(callback: CallbackQuery):

    await callback.answer()

    await callback.message.edit_caption(
        caption="""
<b>🖥️ WINDOWS / PC</b>

🚧 Próximamente.

Actualmente no contamos con productos para Windows.

Vuelve pronto.
""",
        reply_markup=back_catalog()
    )


@router.callback_query(F.data == "home")
async def home(callback: CallbackQuery):

    await callback.answer()

    balance = get_balance(callback.from_user.id)

    await callback.message.edit_caption(
        caption=f"""
<b>⚡ RAYO FIX STORE</b>

👋 Bienvenido <b>{callback.from_user.first_name}</b>

🆔 <code>{callback.from_user.id}</code>

💰 Saldo:
<b>${balance:.2f}</b>

💎 Membresía:
<b>Estándar</b>

━━━━━━━━━━━━━━━━━━

Selecciona una opción.
""",
        reply_markup=main_menu(
            callback.from_user.id
        )
)
# ==========================================
# PREMIUM
# ==========================================

@router.callback_query(F.data == "premium")
async def premium(callback: CallbackQuery):

    await callback.answer()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💳 Comprar Premium",
                    callback_data="buy_premium"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏠 Inicio",
                    callback_data="home"
                )
            ]
        ]
    )

    await callback.message.edit_caption(
        caption="""
<b>💎 RAYO FIX PREMIUM</b>

✅ Descuentos exclusivos

✅ Atención prioritaria

✅ Acceso anticipado a nuevos productos

💰 Contacta con soporte para activarlo.
""",
        reply_markup=keyboard
    )


# ==========================================
# RECARGAS
# ==========================================

@router.callback_query(F.data == "recharge")
async def recharge(callback: CallbackQuery):

    await callback.answer()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📞 Contactar Soporte",
                    url=SUPPORT_URL
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏠 Inicio",
                    callback_data="home"
                )
            ]
        ]
    )

    await callback.message.edit_caption(
        caption="""
<b>💳 RECARGAR SALDO</b>

Métodos disponibles:

• Yape
• Plin
• Binance
• USDT

Después del pago envía tu comprobante al soporte.
""",
        reply_markup=keyboard
    )


# ==========================================
# CUPONES
# ==========================================

@router.callback_query(F.data == "coupon")
async def coupon(callback: CallbackQuery):

    await callback.answer()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🏠 Inicio",
                    callback_data="home"
                )
            ]
        ]
    )

    await callback.message.edit_caption(
        caption="""
<b>🎟️ CUPONES</b>

Esta función estará disponible próximamente.

Podrás canjear códigos promocionales.
""",
        reply_markup=keyboard
    )


# ==========================================
# HISTORIAL
# ==========================================

@router.callback_query(F.data == "history")
async def history(callback: CallbackQuery):

    await callback.answer()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🏠 Inicio",
                    callback_data="home"
                )
            ]
        ]
    )

    await callback.message.edit_caption(
        caption="""
<b>📦 MIS COMPRAS</b>

Todavía no tienes compras registradas.
""",
        reply_markup=keyboard
    )


# ==========================================
# OWNER
# ==========================================

@router.callback_query(F.data == "owner")
async def owner(callback: CallbackQuery):

    if callback.from_user.id != OWNER_ID:
        await callback.answer("Acceso denegado", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💰 Dar Saldo", callback_data="owner_add")
            ],
            [
                InlineKeyboardButton(text="💸 Quitar Saldo", callback_data="owner_remove")
            ],
            [
                InlineKeyboardButton(text="📊 Estadísticas", callback_data="owner_stats")
            ],
            [
                InlineKeyboardButton(text="🏠 Inicio", callback_data="home")
            ]
        ]
    )

    await callback.answer()

    await callback.message.edit_caption(
        caption="<b>👑 PANEL OWNER</b>",
        reply_markup=keyboard
    )


# ==========================================
# ADMIN
# ==========================================

@router.callback_query(F.data == "admin")
async def admin(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):
        await callback.answer("Acceso denegado", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📊 Estadísticas",
                    callback_data="admin_stats"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🏠 Inicio",
                    callback_data="home"
                )
            ]
        ]
    )

    await callback.answer()

    await callback.message.edit_caption(
        caption="<b>⚙️ PANEL ADMIN</b>",
        reply_markup=keyboard
    )


# ==========================================
# ESTADÍSTICAS OWNER
# ==========================================

@router.callback_query(F.data == "owner_stats")
async def owner_stats(callback: CallbackQuery):

    await callback.answer()

    await callback.message.edit_caption(
        caption=f"""
<b>📊 ESTADÍSTICAS</b>

👥 Usuarios registrados:
<b>{total_users()}</b>
""",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="⬅️ Volver",
                        callback_data="owner"
                    )
                ]
            ]
        )
    )
