# ============================================================
# FUNCTIONS.PY
# RAYO FIX STORE
# AIROGRAM 3.22
# ============================================================

import logging

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    FSInputFile
)

from database import (
    register_user,
    get_user,
    get_balance,
    is_admin,
    is_premium,
    total_users
)

router = Router()

logger = logging.getLogger(__name__)

# ============================================================
# CONFIGURACIÓN
# ============================================================

OWNER_ID = 7939709543

SUPPORT = "https://t.me/StoreFixersXiters"

CHANNEL = "https://t.me/StoreFixersXiters"

BANNER = "https://i.ibb.co/3m20gX28/51614.jpg"

BOT_NAME = "⚡ RAYO FIX STORE"

# ============================================================
# MENÚ PRINCIPAL
# ============================================================

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
                url=SUPPORT
            ),
            InlineKeyboardButton(
                text="📢 Canal",
                url=CHANNEL
            )
        ]
    ]

    if user_id == OWNER_ID:

        keyboard.append([
            InlineKeyboardButton(
                text="👑 PANEL OWNER",
                callback_data="owner"
            )
        ])

    elif is_admin(user_id):

        keyboard.append([
            InlineKeyboardButton(
                text="⚙️ PANEL ADMIN",
                callback_data="admin"
            )
        ])

    return InlineKeyboardMarkup(
        inline_keyboard=keyboard
    )

# ============================================================
# TEXTO PRINCIPAL
# ============================================================

def home_text(user):

    premium = "💎 PREMIUM" if user["premium"] else "👤 CLIENTE"

    return f"""
<b>⚡ RAYO FIX STORE</b>

━━━━━━━━━━━━━━━━━━

👋 Bienvenido <b>{user["first_name"]}</b>

🆔 ID:
<code>{user["user_id"]}</code>

💰 Saldo:
<b>${user["balance"]:.2f}</b>

🎖️ Rango:
{premium}

━━━━━━━━━━━━━━━━━━

Selecciona una opción del menú.
"""

# ============================================================
# /START
# ============================================================

@router.message(CommandStart())
async def start(message: Message):

    register_user(
        message.from_user.id,
        message.from_user.first_name,
        message.from_user.username
    )

    user = get_user(message.from_user.id)

    await message.answer_photo(
        photo=BANNER,
        caption=home_text(user),
        reply_markup=main_menu(
            message.from_user.id
        )
    )

# ============================================================
# /PING
# ============================================================

@router.message(Command("ping"))
async def ping(message: Message):

    await message.answer(
        "🏓 Pong\n\n✅ Bot funcionando correctamente."
    )

# ============================================================
# /ID
# ============================================================

@router.message(Command("id"))
async def myid(message: Message):

    await message.answer(
        f"🆔 Tu ID es:\n<code>{message.from_user.id}</code>"
    )

# ============================================================
# HOME
# ============================================================

@router.callback_query(F.data == "home")
async def home(callback: CallbackQuery):

    user = get_user(callback.from_user.id)

    await callback.answer()

    await callback.message.edit_caption(
        caption=home_text(user),
        reply_markup=main_menu(
            callback.from_user.id
        )
    )
# ============================================================
# CATÁLOGO
# ============================================================

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
    "👑 HOLO VIP",
    "📱 ESIG ANUAL",
    "🍏 FLUCK IOS",
    "🔒 PROXY POTATSO"
]


# ============================================================
# MENÚ CATÁLOGO
# ============================================================

def catalog_menu():

    return InlineKeyboardMarkup(
        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text="📱 Android",
                    callback_data="catalog_android"
                )
            ],

            [
                InlineKeyboardButton(
                    text="🍎 iPhone / iOS",
                    callback_data="catalog_ios"
                )
            ],

            [
                InlineKeyboardButton(
                    text="🖥️ Windows / PC",
                    callback_data="catalog_windows"
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


# ============================================================
# ABRIR CATÁLOGO
# ============================================================

@router.callback_query(F.data == "catalog")
async def catalog(callback: CallbackQuery):

    await callback.answer()

    await callback.message.edit_caption(

        caption="""
<b>🛍️ CATÁLOGO OFICIAL</b>

━━━━━━━━━━━━━━━━━━

Selecciona la plataforma.

📱 Android

🍎 iPhone / iOS

🖥️ Windows / PC
""",

        reply_markup=catalog_menu()

    )


# ============================================================
# BOTÓN VOLVER
# ============================================================

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


# ============================================================
# ANDROID
# ============================================================

@router.callback_query(F.data == "catalog_android")
async def catalog_android(callback: CallbackQuery):

    await callback.answer()

    text = "<b>📱 PRODUCTOS ANDROID</b>\n\n"

    for product in ANDROID_PRODUCTS:

        text += f"• {product}\n"

    text += "\n━━━━━━━━━━━━━━━━━━\n"

    text += "💬 Selecciona un producto en la siguiente actualización."

    await callback.message.edit_caption(

        caption=text,

        reply_markup=back_catalog()

    )


# ============================================================
# IOS
# ============================================================

@router.callback_query(F.data == "catalog_ios")
async def catalog_ios(callback: CallbackQuery):

    await callback.answer()

    text = "<b>🍎 PRODUCTOS iPhone / iOS</b>\n\n"

    for product in IOS_PRODUCTS:

        text += f"• {product}\n"

    text += "\n━━━━━━━━━━━━━━━━━━\n"

    text += "💬 Selecciona un producto en la siguiente actualización."

    await callback.message.edit_caption(

        caption=text,

        reply_markup=back_catalog()

    )


# ============================================================
# WINDOWS
# ============================================================

@router.callback_query(F.data == "catalog_windows")
async def catalog_windows(callback: CallbackQuery):

    await callback.answer()

    await callback.message.edit_caption(

        caption="""
<b>🖥️ WINDOWS / PC</b>

━━━━━━━━━━━━━━━━━━

🚧 Próximamente.

Actualmente no contamos con productos para Windows.

Mantente atento a futuras actualizaciones.
""",

        reply_markup=back_catalog()

)
# ============================================================
# PERFIL
# ============================================================

@router.callback_query(F.data == "profile")
async def profile(callback: CallbackQuery):

    await callback.answer()

    user = get_user(callback.from_user.id)

    premium = "✅ Activo" if user["premium"] else "❌ No"

    text = f"""
<b>👤 MI PERFIL</b>

━━━━━━━━━━━━━━━━━━

👤 Nombre:
<b>{user["first_name"]}</b>

📛 Usuario:
@{user["username"] or "Sin username"}

🆔 ID:
<code>{user["user_id"]}</code>

💰 Saldo:
<b>${user["balance"]:.2f}</b>

💎 Premium:
{premium}

🛒 Compras:
{user["total_purchases"]}

💵 Total Gastado:
${user["total_spent"]:.2f}

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

    await callback.message.edit_caption(
        caption=text,
        reply_markup=keyboard
    )


# ============================================================
# PREMIUM
# ============================================================

@router.callback_query(F.data == "premium")
async def premium(callback: CallbackQuery):

    await callback.answer()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💎 Comprar Premium",
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

━━━━━━━━━━━━━━━━━━

✔ Descuentos exclusivos

✔ Prioridad en soporte

✔ Acceso anticipado a productos

✔ Beneficios especiales

Contacta al soporte para activar tu membresía.
""",
        reply_markup=keyboard
    )


# ============================================================
# RECARGAS
# ============================================================

@router.callback_query(F.data == "recharge")
async def recharge(callback: CallbackQuery):

    await callback.answer()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💬 Contactar Soporte",
                    url=SUPPORT
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

━━━━━━━━━━━━━━━━━━

Métodos disponibles:

💙 Yape

💚 Plin

🟡 Binance

🟢 USDT

Después del pago envía tu comprobante al soporte.
""",
        reply_markup=keyboard
    )


# ============================================================
# CUPONES
# ============================================================

@router.callback_query(F.data == "coupon")
async def coupon(callback: CallbackQuery):

    await callback.answer()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎟️ Canjear Cupón",
                    callback_data="redeem_coupon"
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
<b>🎟️ CUPONES</b>

━━━━━━━━━━━━━━━━━━

Canjea un cupón promocional para obtener saldo o beneficios.

Presiona el botón de abajo para comenzar.
""",
        reply_markup=keyboard
    )


# ============================================================
# HISTORIAL
# ============================================================

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
<b>📦 HISTORIAL DE COMPRAS</b>

━━━━━━━━━━━━━━━━━━

Aquí aparecerán todas tus compras realizadas.

Actualmente no tienes compras registradas.
""",
        reply_markup=keyboard
    )


# ============================================================
# COMPRAR PREMIUM
# ============================================================

@router.callback_query(F.data == "buy_premium")
async def buy_premium(callback: CallbackQuery):

    await callback.answer(
        "Contacta al soporte para activar Premium.",
        show_alert=True
    )
    # ============================================================
# INICIO / HOME
# ============================================================

@router.callback_query(F.data == "home")
async def home(callback: CallbackQuery):

    await callback.answer()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👤 Mi Perfil",
                    callback_data="profile"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🛒 Productos",
                    callback_data="products"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💎 Premium",
                    callback_data="premium"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💳 Recargar",
                    callback_data="recharge"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎟️ Cupones",
                    callback_data="coupon"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🆘 Soporte",
                    callback_data="support"
                )
            ]
        ]
    )


    await callback.message.edit_caption(
        caption="""
<b>⚡ RAYO FIX</b>

━━━━━━━━━━━━━━━━━━

Bienvenido al panel principal.

Selecciona una opción:

👤 Perfil
🛒 Productos
💎 Premium
💳 Recargas
🎟️ Cupones
🆘 Soporte

━━━━━━━━━━━━━━━━━━
<b>Servicio rápido y seguro</b>
""",
        reply_markup=keyboard
    )



# ============================================================
# SOPORTE
# ============================================================

@router.callback_query(F.data == "support")
async def support(callback: CallbackQuery):

    await callback.answer()


    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💬 Contactar Soporte",
                    url=SUPPORT
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
<b>🆘 SOPORTE</b>

━━━━━━━━━━━━━━━━━━

¿Necesitas ayuda?

Puedes contactar con nuestro equipo para:

✔ Problemas con compras

✔ Recargas

✔ Activación Premium

✔ Consultas generales

Estamos disponibles para ayudarte.
""",
        reply_markup=keyboard
    )



# ============================================================
# CANAL OFICIAL
# ============================================================

@router.callback_query(F.data == "channel")
async def channel(callback: CallbackQuery):

    await callback.answer()


    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📢 Entrar al Canal",
                    url=CHANNEL
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
<b>📢 CANAL OFICIAL</b>

━━━━━━━━━━━━━━━━━━

Únete a nuestro canal oficial para:

🔥 Noticias

🔥 Nuevos productos

🔥 Promociones

🔥 Avisos importantes
""",
        reply_markup=keyboard
    )



# ============================================================
# AYUDA
# ============================================================

@router.callback_query(F.data == "help")
async def help_menu(callback: CallbackQuery):

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
<b>❓ AYUDA</b>

━━━━━━━━━━━━━━━━━━

¿Cómo funciona el bot?

1️⃣ Recarga saldo

2️⃣ Elige un producto

3️⃣ Realiza tu compra

4️⃣ Recibe tu pedido

Si tienes problemas contacta soporte.
""",
        reply_markup=keyboard
    )



# ============================================================
# ERROR SI USUARIO NO EXISTE
# ============================================================

async def check_user(user_id):

    user = get_user(user_id)

    if not user:
        return False

    return True
    # ============================================================
# PRODUCTOS
# ============================================================

@router.callback_query(F.data == "products")
async def products(callback: CallbackQuery):

    await callback.answer()


    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📦 Producto 1",
                    callback_data="product_1"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📦 Producto 2",
                    callback_data="product_2"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📦 Producto 3",
                    callback_data="product_3"
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
<b>🛒 CATÁLOGO DE PRODUCTOS</b>

━━━━━━━━━━━━━━━━━━

Selecciona un producto para ver detalles.

📦 Productos disponibles:
""",
        reply_markup=keyboard
    )



# ============================================================
# PRODUCTO 1
# ============================================================

@router.callback_query(F.data == "product_1")
async def product_1(callback: CallbackQuery):

    await callback.answer()


    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛒 Comprar",
                    callback_data="buy_product_1"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Volver",
                    callback_data="products"
                )
            ]
        ]
    )


    await callback.message.edit_caption(
        caption="""
<b>📦 PRODUCTO 1</b>

━━━━━━━━━━━━━━━━━━

📌 Descripción:
Producto disponible.

💰 Precio:
<b>$10.00</b>

Estado:
🟢 Disponible

¿Deseas comprarlo?
""",
        reply_markup=keyboard
    )



# ============================================================
# PRODUCTO 2
# ============================================================

@router.callback_query(F.data == "product_2")
async def product_2(callback: CallbackQuery):

    await callback.answer()


    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛒 Comprar",
                    callback_data="buy_product_2"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Volver",
                    callback_data="products"
                )
            ]
        ]
    )


    await callback.message.edit_caption(
        caption="""
<b>📦 PRODUCTO 2</b>

━━━━━━━━━━━━━━━━━━

📌 Descripción:
Producto disponible.

💰 Precio:
<b>$20.00</b>

Estado:
🟢 Disponible
""",
        reply_markup=keyboard
    )



# ============================================================
# PRODUCTO 3
# ============================================================

@router.callback_query(F.data == "product_3")
async def product_3(callback: CallbackQuery):

    await callback.answer()


    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛒 Comprar",
                    callback_data="buy_product_3"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Volver",
                    callback_data="products"
                )
            ]
        ]
    )


    await callback.message.edit_caption(
        caption="""
<b>📦 PRODUCTO 3</b>

━━━━━━━━━━━━━━━━━━

📌 Descripción:
Producto disponible.

💰 Precio:
<b>$30.00</b>

Estado:
🟢 Disponible
""",
        reply_markup=keyboard
)
    # ============================================================
# COMPRAR PRODUCTO 1
# ============================================================

@router.callback_query(F.data == "buy_product_1")
async def buy_product_1(callback: CallbackQuery):

    await callback.answer()

    user_id = callback.from_user.id

    product = "Producto 1"
    price = 10.00


    user = get_user(user_id)


    if not user:
        await callback.answer(
            "❌ Usuario no registrado",
            show_alert=True
        )
        return


    if user["balance"] < price:

        await callback.answer(
            "❌ Saldo insuficiente",
            show_alert=True
        )
        return



    new_balance = user["balance"] - price


    update_balance(
        user_id,
        new_balance
    )


    add_purchase(
        user_id,
        product,
        price
    )


    await callback.message.edit_caption(
        caption=f"""
<b>✅ COMPRA EXITOSA</b>

━━━━━━━━━━━━━━━━━━

📦 Producto:
<b>{product}</b>

💵 Precio:
${price:.2f}

💰 Nuevo saldo:
${new_balance:.2f}

Gracias por tu compra.
""",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🛒 Seguir comprando",
                        callback_data="products"
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
    )



# ============================================================
# COMPRAR PRODUCTO 2
# ============================================================

@router.callback_query(F.data == "buy_product_2")
async def buy_product_2(callback: CallbackQuery):

    await callback.answer()

    user_id = callback.from_user.id

    product = "Producto 2"
    price = 20.00


    user = get_user(user_id)


    if user["balance"] < price:

        await callback.answer(
            "❌ Saldo insuficiente",
            show_alert=True
        )
        return



    new_balance = user["balance"] - price


    update_balance(
        user_id,
        new_balance
    )


    add_purchase(
        user_id,
        product,
        price
    )


    await callback.message.edit_caption(
        caption=f"""
<b>✅ COMPRA EXITOSA</b>

━━━━━━━━━━━━━━━━━━

📦 Producto:
<b>{product}</b>

💵 Precio:
${price:.2f}

💰 Nuevo saldo:
${new_balance:.2f}
""",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🛒 Productos",
                        callback_data="products"
                    )
                ]
            ]
        )
    )



# ============================================================
# COMPRAR PRODUCTO 3
# ============================================================

@router.callback_query(F.data == "buy_product_3")
async def buy_product_3(callback: CallbackQuery):

    await callback.answer()

    user_id = callback.from_user.id

    product = "Producto 3"
    price = 30.00


    user = get_user(user_id)


    if user["balance"] < price:

        await callback.answer(
            "❌ Saldo insuficiente",
            show_alert=True
        )
        return



    new_balance = user["balance"] - price


    update_balance(
        user_id,
        new_balance
    )


    add_purchase(
        user_id,
        product,
        price
    )


    await callback.message.edit_caption(
        caption=f"""
<b>✅ COMPRA EXITOSA</b>

━━━━━━━━━━━━━━━━━━

📦 Producto:
<b>{product}</b>

💵 Precio:
${price:.2f}

💰 Nuevo saldo:
${new_balance:.2f}

Compra registrada correctamente.
""",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🏠 Inicio",
                        callback_data="home"
                    )
                ]
            ]
        )
)
    # ============================================================
# FUNCIÓN GENERAL DE COMPRA
# ============================================================

async def process_purchase(
    callback: CallbackQuery,
    product_name: str,
    price: float
):

    user_id = callback.from_user.id


    user = get_user(user_id)


    if not user:

        await callback.answer(
            "❌ Usuario no registrado",
            show_alert=True
        )
        return



    if user["balance"] < price:

        await callback.answer(
            "❌ No tienes saldo suficiente",
            show_alert=True
        )
        return



    new_balance = user["balance"] - price



    update_balance(
        user_id,
        new_balance
    )


    add_purchase(
        user_id,
        product_name,
        price
    )



    await callback.message.edit_caption(
        caption=f"""
<b>✅ COMPRA COMPLETADA</b>

━━━━━━━━━━━━━━━━━━

📦 Producto:
<b>{product_name}</b>

💵 Precio:
<b>${price:.2f}</b>

💰 Saldo restante:
<b>${new_balance:.2f}</b>


🧾 Compra registrada correctamente.

Gracias por confiar en RAYO FIX ⚡
""",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🛒 Más productos",
                        callback_data="products"
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
    )



# ============================================================
# COMPRA PRODUCTO 1
# ============================================================

@router.callback_query(F.data == "buy_product_1")
async def buy_product_1(callback: CallbackQuery):

    await callback.answer()

    await process_purchase(
        callback,
        "Producto 1",
        10.00
    )



# ============================================================
# COMPRA PRODUCTO 2
# ============================================================

@router.callback_query(F.data == "buy_product_2")
async def buy_product_2(callback: CallbackQuery):

    await callback.answer()

    await process_purchase(
        callback,
        "Producto 2",
        20.00
    )



# ============================================================
# COMPRA PRODUCTO 3
# ============================================================

@router.callback_query(F.data == "buy_product_3")
async def buy_product_3(callback: CallbackQuery):

    await callback.answer()

    await process_purchase(
        callback,
        "Producto 3",
        30.00
)
    # ============================================================
# COMPRA CON ENTREGA AUTOMÁTICA
# ============================================================

async def process_purchase_delivery(
    callback: CallbackQuery,
    product_id: int,
    product_name: str,
    price: float
):

    user_id = callback.from_user.id


    # Buscar usuario

    user = get_user(user_id)


    if not user:

        await callback.answer(
            "❌ Usuario no registrado",
            show_alert=True
        )
        return



    # Revisar saldo

    if user["balance"] < price:

        await callback.answer(
            "❌ Saldo insuficiente",
            show_alert=True
        )
        return



    # Revisar stock

    stock = get_product_stock(product_id)


    if stock <= 0:

        await callback.answer(
            "❌ Producto agotado",
            show_alert=True
        )
        return



    # Obtener producto disponible

    item = get_available_item(product_id)


    if not item:

        await callback.answer(
            "❌ No hay entregas disponibles",
            show_alert=True
        )
        return



    # Descontar saldo

    new_balance = user["balance"] - price


    update_balance(
        user_id,
        new_balance
    )



    # Marcar producto entregado

    mark_item_sold(
        item["id"],
        user_id
    )



    # Registrar compra

    add_purchase(
        user_id,
        product_name,
        price
    )



    # Enviar entrega

    await callback.message.answer(
        f"""
<b>🎉 COMPRA EXITOSA</b>

━━━━━━━━━━━━━━━━━━

📦 Producto:
<b>{product_name}</b>

💳 Precio:
${price:.2f}

💰 Saldo restante:
${new_balance:.2f}


🔐 Tu entrega:

<code>{item["content"]}</code>


⚡ Gracias por comprar en RAYO FIX
"""
    )


    await callback.message.edit_caption(
        caption="""
<b>✅ Pedido completado</b>

Tu producto fue enviado correctamente.
""",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🛒 Comprar más",
                        callback_data="products"
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
    )



# ============================================================
# PRODUCTO 1 ENTREGA
# ============================================================

@router.callback_query(F.data == "buy_product_1")
async def buy_product_1(callback: CallbackQuery):

    await callback.answer()

    await process_purchase_delivery(
        callback,
        1,
        "Producto 1",
        10.00
    )



# ============================================================
# PRODUCTO 2 ENTREGA
# ============================================================

@router.callback_query(F.data == "buy_product_2")
async def buy_product_2(callback: CallbackQuery):

    await callback.answer()

    await process_purchase_delivery(
        callback,
        2,
        "Producto 2",
        20.00
    )



# ============================================================
# PRODUCTO 3 ENTREGA
# ============================================================

@router.callback_query(F.data == "buy_product_3")
async def buy_product_3(callback: CallbackQuery):

    await callback.answer()

    await process_purchase_delivery(
        callback,
        3,
        "Producto 3",
        30.00
    )
    # ============================================================
# PANEL ADMIN
# ============================================================

@router.callback_query(F.data == "admin")
async def admin_panel(callback: CallbackQuery):

    await callback.answer()


    if callback.from_user.id != OWNER_ID:

        await callback.answer(
            "❌ No tienes permisos.",
            show_alert=True
        )
        return



    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👥 Usuarios",
                    callback_data="admin_users"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📊 Estadísticas",
                    callback_data="admin_stats"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💰 Agregar Saldo",
                    callback_data="add_balance"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📦 Stock",
                    callback_data="admin_stock"
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
<b>👑 PANEL ADMINISTRADOR</b>

━━━━━━━━━━━━━━━━━━

Bienvenido al panel de control.

Gestiona usuarios,
productos y ventas.
""",
        reply_markup=keyboard
    )



# ============================================================
# LISTA DE USUARIOS
# ============================================================

@router.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery):

    await callback.answer()


    if callback.from_user.id != OWNER_ID:
        return



    users = get_all_users()


    text = """
<b>👥 USUARIOS</b>

━━━━━━━━━━━━━━━━━━

"""


    if not users:

        text += "No hay usuarios registrados."

    else:

        for user in users[:10]:

            text += f"""
👤 {user['first_name']}

🆔 {user['user_id']}

💰 ${user['balance']}

━━━━━━━━━━
"""



    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Admin",
                    callback_data="admin"
                )
            ]
        ]
    )


    await callback.message.edit_caption(
        caption=text,
        reply_markup=keyboard
    )



# ============================================================
# ESTADÍSTICAS
# ============================================================

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):

    await callback.answer()


    if callback.from_user.id != OWNER_ID:
        return



    stats = get_statistics()



    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Admin",
                    callback_data="admin"
                )
            ]
        ]
    )


    await callback.message.edit_caption(
        caption=f"""
<b>📊 ESTADÍSTICAS</b>

━━━━━━━━━━━━━━━━━━

👥 Usuarios:
<b>{stats['users']}</b>

🛒 Compras:
<b>{stats['sales']}</b>

💵 Ganancias:
<b>${stats['money']:.2f}</b>

📦 Productos vendidos:
<b>{stats['products']}</b>
""",
        reply_markup=keyboard
    )



# ============================================================
# STOCK
# ============================================================

@router.callback_query(F.data == "admin_stock")
async def admin_stock(callback: CallbackQuery):

    await callback.answer()


    if callback.from_user.id != OWNER_ID:
        return


    stock = get_stock()



    await callback.message.edit_caption(
        caption=f"""
<b>📦 STOCK</b>

━━━━━━━━━━━━━━━━━━

Productos disponibles:

{stock}

""",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="⬅️ Admin",
                        callback_data="admin"
                    )
                ]
            ]
        )
    )
    # ============================================================
# ESTADOS ADMIN
# ============================================================

from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):

    add_balance_id = State()
    add_balance_amount = State()

    premium_user_id = State()

    ban_user_id = State()

    broadcast_message = State()
    # ============================================================
# AÑADIR SALDO
# ============================================================

@router.callback_query(F.data == "add_balance")
async def add_balance_start(callback: CallbackQuery, state: FSMContext):

    await callback.answer()


    if callback.from_user.id != OWNER_ID:
        return


    await callback.message.answer(
        "🆔 Envía el ID del usuario:"
    )


    await state.set_state(
        AdminStates.add_balance_id
    )



@router.message(AdminStates.add_balance_id)
async def add_balance_id(
    message: Message,
    state: FSMContext
):

    await state.update_data(
        user_id=int(message.text)
    )


    await message.answer(
        "💰 Ahora envía la cantidad a agregar:"
    )


    await state.set_state(
        AdminStates.add_balance_amount
    )



@router.message(AdminStates.add_balance_amount)
async def add_balance_amount(
    message: Message,
    state: FSMContext
):

    data = await state.get_data()


    user_id = data["user_id"]

    amount = float(message.text)



    add_money(
        user_id,
        amount
    )


    await message.answer(
        f"""
✅ Saldo agregado

🆔 Usuario:
{user_id}

💰 Cantidad:
${amount:.2f}
"""
    )


    await state.clear()
    # ============================================================
# ACTIVAR PREMIUM
# ============================================================

@router.callback_query(F.data == "admin_premium")
async def admin_premium(
    callback: CallbackQuery,
    state: FSMContext
):

    await callback.answer()


    if callback.from_user.id != OWNER_ID:
        return


    await callback.message.answer(
        "🆔 Envía el ID del usuario:"
    )


    await state.set_state(
        AdminStates.premium_user_id
    )



@router.message(AdminStates.premium_user_id)
async def premium_user(
    message: Message,
    state: FSMContext
):

    user_id = int(message.text)


    activate_premium(
        user_id
    )


    await message.answer(
        f"""
💎 Premium activado

Usuario:
{user_id}
"""
    )


    await state.clear()
    # ============================================================
# BAN USUARIO
# ============================================================

@router.callback_query(F.data == "ban_user")
async def ban_start(
    callback: CallbackQuery,
    state: FSMContext
):

    await callback.answer()


    await callback.message.answer(
        "🆔 ID del usuario a bloquear:"
    )


    await state.set_state(
        AdminStates.ban_user_id
    )



@router.message(AdminStates.ban_user_id)
async def ban_user(
    message: Message,
    state: FSMContext
):

    user_id = int(message.text)


    ban_user_db(
        user_id
    )


    await message.answer(
        "🚫 Usuario bloqueado correctamente."
    )


    await state.clear()
    # ============================================================
# BROADCAST
# ============================================================

@router.callback_query(F.data == "broadcast")
async def broadcast_start(
    callback: CallbackQuery,
    state: FSMContext
):

    await callback.answer()


    await callback.message.answer(
        "📢 Escribe el mensaje para enviar:"
    )


    await state.set_state(
        AdminStates.broadcast_message
    )



@router.message(AdminStates.broadcast_message)
async def broadcast_send(
    message: Message,
    state: FSMContext
):

    users = get_all_users()


    for user in users:

        try:

            await message.bot.send_message(
                user["user_id"],
                message.text
            )

        except:
            pass



    await message.answer(
        "✅ Mensaje enviado."
    )


    await state.clear()
    # ============================================================
# DATABASE.PY
# RAYO FIX BOT
# ============================================================

import sqlite3
from datetime import datetime


DB = "rayo_fix.db"



# ============================================================
# CONEXIÓN
# ============================================================

def connect():

    return sqlite3.connect(DB)



# ============================================================
# CREAR TABLAS
# ============================================================

def create_tables():

    con = connect()
    cur = con.cursor()



    # USUARIOS

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (

        user_id INTEGER PRIMARY KEY,

        first_name TEXT,

        username TEXT,

        balance REAL DEFAULT 0,

        premium INTEGER DEFAULT 0,

        total_purchases INTEGER DEFAULT 0,

        total_spent REAL DEFAULT 0,

        register_date TEXT,

        banned INTEGER DEFAULT 0

    )
    """)



    # PRODUCTOS

    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        name TEXT,

        price REAL,

        stock INTEGER DEFAULT 0

    )
    """)



    # ENTREGAS

    cur.execute("""
    CREATE TABLE IF NOT EXISTS items (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        product_id INTEGER,

        content TEXT,

        sold INTEGER DEFAULT 0,

        buyer INTEGER

    )
    """)



    # COMPRAS

    cur.execute("""
    CREATE TABLE IF NOT EXISTS purchases (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        user_id INTEGER,

        product TEXT,

        price REAL,

        date TEXT

    )
    """)



    # CUPONES

    cur.execute("""
    CREATE TABLE IF NOT EXISTS coupons (

        code TEXT PRIMARY KEY,

        amount REAL,

        used INTEGER DEFAULT 0

    )
    """)



    con.commit()
    con.close()



# ============================================================
# CREAR USUARIO
# ============================================================

def create_user(
    user_id,
    first_name,
    username
):

    con = connect()
    cur = con.cursor()


    cur.execute("""
    INSERT OR IGNORE INTO users
    (
    user_id,
    first_name,
    username,
    register_date
    )

    VALUES (?,?,?,?)
    """,
    (
        user_id,
        first_name,
        username,
        datetime.now().strftime(
            "%d/%m/%Y"
        )
    ))


    con.commit()
    con.close()



# ============================================================
# OBTENER USUARIO
# ============================================================

def get_user(user_id):

    con = connect()
    cur = con.cursor()


    cur.execute(
        "SELECT * FROM users WHERE user_id=?",
        (user_id,)
    )


    row = cur.fetchone()


    con.close()



    if not row:
        return None



    return {

        "user_id": row[0],

        "first_name": row[1],

        "username": row[2],

        "balance": row[3],

        "premium": row[4],

        "total_purchases": row[5],

        "total_spent": row[6],

        "register_date": row[7],

        "banned": row[8]

    }
    # ============================================================
# ACTUALIZAR SALDO
# ============================================================

def update_balance(
    user_id,
    balance
):

    con = connect()
    cur = con.cursor()


    cur.execute(
        """
        UPDATE users
        SET balance=?
        WHERE user_id=?
        """,
        (
            balance,
            user_id
        )
    )


    con.commit()
    con.close()



# ============================================================
# AGREGAR SALDO ADMIN
# ============================================================

def add_money(
    user_id,
    amount
):

    con = connect()
    cur = con.cursor()


    cur.execute(
        """
        UPDATE users
        SET balance = balance + ?
        WHERE user_id=?
        """,
        (
            amount,
            user_id
        )
    )


    con.commit()
    con.close()



# ============================================================
# REGISTRAR COMPRA
# ============================================================

def add_purchase(
    user_id,
    product,
    price
):

    con = connect()
    cur = con.cursor()


    date = datetime.now().strftime(
        "%d/%m/%Y %H:%M"
    )


    cur.execute(
        """
        INSERT INTO purchases
        (
        user_id,
        product,
        price,
        date
        )

        VALUES (?,?,?,?)
        """,
        (
            user_id,
            product,
            price,
            date
        )
    )



    cur.execute(
        """
        UPDATE users

        SET

        total_purchases =
        total_purchases + 1,

        total_spent =
        total_spent + ?

        WHERE user_id=?

        """,
        (
            price,
            user_id
        )
    )


    con.commit()
    con.close()



# ============================================================
# OBTENER TODOS LOS USUARIOS
# ============================================================

def get_all_users():

    con = connect()
    cur = con.cursor()


    cur.execute(
        "SELECT * FROM users"
    )


    rows = cur.fetchall()


    con.close()


    users = []


    for row in rows:

        users.append({

            "user_id": row[0],

            "first_name": row[1],

            "username": row[2],

            "balance": row[3],

            "premium": row[4],

            "total_purchases": row[5],

            "total_spent": row[6]

        })


    return users



# ============================================================
# ESTADÍSTICAS
# ============================================================

def get_statistics():

    con = connect()
    cur = con.cursor()



    cur.execute(
        "SELECT COUNT(*) FROM users"
    )

    users = cur.fetchone()[0]



    cur.execute(
        "SELECT COUNT(*) FROM purchases"
    )

    sales = cur.fetchone()[0]



    cur.execute(
        "SELECT SUM(price) FROM purchases"
    )

    money = cur.fetchone()[0] or 0



    cur.execute(
        "SELECT COUNT(*) FROM items WHERE sold=1"
    )

    products = cur.fetchone()[0]



    con.close()



    return {

        "users": users,

        "sales": sales,

        "money": money,

        "products": products

    }



# ============================================================
# ACTIVAR PREMIUM
# ============================================================

def activate_premium(
    user_id
):

    con = connect()
    cur = con.cursor()



    cur.execute(
        """
        UPDATE users

        SET premium=1

        WHERE user_id=?

        """,
        (user_id,)
    )


    con.commit()
    con.close()



# ============================================================
# BLOQUEAR USUARIO
# ============================================================

def ban_user_db(
    user_id
):

    con = connect()
    cur = con.cursor()



    cur.execute(
        """
        UPDATE users

        SET banned=1

        WHERE user_id=?

        """,
        (user_id,)
    )


    con.commit()
    con.close()
    # ============================================================
# CREAR PRODUCTO
# ============================================================

def create_product(
    name,
    price
):

    con = connect()
    cur = con.cursor()


    cur.execute(
        """
        INSERT INTO products
        (
        name,
        price
        )

        VALUES (?,?)
        """,
        (
            name,
            price
        )
    )


    con.commit()
    con.close()



# ============================================================
# OBTENER PRODUCTOS
# ============================================================

def get_products():

    con = connect()
    cur = con.cursor()


    cur.execute(
        """
        SELECT *
        FROM products
        """
    )


    rows = cur.fetchall()


    con.close()


    products = []


    for row in rows:

        products.append({

            "id": row[0],

            "name": row[1],

            "price": row[2],

            "stock": row[3]

        })


    return products



# ============================================================
# AGREGAR STOCK
# ============================================================

def add_stock(
    product_id,
    content
):

    con = connect()
    cur = con.cursor()


    cur.execute(
        """
        INSERT INTO items
        (
        product_id,
        content
        )

        VALUES (?,?)
        """,
        (
            product_id,
            content
        )
    )



    cur.execute(
        """
        UPDATE products

        SET stock = stock + 1

        WHERE id=?

        """,
        (
            product_id,
        )
    )


    con.commit()
    con.close()



# ============================================================
# VER STOCK
# ============================================================

def get_product_stock(
    product_id
):

    con = connect()
    cur = con.cursor()



    cur.execute(
        """
        SELECT stock

        FROM products

        WHERE id=?

        """,
        (
            product_id,
        )
    )


    result = cur.fetchone()


    con.close()



    if result:
        return result[0]


    return 0



# ============================================================
# OBTENER ENTREGA DISPONIBLE
# ============================================================

def get_available_item(
    product_id
):

    con = connect()
    cur = con.cursor()



    cur.execute(
        """
        SELECT *

        FROM items

        WHERE product_id=?

        AND sold=0

        LIMIT 1

        """,
        (
            product_id,
        )
    )


    row = cur.fetchone()


    con.close()



    if not row:
        return None



    return {

        "id": row[0],

        "product_id": row[1],

        "content": row[2],

        "sold": row[3]

    }



# ============================================================
# MARCAR ENTREGA COMO VENDIDA
# ============================================================

def mark_item_sold(
    item_id,
    buyer
):

    con = connect()
    cur = con.cursor()



    cur.execute(
        """
        UPDATE items

        SET

        sold=1,

        buyer=?

        WHERE id=?

        """,
        (
            buyer,

            item_id
        )
    )



    cur.execute(
        """
        UPDATE products

        SET stock = stock - 1

        WHERE id =

        (
        SELECT product_id
        FROM items
        WHERE id=?
        )

        """,
        (
            item_id,
        )
    )



    con.commit()
    con.close()



# ============================================================
# ELIMINAR PRODUCTO
# ============================================================

def delete_product(
    product_id
):

    con = connect()
    cur = con.cursor()


    cur.execute(
        """
        DELETE FROM products

        WHERE id=?

        """,
        (
            product_id,
        )
    )


    con.commit()
    con.close()
    # ============================================================
# CREAR CUPÓN
# ============================================================

def create_coupon(
    code,
    amount
):

    con = connect()
    cur = con.cursor()


    cur.execute(
        """
        INSERT INTO coupons
        (
        code,
        amount
        )

        VALUES (?,?)
        """,
        (
            code.upper(),
            amount
        )
    )


    con.commit()
    con.close()



# ============================================================
# OBTENER CUPÓN
# ============================================================

def get_coupon(
    code
):

    con = connect()
    cur = con.cursor()


    cur.execute(
        """
        SELECT *

        FROM coupons

        WHERE code=?

        """,
        (
            code.upper(),
        )
    )


    row = cur.fetchone()


    con.close()



    if not row:
        return None



    return {

        "code": row[0],

        "amount": row[1],

        "used": row[2]

    }



# ============================================================
# USAR CUPÓN
# ============================================================

def use_coupon(
    code
):

    con = connect()
    cur = con.cursor()



    cur.execute(
        """
        UPDATE coupons

        SET used=1

        WHERE code=?

        """,
        (
            code.upper(),
        )
    )



    con.commit()
    con.close()
    from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup



# ============================================================
# ESTADO CUPÓN
# ============================================================

class CouponState(StatesGroup):

    waiting_code = State()



# ============================================================
# INICIAR CUPÓN
# ============================================================

@router.callback_query(F.data == "redeem_coupon")
async def redeem_coupon(
    callback: CallbackQuery,
    state: FSMContext
):

    await callback.answer()


    await callback.message.answer(
        """
🎟️ Envía tu código de cupón:

Ejemplo:
RAYO100
"""
    )


    await state.set_state(
        CouponState.waiting_code
    )



# ============================================================
# VALIDAR CUPÓN
# ============================================================

@router.message(
    CouponState.waiting_code
)

async def check_coupon(
    message: Message,
    state: FSMContext
):

    code = message.text.strip()


    coupon = get_coupon(code)



    if not coupon:

        await message.answer(
            "❌ Cupón inválido."
        )

        await state.clear()

        return



    if coupon["used"]:

        await message.answer(
            "❌ Este cupón ya fue utilizado."
        )

        await state.clear()

        return



    amount = coupon["amount"]



    add_money(
        message.from_user.id,
        amount
    )



    use_coupon(code)



    await message.answer(
        f"""
🎉 CUPÓN APLICADO

━━━━━━━━━━━━━━

🎟️ Código:
<b>{code}</b>

💰 Saldo añadido:
<b>${amount:.2f}</b>

Disfruta tu beneficio ⚡
"""
    )


    await state.clear()
    # ============================================================
# SEGURIDAD USUARIOS
# ============================================================

@router.message()
async def security_check(
    message: Message
):

    user_id = message.from_user.id


    if is_banned(user_id):

        await message.answer(
            "🚫 Tu cuenta está bloqueada."
        )

        return



    add_log(
        user_id,
        "Uso del bot"
    )
    import time


user_cooldowns = {}



async def anti_spam(
    user_id
):

    now = time.time()


    if user_id in user_cooldowns:

        last = user_cooldowns[user_id]


        if now - last < 2:

            return False



    user_cooldowns[user_id] = now


    return True
