import os
import sys
import logging
import sqlite3
import asyncio
from datetime import datetime
from threading import Thread

from flask import Flask
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.exceptions import TelegramAPIError

from database import init_db, db_get_user, db_register_user, DB_NAME

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("RAYO_FIX_STORE")

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

if not BOT_TOKEN:
    logger.critical("BOT_TOKEN no está configurado.")
    sys.exit(1)

init_db()

app = Flask(__name__)

@app.route("/")
def health_check():
    return "⚡ RAYO FIX STORE Bot is running 24/7!", 200

def run_flask():
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "10000")))

def start_web_server():
    Thread(target=run_flask, daemon=True).start()

class AdminStates(StatesGroup):
    waiting_for_broadcast = State()
    waiting_for_user_id = State()
    waiting_for_amount = State()
    waiting_for_message = State()

class OwnerStates(StatesGroup):
    waiting_for_product_name = State()
    waiting_for_product_desc = State()
    waiting_for_product_price = State()
    waiting_for_product_stock = State()
    waiting_for_product_category = State()
    waiting_for_product_image = State()
    waiting_for_product_id = State()
    waiting_for_admin_id = State()
    waiting_for_admin_name = State()
    waiting_for_user_id = State()
    waiting_for_amount = State()

class UserStates(StatesGroup):
    waiting_for_recharge_proof = State()
    waiting_for_coupon = State()

def db_query(query, params=(), fetchone=False, fetchall=False, commit=False):
    conn = sqlite3.connect(DB_NAME)
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        if commit:
            conn.commit()
        if fetchone:
            return cur.fetchone()
        if fetchall:
            return cur.fetchall()
        return cur.lastrowid
    finally:
        conn.close()

def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID

def is_admin(user_id: int) -> bool:
    if is_owner(user_id):
        return True
    row = db_query(
        "SELECT user_id FROM admins WHERE user_id=?",
        (user_id,),
        fetchone=True
    )
    return row is not None

def is_admin_or_owner(user_id: int) -> bool:
    return is_admin(user_id)

def nav_buttons(back="main_menu"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🏠 Inicio", callback_data="main_menu"),
            InlineKeyboardButton(text="⬅️ Atrás", callback_data=back)
        ]
    ])

def owner_admin_buttons():
    return [
        [InlineKeyboardButton(text="⚙️ Panel Admin", callback_data="admin_panel")],
        [InlineKeyboardButton(text="👑 Panel Owner", callback_data="owner_panel")]
    ]

def get_main_menu(user_id: int):
    keyboard = [
        [
            InlineKeyboardButton(text="🛍️ Catálogo", callback_data="menu_catalog"),
            InlineKeyboardButton(text="👤 Mi Perfil", callback_data="menu_profile")
        ],
        [
            InlineKeyboardButton(text="💳 Recargar", callback_data="menu_recharge"),
            InlineKeyboardButton(text="🎟️ Cupones", callback_data="menu_coupons")
        ],
        [
            InlineKeyboardButton(text="💎 Premium", callback_data="menu_premium"),
            InlineKeyboardButton(text="📦 Mis Compras", callback_data="menu_purchases")
        ],
        [
            InlineKeyboardButton(text="📞 Soporte", callback_data="menu_support"),
            InlineKeyboardButton(text="📢 Canal", callback_data="menu_channel")
        ]
    ]

    if is_admin(user_id):
        keyboard.append([
            InlineKeyboardButton(text="⚙️ Panel Admin", callback_data="admin_panel")
        ])

    if is_owner(user_id):
        keyboard.append([
            InlineKeyboardButton(text="👑 Panel Owner", callback_data="owner_panel")
        ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def main_text(user):
    u = db_get_user(user.id)
    balance = float(u[4] or 0)
    premium = "Activa 💎" if u[5] == 1 else "Inactiva"
    return (
        "⚡ *RAYO FIX STORE*\n\n"
        f"👤 *Cliente:* {user.full_name}\n"
        f"🆔 *ID:* `{user.id}`\n"
        f"💰 *Saldo:* ${balance:.2f}\n"
        f"💎 *Membresía:* {premium}\n\n"
        "Selecciona una opción:"
    )

async def safe_edit(callback, text, keyboard=None, photo=False):
    try:
        if photo:
            await callback.message.delete()
            await callback.message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
        else:
            await callback.message.edit_text(
                text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
    except TelegramAPIError:
        await callback.message.answer(
            text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    args = message.text.split()

    invited_by = None
    if len(args) > 1 and args[1].isdigit():
        ref = int(args[1])
        if ref != user.id:
            invited_by = ref

    db_register_user(
        user.id,
        user.full_name,
        user.username,
        invited_by
    )

    db_user = db_get_user(user.id)

    if db_user and len(db_user) > 8 and db_user[8] == 1:
        await message.answer("⚠️ Tu cuenta ha sido bloqueada de RAYO FIX STORE.")
        return

    await message.answer(
        main_text(user),
        reply_markup=get_main_menu(user.id),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await safe_edit(
        callback,
        main_text(callback.from_user),
        get_main_menu(callback.from_user.id)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("noop"))
async def cb_noop(callback: CallbackQuery):
    await callback.answer()

@router.message(Command("id"))
async def cmd_id(message: Message):
    await message.answer(
        f"🆔 Tu ID de Telegram es:\n`{message.from_user.id}`",
        parse_mode="Markdown"
    )

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ No tienes permisos.")
        return
    await message.answer(
        "⚙️ *PANEL ADMIN*",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="👥 Usuarios",
                        callback_data="admin_users"
                    ),
                    InlineKeyboardButton(
                        text="📊 Estadísticas",
                        callback_data="admin_stats"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="💳 Pagos",
                        callback_data="admin_payments"
                    ),
                    InlineKeyboardButton(
                        text="📢 Difusión",
                        callback_data="admin_broadcast"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🏠 Inicio",
                        callback_data="main_menu"
                    )
                ]
            ]
        ),
        parse_mode="Markdown"
    )

@router.message(Command("owner"))
async def cmd_owner(message: Message):
    if not is_owner(message.from_user.id):
        await message.answer("⛔ Acceso exclusivo del Owner.")
        return
    await message.answer(
        "👑 *PANEL OWNER*\n\nAcceso total al sistema.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📦 Productos",
                        callback_data="owner_products"
                    ),
                    InlineKeyboardButton(
                        text="👥 Usuarios",
                        callback_data="owner_users"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="⚙️ Administradores",
                        callback_data="owner_admins"
                    ),
                    InlineKeyboardButton(
                        text="📊 Estadísticas",
                        callback_data="owner_stats"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="💳 Pagos",
                        callback_data="admin_payments"
                    ),
                    InlineKeyboardButton(
                        text="📢 Difusión",
                        callback_data="admin_broadcast"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🏠 Inicio",
                        callback_data="main_menu"
                    )
                ]
            ]
        ),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "close_menu")
async def cb_close_legacy(callback: CallbackQuery):
    await callback.answer("Esta opción ya no está disponible.")
    @router.callback_query(F.data == "menu_catalog")
async def cb_catalog(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📱 Android", callback_data="cat_android"),
            InlineKeyboardButton(text="🍎 iPhone / iOS", callback_data="cat_ios")
        ],
        [
            InlineKeyboardButton(text="🖥️ Windows / PC", callback_data="cat_windows")
        ],
        [
            InlineKeyboardButton(text="🏠 Inicio", callback_data="main_menu"),
            InlineKeyboardButton(text="⬅️ Atrás", callback_data="main_menu")
        ]
    ])
    await safe_edit(
        callback,
        "🛍️ *CATÁLOGO RAYO FIX STORE*\n\n"
        "Selecciona la plataforma donde quieres ver los productos:",
        kb
    )
    await callback.answer()

@router.callback_query(F.data == "cat_windows")
async def cb_windows(callback: CallbackQuery):
    await safe_edit(
        callback,
        "🖥️ *WINDOWS / PC*\n\n"
        "🚧 Esta sección estará disponible próximamente.",
        nav_buttons("menu_catalog")
    )
    await callback.answer()

DEFAULT_PRODUCTS = [
    ("ANDROID", "DRIP CLIENT APK MOD", "Mod APK avanzado para optimización", 15.0, 99),
    ("ANDROID", "DRIP CLIENT PROXY", "Proxy optimizado para Drip Client", 10.0, 50),
    ("ANDROID", "HG CHEATS", "Herramienta avanzada de rendimiento", 20.0, 30),
    ("ANDROID", "HG CHEATS PROXY", "Proxy dedicado HG", 12.0, 40),
    ("ANDROID", "BR MODS", "Configuraciones BR optimizadas", 18.0, 25),
    ("ANDROID", "STRICK BR", "Herramienta de precisión móvil", 22.0, 15),
    ("ANDROID", "CUBAN APK MOD", "Mod APK optimizador general", 14.0, 60),
    ("ANDROID", "CUBAN PROXY", "Proxy Cuban", 9.0, 80),
    ("ANDROID", "FFH4X", "Herramienta de configuración móvil", 25.0, 10),
    ("IOS", "MONITE PRO", "Versión profesional para iOS", 30.0, 20),
    ("IOS", "MONITE BÁSICO", "Versión estándar para iOS", 15.0, 35),
    ("IOS", "CERTIFICADOS", "Certificados para dispositivos iOS", 20.0, 100),
    ("IOS", "PROXY POTATSO", "Configuración avanzada Potatso", 12.0, 50),
    ("IOS", "FLUCK IOS", "Herramienta de configuración iOS", 25.0, 18),
]

def ensure_products():
    total = db_query(
        "SELECT COUNT(*) FROM products",
        fetchone=True
    )[0]

    if total:
        return

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    for category, name, desc, price, stock in DEFAULT_PRODUCTS:
        cur.execute(
            """INSERT INTO products
            (category,name,description,price,stock,status,image_url)
            VALUES (?,?,?,?,?,?,?)""",
            (
                category,
                name,
                desc,
                price,
                stock,
                "Disponible",
                "https://i.imgur.com/4X7b9dM.png"
            )
        )

    conn.commit()
    conn.close()

@router.callback_query(F.data.in_({"cat_android", "cat_ios"}))
async def cb_products(callback: CallbackQuery):
    ensure_products()

    category = "ANDROID" if callback.data == "cat_android" else "IOS"

    products = db_query(
        """SELECT id,name,price,stock,status
        FROM products
        WHERE category=?
        ORDER BY id ASC""",
        (category,),
        fetchall=True
    )

    if not products:
        await safe_edit(
            callback,
            f"📦 *{category}*\n\nNo hay productos disponibles.",
            nav_buttons("menu_catalog")
        )
        await callback.answer()
        return

    keyboard = []

    for product in products:
        pid, name, price, stock, status = product

        if stock > 0:
            text = f"🛒 {name} • ${price:.2f} • {stock}"
        else:
            text = f"❌ {name} • AGOTADO"

        keyboard.append([
            InlineKeyboardButton(
                text=text,
                callback_data=f"prod_{pid}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(text="🏠 Inicio", callback_data="main_menu"),
        InlineKeyboardButton(text="⬅️ Atrás", callback_data="menu_catalog")
    ])

    await safe_edit(
        callback,
        f"📦 *PRODUCTOS {category}*\n\n"
        "Selecciona un producto para ver sus detalles:",
        InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("prod_"))
async def cb_product_detail(callback: CallbackQuery):
    try:
        product_id = int(callback.data.split("_", 1)[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Producto inválido.", show_alert=True)
        return

    product = db_query(
        """SELECT id,name,description,price,stock,status,image_url,category
        FROM products WHERE id=?""",
        (product_id,),
        fetchone=True
    )

    if not product:
        await callback.answer("❌ Producto no encontrado.", show_alert=True)
        return

    pid, name, desc, price, stock, status, image_url, category = product

    if stock > 0:
        buy_button = InlineKeyboardButton(
            text=f"🛒 Comprar • ${price:.2f}",
            callback_data=f"buy_{pid}"
        )
    else:
        buy_button = InlineKeyboardButton(
            text="❌ Agotado",
            callback_data="noop"
        )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [buy_button],
        [
            InlineKeyboardButton(
                text="⬅️ Atrás",
                callback_data=f"cat_{category.lower()}"
            ),
            InlineKeyboardButton(
                text="🏠 Inicio",
                callback_data="main_menu"
            )
        ]
    ])

    text = (
        f"🛍️ *{name}*\n\n"
        f"📂 *Categoría:* {category}\n"
        f"📝 *Descripción:* {desc or 'Sin descripción'}\n\n"
        f"💵 *Precio:* ${float(price):.2f}\n"
        f"📦 *Stock:* {stock}\n"
        f"📌 *Estado:* {status}"
    )

    try:
        if image_url:
            await callback.message.delete()
            await callback.message.answer_photo(
                photo=image_url,
                caption=text,
                reply_markup=kb,
                parse_mode="Markdown"
            )
        else:
            await callback.message.edit_text(
                text,
                reply_markup=kb,
                parse_mode="Markdown"
            )
    except TelegramAPIError:
        await callback.message.answer(
            text,
            reply_markup=kb,
            parse_mode="Markdown"
        )

    await callback.answer()

@router.callback_query(F.data.startswith("buy_"))
async def cb_buy_product(callback: CallbackQuery):
    try:
        product_id = int(callback.data.split("_", 1)[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Compra inválida.", show_alert=True)
        return

    user_id = callback.from_user.id

    product = db_query(
        """SELECT id,name,price,stock,status
        FROM products WHERE id=?""",
        (product_id,),
        fetchone=True
    )

    user = db_query(
        """SELECT balance,purchases_count,banned
        FROM users WHERE id=?""",
        (user_id,),
        fetchone=True
    )

    if not product or not user:
        await callback.answer("❌ Datos no encontrados.", show_alert=True)
        return

    pid, name, price, stock, status = product
    balance, purchases_count, banned = user

    if banned == 1:
        await callback.answer(
            "⛔ Tu cuenta está bloqueada.",
            show_alert=True
        )
        return

    if stock <= 0:
        await callback.answer(
            "❌ Producto agotado.",
            show_alert=True
        )
        return

    if str(status).lower() not in {
        "disponible",
        "activo",
        "available"
    }:
        await callback.answer(
            "❌ Producto no disponible.",
            show_alert=True
        )
        return

    balance = float(balance or 0)
    price = float(price)

    if balance < price:
        await callback.answer(
            f"💰 Saldo insuficiente.\n\n"
            f"Precio: ${price:.2f}\n"
            f"Saldo: ${balance:.2f}",
            show_alert=True
        )
        return

    new_balance = balance - price
    new_stock = stock - 1
    new_purchases = int(purchases_count or 0) + 1
    date_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect(DB_NAME)

    try:
        cur = conn.cursor()

        cur.execute(
            """UPDATE users
            SET balance=?, purchases_count=?
            WHERE id=? AND balance>=?""",
            (
                new_balance,
                new_purchases,
                user_id,
                price
            )
        )

        if cur.rowcount != 1:
            conn.rollback()
            await callback.answer(
                "❌ No se pudo completar la compra.",
                show_alert=True
            )
            return

        cur.execute(
            """UPDATE products
            SET stock=?
            WHERE id=? AND stock>0""",
            (new_stock, product_id)
        )

        if cur.rowcount != 1:
            conn.rollback()
            await callback.answer(
                "❌ El producto se agotó. Intenta nuevamente.",
                show_alert=True
            )
            return

        cur.execute(
            """INSERT INTO purchases
            (user_id,product_name,price,date,status)
            VALUES (?,?,?,?,?)""",
            (
                user_id,
                name,
                price,
                date_now,
                "Completado"
            )
        )

        conn.commit()

    except Exception as e:
        conn.rollback()
        logger.exception("Error en compra: %s", e)
        await callback.answer(
            "❌ Error procesando la compra.",
            show_alert=True
        )
        return

    finally:
        conn.close()

    await callback.answer(
        "✅ ¡Compra realizada correctamente!",
        show_alert=True
    )

    await callback.message.answer(
        "🧾 *COMPRA EXITOSA*\n\n"
        f"📦 *Producto:* {name}\n"
        f"💵 *Pagado:* ${price:.2f}\n"
f"💰 *Saldo restante:* ${new_balance:.2f}\n"
f"📅 *Fecha:* {date_now}\n\n"
"Gracias por comprar en ⚡ RAYO FIX STORE.",
reply_markup=nav_buttons(),
parse_mode="Markdown"
)
    @router.callback_query(F.data == "menu_profile")
async def cb_profile(callback: CallbackQuery):
    u = db_get_user(callback.from_user.id)

    if not u:
        await callback.answer("❌ Usuario no encontrado.", show_alert=True)
        return

    username = f"@{u[2]}" if u[2] else "Sin username"
    balance = float(u[4] or 0)
    premium = "💎 Activa" if u[5] == 1 else "❌ Inactiva"
    purchases = int(u[6] or 0)

    spent = db_query(
        "SELECT COALESCE(SUM(price),0) FROM purchases WHERE user_id=?",
        (callback.from_user.id,),
        fetchone=True
    )[0]

    text = (
        "👤 *MI PERFIL*\n\n"
        f"📌 *Nombre:* {u[1]}\n"
        f"🔖 *Usuario:* {username}\n"
        f"🆔 *ID:* `{u[0]}`\n\n"
        f"💰 *Saldo:* ${balance:.2f}\n"
        f"💎 *Premium:* {premium}\n"
        f"📦 *Compras:* {purchases}\n"
        f"💵 *Total gastado:* ${float(spent or 0):.2f}\n"
        f"📅 *Registro:* {u[3]}"
    )

    await safe_edit(
        callback,
        text,
        nav_buttons()
    )
    await callback.answer()

@router.callback_query(F.data == "menu_purchases")
async def cb_my_purchases(callback: CallbackQuery):
    rows = db_query(
        """SELECT product_name,price,date,status
        FROM purchases
        WHERE user_id=?
        ORDER BY id DESC
        LIMIT 15""",
        (callback.from_user.id,),
        fetchall=True
    )

    if not rows:
        text = (
            "📦 *MIS COMPRAS*\n\n"
            "No tienes compras registradas todavía."
        )
    else:
        lines = ["📦 *MIS COMPRAS*\n"]

        for i, row in enumerate(rows, 1):
            name, price, date, status = row
            lines.append(
                f"*{i}.* 🛍️ {name}\n"
                f"   💵 ${float(price):.2f}\n"
                f"   📅 {date}\n"
                f"   📌 {status}\n"
            )

        text = "\n".join(lines)

    await safe_edit(
        callback,
        text,
        nav_buttons()
    )
    await callback.answer()

@router.callback_query(F.data == "menu_recharge")
async def cb_recharge(callback: CallbackQuery):
    text = (
        "💳 *RECARGAR SALDO*\n\n"
        "Selecciona un método de pago:\n\n"
        "🇵🇪 *Yape / Plin*\n"
        "`999-999-999`\n\n"
        "₿ *Binance USDT*\n"
        "`T_WALLET_EXAMPLE`\n\n"
        "Después de realizar el pago, "
        "envía tu comprobante para que sea revisado."
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📤 Enviar Comprobante",
                callback_data="send_proof"
            )
        ],
        [
            InlineKeyboardButton(
                text="📋 Mis Recargas",
                callback_data="my_payments"
            )
        ],
        [
            InlineKeyboardButton(
                text="🏠 Inicio",
                callback_data="main_menu"
            ),
            InlineKeyboardButton(
                text="⬅️ Atrás",
                callback_data="main_menu"
            )
        ]
    ])

    await safe_edit(callback, text, kb)
    await callback.answer()

@router.callback_query(F.data == "send_proof")
async def cb_send_proof(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(
        UserStates.waiting_for_recharge_proof
    )

    text = (
        "📤 *ENVIAR COMPROBANTE*\n\n"
        "Envía ahora una *foto* de tu comprobante "
        "de pago por este chat.\n\n"
        "⚠️ Asegúrate de que la imagen sea clara "
        "y que se pueda verificar el pago."
    )

    await safe_edit(
        callback,
        text,
        nav_buttons("menu_recharge")
    )
    await callback.answer()

@router.message(
    UserStates.waiting_for_recharge_proof,
    F.photo
)
async def process_recharge_proof(
    message: Message,
    state: FSMContext
):
    user = message.from_user
    photo_id = message.photo[-1].file_id
    caption = message.caption or ""

    existing = db_query(
        """SELECT id FROM payments
        WHERE user_id=? AND status='Pendiente'
        ORDER BY id DESC LIMIT 1""",
        (user.id,),
        fetchone=True
    )

    if existing:
        await state.clear()
        await message.answer(
            "⚠️ Ya tienes una recarga pendiente de revisión.",
            reply_markup=nav_buttons()
        )
        return

    pay_id = db_query(
        """INSERT INTO payments
        (user_id,amount,method,proof,status,date)
        VALUES (?,?,?,?,?,?)""",
        (
            user.id,
            0.0,
            "Comprobante",
            photo_id,
            "Pendiente",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ),
        commit=True
    )

    await state.clear()

    await message.answer(
        "✅ *COMPROBANTE RECIBIDO*\n\n"
        f"🧾 *Solicitud:* `#{pay_id}`\n"
        "📌 *Estado:* Pendiente\n\n"
        "El administrador revisará tu comprobante "
        "y actualizará tu saldo si el pago es válido.",
        reply_markup=nav_buttons("menu_recharge"),
        parse_mode="Markdown"
    )

@router.message(UserStates.waiting_for_recharge_proof)
async def invalid_recharge_proof(
    message: Message,
    state: FSMContext
):
    await message.answer(
        "⚠️ Debes enviar una *FOTO* del comprobante.",
        reply_markup=nav_buttons("menu_recharge"),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "my_payments")
async def cb_my_payments(callback: CallbackQuery):
    rows = db_query(
        """SELECT id,amount,method,status,date
        FROM payments
        WHERE user_id=?
        ORDER BY id DESC
        LIMIT 10""",
        (callback.from_user.id,),
        fetchall=True
    )

    if not rows:
        text = (
            "💳 *MIS RECARGAS*\n\n"
            "No tienes solicitudes de recarga."
        )
    else:
        lines = ["💳 *MIS RECARGAS*\n"]

        for row in rows:
            pid, amount, method, status, date = row

            if status == "Aprobado":
                icon = "✅"
            elif status == "Rechazado":
                icon = "❌"
            else:
                icon = "⏳"

            lines.append(
                f"{icon} *Solicitud #{pid}*\n"
                f"💵 ${float(amount or 0):.2f}\n"
                f"💳 {method}\n"
                f"📌 {status}\n"
                f"📅 {date}\n"
            )

        text = "\n".join(lines)

    await safe_edit(
        callback,
        text,
        nav_buttons("menu_recharge")
    )
    await callback.answer()

@router.callback_query(F.data == "menu_coupons")
async def cb_coupons(callback: CallbackQuery, state: FSMContext):
    text = (
        "🎟️ *CUPONES*\n\n"
        "¿Tienes un código promocional?\n"
        "Puedes introducirlo para obtener el beneficio "
        "correspondiente."
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🎟️ Introducir Cupón",
                callback_data="enter_coupon"
            )
        ],
        [
            InlineKeyboardButton(
                text="🏠 Inicio",
                callback_data="main_menu"
            ),
            InlineKeyboardButton(
                text="⬅️ Atrás",
                callback_data="main_menu"
            )
        ]
    ])

    await safe_edit(callback, text, kb)
    await callback.answer()

@router.callback_query(F.data == "enter_coupon")
async def cb_enter_coupon(
    callback: CallbackQuery,
    state: FSMContext
):
    await state.clear()
    await state.set_state(UserStates.waiting_for_coupon)

    await safe_edit(
        callback,
        "🎟️ *INTRODUCIR CUPÓN*\n\n"
        "Escribe ahora el código del cupón:",
        nav_buttons("menu_coupons")
    )
    await callback.answer()

@router.message(UserStates.waiting_for_coupon)
async def process_coupon(
    message: Message,
    state: FSMContext
):
    code = message.text.strip().upper() if message.text else ""

    if not code:
        await message.answer(
            "⚠️ Escribe un código válido.",
            reply_markup=nav_buttons("menu_coupons")
        )
        return

    coupon = db_query(
        """SELECT id,code,discount,max_uses,used
        FROM coupons
        WHERE UPPER(code)=?
        LIMIT 1""",
        (code,),
        fetchone=True
    )

    if not coupon:
        await state.clear()
        await message.answer(
            "❌ Cupón no encontrado o inválido.",
            reply_markup=nav_buttons("menu_coupons")
        )
        return

    cid, coupon_code, discount, max_uses, used = coupon

    if max_uses and used >= max_uses:
        await state.clear()
        await message.answer(
            "❌ Este cupón ya alcanzó su límite de usos.",
            reply_markup=nav_buttons("menu_coupons")
        )
        return

    used_by_user = db_query(
        """SELECT id FROM coupon_uses
        WHERE coupon_id=? AND user_id=?""",
        (cid, message.from_user.id),
        fetchone=True
    )

    if used_by_user:
        await state.clear()
        await message.answer(
            "⚠️ Ya utilizaste este cupón.",
            reply_markup=nav_buttons("menu_coupons")
        )
        return

    db_query(
        """INSERT INTO coupon_uses
        (coupon_id,user_id,date)
        VALUES (?,?,?)""",
        (
            cid,
            message.from_user.id,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ),
        commit=True
    )

    db_query(
        "UPDATE coupons SET used=used+1 WHERE id=?",
        (cid,),
        commit=True
    )

    await state.clear()

    await message.answer(
        "🎉 *CUPÓN APLICADO*\n\n"
        f"🎟️ Código: `{coupon_code}`\n"
        f"💎 Beneficio: *{discount}*\n\n"
        "Tu beneficio ha sido registrado correctamente.",
        reply_markup=nav_buttons("menu_coupons"),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "menu_premium")
async def cb_premium(callback: CallbackQuery):
    user = db_get_user(callback.from_user.id)

    active = bool(user and user[5] == 1)

    if active:
        text = (
            "💎 *RAYO FIX PREMIUM*\n\n"
            "✅ Tu membresía Premium está activa.\n\n"
            "Disfruta de los beneficios exclusivos "
            "disponibles para miembros Premium."
        )
    else:
        text = (
            "💎 *RAYO FIX PREMIUM*\n\n"
            "❌ Actualmente no tienes Premium activo.\n\n"
            "La membresía Premium puede ofrecer "
            "beneficios exclusivos dentro de la tienda.\n\n"
            "📌 Consulta con soporte para conocer "
            "los planes disponibles."
        )

    await safe_edit(
        callback,
        text,
        nav_buttons()
    )
    await callback.answer()

@router.callback_query(F.data == "menu_support")
async def cb_support(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="💬 Contactar Soporte",
                url="https://t.me/RayoFixSupport"
            )
        ],
        [
            InlineKeyboardButton(
                text="🏠 Inicio",
                callback_data="main_menu"
            ),
            InlineKeyboardButton(
                text="⬅️ Atrás",
                callback_data="main_menu"
            )
        ]
    ])

    await safe_edit(
        callback,
        "📞 *SOPORTE RAYO FIX STORE*\n\n"
        "¿Necesitas ayuda con una compra, recarga "
        "o algún producto?\n\n"
        "Nuestro equipo de soporte puede ayudarte.",
        kb
    )
    await callback.answer()

@router.callback_query(F.data == "menu_channel")
async def cb_channel(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📢 Abrir Canal Oficial",
                url="https://t.me/RayoFixStoreChannel"
            )
        ],
        [
            InlineKeyboardButton(
                text="🏠 Inicio",
                callback_data="main_menu"
            ),
            InlineKeyboardButton(
                text="⬅️ Atrás",
                callback_data="main_menu"
            )
        ]
    ])

    await safe_edit(
        callback,
        "📢 *CANAL OFICIAL*\n\n"
        "Únete al canal oficial para recibir "
        "novedades, productos y anuncios de RAYO FIX STORE.",
        kb
    )
    await callback.answer()
@router.callback_query(F.data == "menu_profile")
async def cb_profile(callback: CallbackQuery):
    u = db_get_user(callback.from_user.id)
    if not u:
        await callback.answer("❌ Usuario no encontrado.", show_alert=True)
        return
    username = f"@{u[2]}" if u[2] and u[2] != "Sin username" else "Sin username"
    text = (
        "👤 **MI PERFIL**\n\n"
        f"📌 Nombre: {u[1]}\n"
        f"🔖 Usuario: {username}\n"
        f"🆔 ID: `{u[0]}`\n"
        f"💰 Saldo: ${u[4]:.2f}\n"
        f"💎 Premium: {'✅ Activo' if u[5] else '❌ Inactivo'}\n"
        f"📦 Compras: {u[6]}\n"
        f"📅 Registro: {u[3]}"
    )
    await callback.message.edit_text(
        text,
        reply_markup=nav_buttons(),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "menu_purchases")
async def cb_my_purchases(callback: CallbackQuery):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "SELECT product_name, price, date, status FROM purchases "
        "WHERE user_id = ? ORDER BY id DESC LIMIT 15",
        (callback.from_user.id,)
    )
    rows = cur.fetchall()
    conn.close()

    if not rows:
        text = (
            "📦 **MIS COMPRAS**\n\n"
            "No tienes compras registradas todavía."
        )
    else:
        items = []
        for name, price, date, status in rows:
            items.append(
                f"🛍️ **{name}**\n"
                f"💵 ${price:.2f}\n"
                f"📅 {date}\n"
                f"📌 {status}"
            )
        text = "📦 **MIS COMPRAS**\n\n" + "\n\n".join(items)

    await callback.message.edit_text(
        text,
        reply_markup=nav_buttons(),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "menu_recharge")
async def cb_recharge(callback: CallbackQuery):
    text = (
        "💳 **RECARGAR SALDO**\n\n"
        "Selecciona el método de pago que deseas utilizar.\n\n"
        "⚡ Una vez realizado el pago, envía tu comprobante "
        "para que pueda ser revisado."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🇵🇪 Yape / Plin",
            callback_data="recharge_yape"
        )],
        [InlineKeyboardButton(
            text="💰 Binance USDT",
            callback_data="recharge_binance"
        )],
        [
            InlineKeyboardButton(
                text="🏠 Inicio",
                callback_data="main_menu"
            ),
            InlineKeyboardButton(
                text="⬅️ Atrás",
                callback_data="main_menu"
            )
        ]
    ])
    await callback.message.edit_text(
        text,
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "recharge_yape")
async def cb_recharge_yape(callback: CallbackQuery):
    text = (
        "🇵🇪 **RECARGA POR YAPE / PLIN**\n\n"
        "📱 Número: `903-472-998`\n\n"
        "💡 Realiza el pago y luego pulsa "
        "**Enviar Comprobante**."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📤 Enviar Comprobante",
            callback_data="send_proof"
        )],
        [
            InlineKeyboardButton(
                text="🏠 Inicio",
                callback_data="main_menu"
            ),
            InlineKeyboardButton(
                text="⬅️ Atrás",
                callback_data="menu_recharge"
            )
        ]
    ])
    await callback.message.edit_text(
        text,
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "recharge_binance")
async def cb_recharge_binance(callback: CallbackQuery):
    text = (
        "💰 **RECARGA POR BINANCE USDT**\n\n"
        "🌐 Red: TRC20\n"
        "💳 Wallet: `T_WALLET_EXAMPLE`\n\n"
        "⚠️ Verifica cuidadosamente la dirección antes "
        "de realizar el pago."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="📤 Enviar Comprobante",
            callback_data="send_proof"
        )],
        [
            InlineKeyboardButton(
                text="🏠 Inicio",
                callback_data="main_menu"
            ),
            InlineKeyboardButton(
                text="⬅️ Atrás",
                callback_data="menu_recharge"
            )
        ]
    ])
    await callback.message.edit_text(
        text,
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "send_proof")
async def cb_send_proof_prompt(
    callback: CallbackQuery,
    state: FSMContext
):
    await state.set_state(UserStates.waiting_for_recharge_proof)
    await callback.message.edit_text(
        "📤 **ENVIAR COMPROBANTE**\n\n"
        "Envía ahora la **foto de tu comprobante** "
        "por este chat.\n\n"
        "📝 El administrador revisará el pago y "
        "aprobará la recarga.",
        reply_markup=nav_buttons("menu_recharge"),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(UserStates.waiting_for_recharge_proof, F.photo)
async def process_recharge_proof(
    message: Message,
    state: FSMContext
):
    photo_id = message.photo[-1].file_id
    user_id = message.from_user.id
    date_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO payments "
        "(user_id, amount, method, proof, status, date) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            user_id,
            0.0,
            "Pendiente",
            photo_id,
            "Pendiente",
            date_now
        )
    )
    payment_id = cur.lastrowid
    conn.commit()
    conn.close()

    await state.clear()

    await message.answer(
        "✅ **COMPROBANTE RECIBIDO**\n\n"
        f"🧾 Solicitud: `#{payment_id}`\n"
        "📌 Estado: **Pendiente**\n\n"
        "⏳ Tu comprobante será revisado por el equipo.",
        reply_markup=nav_buttons(),
        parse_mode="Markdown"
    )


@router.message(UserStates.waiting_for_recharge_proof)
async def invalid_recharge_proof(
    message: Message,
    state: FSMContext
):
    await message.answer(
        "⚠️ Debes enviar una **foto del comprobante**.",
        reply_markup=nav_buttons("menu_recharge"),
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "menu_coupons")
async def cb_coupons(
    callback: CallbackQuery,
    state: FSMContext
):
    await state.set_state(UserStates.waiting_for_coupon)
    await callback.message.edit_text(
        "🎟️ **CUPÓN DE DESCUENTO**\n\n"
        "Escribe el código del cupón que deseas utilizar.\n\n"
        "Ejemplo:\n"
        "`RAYO10`",
        reply_markup=nav_buttons(),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(UserStates.waiting_for_coupon)
async def process_coupon(
    message: Message,
    state: FSMContext
):
    code = message.text.strip().upper() if message.text else ""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "SELECT code, discount_type, value, uses_left, expires_at "
        "FROM coupons WHERE code = ?",
        (code,)
    )
    coupon = cur.fetchone()
    conn.close()

    if not coupon:
        await message.answer(
            "❌ El cupón no existe o no es válido.",
            reply_markup=nav_buttons(),
            parse_mode="Markdown"
        )
        return

    expires = coupon[4]
    if expires:
        try:
            exp = datetime.strptime(expires, "%Y-%m-%d %H:%M:%S")
            if datetime.now() > exp:
                await message.answer(
                    "❌ Este cupón ha expirado.",
                    reply_markup=nav_buttons(),
                    parse_mode="Markdown"
                )
                await state.clear()
                return
        except ValueError:
            pass

    if coupon[3] <= 0:
        await message.answer(
            "❌ Este cupón ya no tiene usos disponibles.",
            reply_markup=nav_buttons(),
            parse_mode="Markdown"
        )
        await state.clear()
        return

    discount = (
        f"{coupon[2]:.0f}%"
        if coupon[1].lower() == "percent"
        else f"${coupon[2]:.2f}"
    )

    await state.clear()
    await message.answer(
        "✅ **CUPÓN VÁLIDO**\n\n"
        f"🎟️ Código: `{coupon[0]}`\n"
        f"💎 Descuento: **{discount}**\n\n"
        "El descuento será aplicado según las condiciones "
        "del cupón.",
        reply_markup=nav_buttons(),
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "menu_premium")
async def cb_premium(callback: CallbackQuery):
    u = db_get_user(callback.from_user.id)
    active = bool(u and u[5])

    if active:
        text = (
            "💎 **MEMBRESÍA PREMIUM**\n\n"
            "🟢 Estado: **ACTIVA**\n\n"
            "Disfrutas de los beneficios Premium disponibles "
            "en la tienda."
        )
    else:
        text = (
            "💎 **MEMBRESÍA PREMIUM**\n\n"
            "🔴 Estado: **INACTIVA**\n\n"
            "La membresía Premium te permitirá acceder a "
            "beneficios especiales de la tienda."
        )

    await callback.message.edit_text(
        text,
        reply_markup=nav_buttons(),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "menu_support")
async def cb_support(callback: CallbackQuery):
    await callback.message.edit_text(
        "📞 **SOPORTE OFICIAL**\n\n"
        "¿Necesitas ayuda con una compra, recarga o producto?\n\n"
        "👨‍💻 Soporte: @RayoFixSupport\n\n"
        "🕐 Atención según disponibilidad.",
        reply_markup=nav_buttons(),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "menu_channel")
async def cb_channel(callback: CallbackQuery):
    await callback.message.edit_text(
        "📢 **CANAL OFICIAL**\n\n"
        "Únete al canal para recibir:\n\n"
        "🆕 Nuevos productos\n"
        "🔥 Promociones\n"
        "📢 Avisos importantes\n"
        "💎 Beneficios especiales\n\n"
        "🔗 t.me/RayoFixStoreChannel",
        reply_markup=nav_buttons(),
        parse_mode="Markdown"
    )
    await callback.answer()
    @router.callback_query(F.data == "admin_panel")
async def cb_admin_panel(callback: CallbackQuery):
    if not is_admin_or_owner(callback.from_user.id):
        await callback.answer("❌ No tienes permisos.", show_alert=True)
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👥 Usuarios", callback_data="admin_users"),
            InlineKeyboardButton(text="📦 Productos", callback_data="admin_products")
        ],
        [
            InlineKeyboardButton(text="💳 Pagos", callback_data="admin_payments"),
            InlineKeyboardButton(text="📊 Estadísticas", callback_data="admin_stats")
        ],
        [
            InlineKeyboardButton(text="📢 Difusión", callback_data="admin_broadcast"),
            InlineKeyboardButton(text="🎟️ Cupones", callback_data="admin_coupons")
        ],
        [
            InlineKeyboardButton(text="🏠 Inicio", callback_data="main_menu"),
            InlineKeyboardButton(text="⬅️ Atrás", callback_data="main_menu")
        ]
    ])

    await callback.message.edit_text(
        "⚙️ **PANEL ADMINISTRADOR**\n\n"
        "Gestiona las funciones autorizadas de la tienda.",
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_users")
async def cb_admin_users(callback: CallbackQuery):
    if not is_admin_or_owner(callback.from_user.id):
        await callback.answer("❌ Sin permisos.", show_alert=True)
        return

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute(
        "SELECT id, name, username, balance, is_premium, is_banned "
        "FROM users ORDER BY registered_at DESC LIMIT 30"
    )
    users = cur.fetchall()

    cur.execute("SELECT COUNT(*) FROM users")
    total = cur.fetchone()[0]

    conn.close()

    if not users:
        text = "👥 **USUARIOS**\n\nNo hay usuarios registrados."
    else:
        lines = []

        for user in users:
            premium = "💎" if user[4] else "👤"
            banned = "🚫" if user[5] else ""
            username = (
                f"@{user[2]}"
                if user[2] and user[2] != "Sin username"
                else "Sin username"
            )

            lines.append(
                f"{premium} `{user[0]}` • {username} {banned}\n"
                f"💰 Saldo: ${user[3]:.2f}\n"
                f"👤 {user[1]}"
            )

        text = (
            f"👥 **USUARIOS**\n\n"
            f"📊 Total registrados: **{total}**\n\n"
            + "\n\n".join(lines)
        )

    await callback.message.edit_text(
        text,
        reply_markup=nav_buttons("admin_panel"),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_products")
async def cb_admin_products(callback: CallbackQuery):
    if not is_admin_or_owner(callback.from_user.id):
        await callback.answer("❌ Sin permisos.", show_alert=True)
        return

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute(
        "SELECT id, category, name, price, stock, status "
        "FROM products ORDER BY id DESC LIMIT 30"
    )
    products = cur.fetchall()

    conn.close()

    if not products:
        text = "📦 **PRODUCTOS**\n\nNo hay productos registrados."
    else:
        lines = []

        for product in products:
            status = str(product[5] or "").lower()

            if status in ("disponible", "activo", "available"):
                icon = "🟢"
            else:
                icon = "🔴"

            lines.append(
                f"{icon} `{product[0]}` **{product[2]}**\n"
                f"📂 Categoría: {product[1]}\n"
                f"💵 Precio: ${product[3]:.2f}\n"
                f"📦 Stock: {product[4]}\n"
                f"📌 Estado: {product[5]}"
            )

        text = "📦 **PRODUCTOS**\n\n" + "\n\n".join(lines)

    await callback.message.edit_text(
        text,
        reply_markup=nav_buttons("admin_panel"),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(callback: CallbackQuery):
    if not is_admin_or_owner(callback.from_user.id):
        await callback.answer("❌ Sin permisos.", show_alert=True)
        return

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM users")
    users = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM users WHERE is_premium = 1")
    premium = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM users WHERE is_banned = 1")
    banned = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM products")
    products = cur.fetchone()[0]

    cur.execute("SELECT COALESCE(SUM(stock), 0) FROM products")
    stock = cur.fetchone()[0] or 0

    cur.execute("SELECT COUNT(*) FROM purchases")
    sales = cur.fetchone()[0]

    cur.execute("SELECT COALESCE(SUM(price), 0) FROM purchases")
    revenue = cur.fetchone()[0] or 0

    cur.execute(
        "SELECT COUNT(*) FROM payments WHERE status = 'Pendiente'"
    )
    pending = cur.fetchone()[0]

    conn.close()

    text = (
        "📊 **ESTADÍSTICAS DE LA TIENDA**\n\n"
        f"👥 Usuarios: **{users}**\n"
        f"💎 Usuarios Premium: **{premium}**\n"
        f"🚫 Usuarios baneados: **{banned}**\n\n"
        f"📦 Productos: **{products}**\n"
        f"📊 Stock total: **{stock}**\n\n"
        f"🛒 Ventas: **{sales}**\n"
        f"💰 Ingresos: **${revenue:.2f}**\n"
        f"💳 Pagos pendientes: **{pending}**"
    )

    await callback.message.edit_text(
        text,
        reply_markup=nav_buttons("admin_panel"),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_payments")
async def cb_admin_payments(callback: CallbackQuery):
    if not is_admin_or_owner(callback.from_user.id):
        await callback.answer("❌ Sin permisos.", show_alert=True)
        return

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute(
        "SELECT id, user_id, amount, method, status, date "
        "FROM payments ORDER BY id DESC LIMIT 20"
    )
    payments = cur.fetchall()

    conn.close()

    if not payments:
        text = "💳 **PAGOS**\n\nNo hay pagos registrados."
    else:
        lines = []

        for payment in payments:
            status = payment[4]

            if status == "Pendiente":
                icon = "🟡"
            elif status == "Aprobado":
                icon = "🟢"
            else:
                icon = "🔴"

            lines.append(
                f"{icon} **Pago #{payment[0]}**\n"
                f"👤 Usuario: `{payment[1]}`\n"
                f"💵 Monto: ${payment[2]:.2f}\n"
                f"💳 Método: {payment[3]}\n"
                f"📌 Estado: {status}\n"
                f"📅 Fecha: {payment[5]}"
            )

        text = "💳 **PAGOS RECIENTES**\n\n" + "\n\n".join(lines)

    await callback.message.edit_text(
        text,
        reply_markup=nav_buttons("admin_panel"),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_coupons")
async def cb_admin_coupons(callback: CallbackQuery):
    if not is_admin_or_owner(callback.from_user.id):
        await callback.answer("❌ Sin permisos.", show_alert=True)
        return

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute(
        "SELECT code, discount_type, value, uses_left, expires_at "
        "FROM coupons ORDER BY code LIMIT 30"
    )
    coupons = cur.fetchall()

    conn.close()

    if not coupons:
        text = "🎟️ **CUPONES**\n\nNo hay cupones registrados."
    else:
        lines = []

        for coupon in coupons:
            discount = (
                f"{coupon[2]:.0f}%"
                if coupon[1].lower() == "percent"
                else f"${coupon[2]:.2f}"
            )

            expiry = coupon[4] or "Sin vencimiento"

            lines.append(
                f"🎟️ `{coupon[0]}`\n"
                f"💎 Descuento: **{discount}**\n"
                f"🔢 Usos restantes: **{coupon[3]}**\n"
                f"📅 Vence: {expiry}"
            )

        text = "🎟️ **CUPONES**\n\n" + "\n\n".join(lines)

    await callback.message.edit_text(
        text,
        reply_markup=nav_buttons("admin_panel"),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_broadcast")
async def cb_admin_broadcast(
    callback: CallbackQuery,
    state: FSMContext
):
    if not is_admin_or_owner(callback.from_user.id):
        await callback.answer("❌ Sin permisos.", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_for_broadcast)

    await callback.message.edit_text(
        "📢 **DIFUSIÓN GLOBAL**\n\n"
        "Envía ahora el mensaje que deseas enviar a todos "
        "los usuarios registrados.\n\n"
        "⚠️ Utiliza esta función únicamente para comunicados "
        "de la tienda.",
        reply_markup=nav_buttons("admin_panel"),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.message(AdminStates.waiting_for_broadcast)
async def process_admin_broadcast(
    message: Message,
    state: FSMContext,
    bot: Bot
):
    if not is_admin_or_owner(message.from_user.id):
        await state.clear()
        return

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("SELECT id FROM users WHERE is_banned = 0")
    users = [row[0] for row in cur.fetchall()]

    conn.close()
    await state.clear()

    sent = 0
    failed = 0

    for user_id in users:
        try:
            await bot.copy_message(
                chat_id=user_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
            sent += 1
        except TelegramAPIError:
            failed += 1

        await asyncio.sleep(0.03)

    await message.answer(
        "📢 **DIFUSIÓN FINALIZADA**\n\n"
        f"✅ Enviados: **{sent}**\n"
        f"❌ Fallidos: **{failed}**",
        reply_markup=nav_buttons("admin_panel"),
        parse_mode="Markdown"
                            )
    @router.callback_query(F.data == "owner_panel")
async def cb_owner_panel(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        await callback.answer(
            "❌ Esta sección es exclusiva del Owner.",
            show_alert=True
        )
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="📊 Dashboard",
                callback_data="owner_dashboard"
            ),
            InlineKeyboardButton(
                text="👥 Usuarios",
                callback_data="owner_users"
            )
        ],
        [
            InlineKeyboardButton(
                text="📦 Productos",
                callback_data="owner_products"
            ),
            InlineKeyboardButton(
                text="💳 Pagos",
                callback_data="owner_payments"
            )
        ],
        [
            InlineKeyboardButton(
                text="⚙️ Administradores",
                callback_data="owner_admins"
            ),
            InlineKeyboardButton(
                text="🔧 Configuración",
                callback_data="owner_settings"
            )
        ],
        [
            InlineKeyboardButton(
                text="🎟️ Cupones",
                callback_data="owner_coupons"
            ),
            InlineKeyboardButton(
                text="📢 Difusión",
                callback_data="owner_broadcast"
            )
        ],
        [
            InlineKeyboardButton(
                text="🛡️ Seguridad",
                callback_data="owner_security"
            ),
            InlineKeyboardButton(
                text="📜 Registros",
                callback_data="owner_logs"
            )
        ],
        [
            InlineKeyboardButton(
                text="🏠 Inicio",
                callback_data="main_menu"
            ),
            InlineKeyboardButton(
                text="⬅️ Atrás",
                callback_data="main_menu"
            )
        ]
    ])

    await callback.message.edit_text(
        "👑 **PANEL OWNER**\n\n"
        "🔐 Acceso máximo del sistema.\n\n"
        "Desde aquí puedes administrar y configurar "
        "prácticamente toda la tienda.",
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "owner_dashboard")
async def cb_owner_dashboard(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        await callback.answer(
            "❌ Acceso denegado.",
            show_alert=True
        )
        return

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    queries = {
        "users": "SELECT COUNT(*) FROM users",
        "premium": "SELECT COUNT(*) FROM users WHERE is_premium = 1",
        "banned": "SELECT COUNT(*) FROM users WHERE is_banned = 1",
        "products": "SELECT COUNT(*) FROM products",
        "stock": "SELECT COALESCE(SUM(stock), 0) FROM products",
        "sales": "SELECT COUNT(*) FROM purchases",
        "revenue": "SELECT COALESCE(SUM(price), 0) FROM purchases",
        "pending": "SELECT COUNT(*) FROM payments WHERE status = 'Pendiente'",
        "admins": "SELECT COUNT(*) FROM admins"
    }

    data = {}

    for key, query in queries.items():
        cur.execute(query)
        data[key] = cur.fetchone()[0] or 0

    conn.close()

    text = (
        "👑 **OWNER DASHBOARD**\n\n"
        "📈 **RESUMEN DEL SISTEMA**\n\n"
        f"👥 Usuarios: **{data['users']}**\n"
        f"💎 Premium: **{data['premium']}**\n"
        f"🚫 Baneados: **{data['banned']}**\n\n"
        f"📦 Productos: **{data['products']}**\n"
        f"📊 Stock total: **{data['stock']}**\n\n"
        f"🛒 Ventas: **{data['sales']}**\n"
        f"💰 Ingresos: **${data['revenue']:.2f}**\n"
        f"💳 Pagos pendientes: **{data['pending']}**\n"
        f"⚙️ Administradores: **{data['admins']}**"
    )

    await callback.message.edit_text(
        text,
        reply_markup=nav_buttons("owner_panel"),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "owner_security")
async def cb_owner_security(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        await callback.answer(
            "❌ Acceso denegado.",
            show_alert=True
        )
        return

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute(
        "SELECT COUNT(*) FROM users WHERE is_banned = 1"
    )
    banned = cur.fetchone()[0]

    cur.execute(
        "SELECT COUNT(*) FROM admins"
    )
    admins = cur.fetchone()[0]

    cur.execute(
        "SELECT COUNT(*) FROM payments WHERE status = 'Pendiente'"
    )
    pending = cur.fetchone()[0]

    conn.close()

    text = (
        "🛡️ **SEGURIDAD DEL SISTEMA**\n\n"
        f"🚫 Usuarios baneados: **{banned}**\n"
        f"⚙️ Administradores: **{admins}**\n"
        f"💳 Pagos pendientes: **{pending}**\n\n"
        "🔐 El Owner mantiene el control total sobre "
        "los permisos administrativos."
    )

    await callback.message.edit_text(
        text,
        reply_markup=nav_buttons("owner_panel"),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "owner_users")
async def cb_owner_users(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        await callback.answer(
            "❌ Acceso denegado.",
            show_alert=True
        )
        return

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute(
        "SELECT id, name, username, balance, is_premium, is_banned "
        "FROM users ORDER BY registered_at DESC LIMIT 50"
    )
    users = cur.fetchall()

    cur.execute("SELECT COUNT(*) FROM users")
    total = cur.fetchone()[0]

    conn.close()

    if not users:
        text = "👥 **USUARIOS**\n\nNo hay usuarios registrados."
    else:
        lines = []

        for user in users:
            premium = "💎" if user[4] else "👤"
            banned = "🚫" if user[5] else ""
            username = (
                f"@{user[2]}"
                if user[2] and user[2] != "Sin username"
                else "Sin username"
            )

            lines.append(
                f"{premium} `{user[0]}` • {username} {banned}\n"
                f"👤 {user[1]}\n"
                f"💰 Saldo: ${user[3]:.2f}"
            )

        text = (
            f"👥 **GESTIÓN DE USUARIOS**\n\n"
            f"📊 Total: **{total}**\n\n"
            + "\n\n".join(lines)
        )

    await callback.message.edit_text(
        text,
        reply_markup=nav_buttons("owner_panel"),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("owner_"))
async def owner_reserved(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        await callback.answer(
            "❌ Función exclusiva del Owner.",
            show_alert=True
        )
        return

    reserved = {
        "owner_products": "📦 Productos",
        "owner_payments": "💳 Pagos",
        "owner_admins": "⚙️ Administradores",
        "owner_settings": "🔧 Configuración",
        "owner_coupons": "🎟️ Cupones",
        "owner_broadcast": "📢 Difusión",
        "owner_logs": "📜 Registros"
    }

    if callback.data in reserved:
        await callback.answer(
            f"⚙️ {reserved[callback.data]} se configurará en la siguiente sección.",
            show_alert=True
    )
        @router.callback_query(F.data == "owner_products")
async def cb_owner_products(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        await callback.answer("❌ Acceso denegado.", show_alert=True)
        return

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, category, name, price, stock, status "
        "FROM products ORDER BY id DESC LIMIT 50"
    )
    products = cur.fetchall()
    conn.close()

    kb = [
        [InlineKeyboardButton(
            text="➕ Agregar producto",
            callback_data="owner_product_add"
        )]
    ]

    if products:
        for product in products:
            status = "🟢" if str(product[5]).lower() in (
                "disponible", "activo", "available"
            ) else "🔴"

            kb.append([
                InlineKeyboardButton(
                    text=f"{status} {product[2][:25]}",
                    callback_data=f"owner_product_view:{product[0]}"
                )
            ])

    kb.append([
        InlineKeyboardButton(
            text="🏠 Inicio",
            callback_data="main_menu"
        ),
        InlineKeyboardButton(
            text="⬅️ Atrás",
            callback_data="owner_panel"
        )
    ])

    if not products:
        text = (
            "📦 **GESTIÓN DE PRODUCTOS**\n\n"
            "No hay productos registrados.\n\n"
            "Pulsa **Agregar producto** para crear uno."
        )
    else:
        text = (
            "📦 **GESTIÓN DE PRODUCTOS**\n\n"
            f"Productos registrados: **{len(products)}**\n\n"
            "Selecciona un producto para administrarlo."
        )

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("owner_product_view:"))
async def cb_owner_product_view(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        await callback.answer("❌ Acceso denegado.", show_alert=True)
        return

    try:
        product_id = int(callback.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Producto inválido.", show_alert=True)
        return

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, category, name, description, price, stock, status, image_url "
        "FROM products WHERE id = ?",
        (product_id,)
    )
    product = cur.fetchone()
    conn.close()

    if not product:
        await callback.answer("❌ Producto no encontrado.", show_alert=True)
        return

    status = product[6] or "Sin estado"

    text = (
        "📦 **DETALLES DEL PRODUCTO**\n\n"
        f"🆔 ID: `{product[0]}`\n"
        f"📂 Categoría: **{product[1]}**\n"
        f"🛍️ Nombre: **{product[2]}**\n"
        f"📝 Descripción: {product[3] or 'Sin descripción'}\n"
        f"💵 Precio: **${product[4]:.2f}**\n"
        f"📦 Stock: **{product[5]}**\n"
        f"📌 Estado: **{status}**"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✏️ Editar",
                callback_data=f"owner_product_edit:{product[0]}"
            ),
            InlineKeyboardButton(
                text="🗑️ Eliminar",
                callback_data=f"owner_product_delete:{product[0]}"
            )
        ],
        [
            InlineKeyboardButton(
                text="⬅️ Atrás",
                callback_data="owner_products"
            ),
            InlineKeyboardButton(
                text="🏠 Inicio",
                callback_data="main_menu"
            )
        ]
    ])

    await callback.message.edit_text(
        text,
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "owner_payments")
async def cb_owner_payments(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        await callback.answer("❌ Acceso denegado.", show_alert=True)
        return

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, user_id, amount, method, status, date, proof "
        "FROM payments ORDER BY id DESC LIMIT 30"
    )
    payments = cur.fetchall()
    conn.close()

    if not payments:
        text = "💳 **GESTIÓN DE PAGOS**\n\nNo hay pagos registrados."
    else:
        lines = []

        for payment in payments:
            status = payment[4]
            icon = (
                "🟡" if status == "Pendiente"
                else "🟢" if status == "Aprobado"
                else "🔴"
            )

            lines.append(
                f"{icon} **Pago #{payment[0]}**\n"
                f"👤 Usuario: `{payment[1]}`\n"
                f"💵 Monto: **${payment[2]:.2f}**\n"
                f"💳 Método: {payment[3]}\n"
                f"📌 Estado: **{status}**\n"
                f"📅 {payment[5]}"
            )

        text = "💳 **GESTIÓN DE PAGOS**\n\n" + "\n\n".join(lines)

    await callback.message.edit_text(
        text,
        reply_markup=nav_buttons("owner_panel"),
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "owner_admins")
async def cb_owner_admins(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        await callback.answer("❌ Acceso denegado.", show_alert=True)
        return

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM admins ORDER BY user_id")
    admins = [row[0] for row in cur.fetchall()]
    conn.close()

    if admins:
        text = (
            "⚙️ **ADMINISTRADORES**\n\n"
            f"Total: **{len(admins)}**\n\n"
            + "\n".join(f"👤 `{admin_id}`" for admin_id in admins)
        )
    else:
        text = (
            "⚙️ **ADMINISTRADORES**\n\n"
            "No hay administradores registrados."
        )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="➕ Agregar Admin",
                callback_data="owner_admin_add"
            ),
            InlineKeyboardButton(
                text="➖ Quitar Admin",
                callback_data="owner_admin_remove"
            )
        ],
        [
            InlineKeyboardButton(
                text="⬅️ Atrás",
                callback_data="owner_panel"
            ),
            InlineKeyboardButton(
                text="🏠 Inicio",
                callback_data="main_menu"
            )
        ]
    ])

    await callback.message.edit_text(
        text,
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "owner_settings")
async def cb_owner_settings(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        await callback.answer("❌ Acceso denegado.", show_alert=True)
        return

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT key, value FROM settings ORDER BY key")
    settings = cur.fetchall()
    conn.close()

    if settings:
        text = (
            "🔧 **CONFIGURACIÓN DEL SISTEMA**\n\n"
            + "\n".join(
                f"⚙️ `{key}` → `{value}`"
                for key, value in settings
            )
        )
    else:
        text = (
            "🔧 **CONFIGURACIÓN DEL SISTEMA**\n\n"
            "No hay configuraciones personalizadas."
        )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="➕ Nueva configuración",
                callback_data="owner_setting_add"
            )
        ],
        [
            InlineKeyboardButton(
                text="⬅️ Atrás",
                callback_data="owner_panel"
            ),
            InlineKeyboardButton(
                text="🏠 Inicio",
                callback_data="main_menu"
            )
        ]
    ])

    await callback.message.edit_text(
        text,
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "owner_coupons")
async def cb_owner_coupons(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        await callback.answer("❌ Acceso denegado.", show_alert=True)
        return

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "SELECT code, discount_type, value, uses_left, expires_at "
        "FROM coupons ORDER BY code LIMIT 50"
    )
    coupons = cur.fetchall()
    conn.close()

    if not coupons:
        text = "🎟️ **GESTIÓN DE CUPONES**\n\nNo hay cupones registrados."
    else:
        lines = []

        for coupon in coupons:
            discount = (
                f"{coupon[2]:.0f}%"
                if coupon[1].lower() == "percent"
                else f"${coupon[2]:.2f}"
            )

            lines.append(
                f"🎟️ `{coupon[0]}` • **{discount}**\n"
                f"🔢 Usos: {coupon[3]}\n"
                f"📅 Vence: {coupon[4] or 'Sin vencimiento'}"
            )

        text = "🎟️ **GESTIÓN DE CUPONES**\n\n" + "\n\n".join(lines)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="➕ Crear cupón",
                callback_data="owner_coupon_add"
            )
        ],
        [
            InlineKeyboardButton(
                text="⬅️ Atrás",
                callback_data="owner_panel"
            ),
            InlineKeyboardButton(
                text="🏠 Inicio",
                callback_data="main_menu"
            )
        ]
    ])

    await callback.message.edit_text(
        text,
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await callback.answer()


@router.callback_query(F.data == "owner_logs")
async def cb_owner_logs(callback: CallbackQuery):
    if not is_owner(callback.from_user.id):
        await callback.answer("❌ Acceso denegado.", show_alert=True)
        return

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute(
        "SELECT id, user_id, product_name, price, date, status "
        "FROM purchases ORDER BY id DESC LIMIT 20"
    )
    purchases = cur.fetchall()

    conn.close()

    if not purchases:
        text = (
            "📜 **REGISTROS DEL SISTEMA**\n\n"
            "No existen registros de compras todavía."
        )
    else:
        lines = []

        for purchase in purchases:
            lines.append(
                f"🧾 **#{purchase[0]}**\n"
                f"👤 Usuario: `{purchase[1]}`\n"
                f"🛍️ Producto: {purchase[2]}\n"
                f"💵 ${purchase[3]:.2f}\n"
                f"📌 {purchase[5]}\n"
                f"📅 {purchase[4]}"
            )

        text = (
            "📜 **REGISTROS DEL SISTEMA**\n\n"
            + "\n\n".join(lines)
        )

    await callback.message.edit_text(
        text,
        reply_markup=nav_buttons("owner_panel"),
        parse_mode="Markdown"
    )
    await callback.answer()
    @router.callback_query(F.data == "owner_admins")
async def cb_owner_admins(callback: CallbackQuery):
if not is_owner(callback.from_user.id):
await callback.answer("❌ Acceso denegado.", show_alert=True)
return

conn = sqlite3.connect(DB_NAME)
cur = conn.cursor()
cur.execute("SELECT user_id FROM admins ORDER BY user_id")
admins = cur.fetchall()
conn.close()

if not admins:
    text = (
        "⚙️ **ADMINISTRADORES**\n\n"
        "No hay administradores registrados."
    )
else:
    lines = [f"👤 `{row[0]}`" for row in admins]
    text = (
        "⚙️ **ADMINISTRADORES**\n\n"
        "Usuarios con permisos administrativos:\n\n"
        + "\n".join(lines)
    )

await callback.message.edit_text(
    text,
    reply_markup=nav_buttons("owner_panel"),
    parse_mode="Markdown"
)
await callback.answer()

@router.callback_query(F.data == "owner_users")
async def cb_owner_users(callback: CallbackQuery):
if not is_owner(callback.from_user.id):
await callback.answer("❌ Acceso denegado.", show_alert=True)
return

conn = sqlite3.connect(DB_NAME)
cur = conn.cursor()
cur.execute(
    "SELECT id, name, username, balance, is_premium, is_banned "
    "FROM users ORDER BY registered_at DESC LIMIT 50"
)
users = cur.fetchall()
cur.execute("SELECT COUNT(*) FROM users")
total = cur.fetchone()[0]
conn.close()

if not users:
    text = "👥 **USUARIOS**\n\nNo hay usuarios registrados."
else:
    lines = []
    for u in users:
        premium = "💎" if u[4] else "👤"
        banned = " 🚫" if u[5] else ""
        username = (
            f"@{u[2]}"
            if u[2] and u[2] != "Sin username"
            else "Sin username"
        )
        lines.append(
            f"{premium} `{u[0]}` • {username}{banned}\n"
            f"👤 {u[1]}\n"
            f"💰 Saldo: ${u[3]:.2f}"
        )

    text = (
        f"👥 **GESTIÓN DE USUARIOS**\n\n"
        f"📊 Total registrados: **{total}**\n\n"
        + "\n\n".join(lines)
    )

await callback.message.edit_text(
    text,
    reply_markup=nav_buttons("owner_panel"),
    parse_mode="Markdown"
)
await callback.answer()

@router.callback_query(F.data == "owner_products")
async def cb_owner_products(callback: CallbackQuery):
if not is_owner(callback.from_user.id):
await callback.answer("❌ Acceso denegado.", show_alert=True)
return

conn = sqlite3.connect(DB_NAME)
cur = conn.cursor()
cur.execute(
    "SELECT id, category, name, description, price, stock, status "
    "FROM products ORDER BY id DESC LIMIT 50"
)
products = cur.fetchall()
conn.close()

if not products:
    text = "📦 **GESTIÓN DE PRODUCTOS**\n\nNo hay productos registrados."
else:
    lines = []
    for p in products:
        status = (
            "🟢"
            if str(p[6]).lower() in ("disponible", "activo", "available")
            else "🔴"
        )
        lines.append(
            f"{status} `{p[0]}` **{p[2]}**\n"
            f"📂 {p[1]}\n"
            f"💵 ${p[4]:.2f} • 📦 Stock: {p[5]}\n"
            f"📌 {p[6]}"
        )

    text = "📦 **GESTIÓN DE PRODUCTOS**\n\n" + "\n\n".join(lines)

await callback.message.edit_text(
    text,
    reply_markup=nav_buttons("owner_panel"),
    parse_mode="Markdown"
)
await callback.answer()

@router.callback_query(F.data == "owner_payments")
async def cb_owner_payments(callback: CallbackQuery):
if not is_owner(callback.from_user.id):
await callback.answer("❌ Acceso denegado.", show_alert=True)
return

conn = sqlite3.connect(DB_NAME)
cur = conn.cursor()
cur.execute(
    "SELECT id, user_id, amount, method, proof, status, date "
    "FROM payments ORDER BY id DESC LIMIT 30"
)
payments = cur.fetchall()
conn.close()

if not payments:
    text = "💳 **GESTIÓN DE PAGOS**\n\nNo hay pagos registrados."
else:
    lines = []
    for p in payments:
        icon = (
            "🟡" if p[5] == "Pendiente"
            else "🟢" if p[5] == "Aprobado"
            else "🔴"
        )
        lines.append(
            f"{icon} **Pago #{p[0]}**\n"
            f"👤 Usuario: `{p[1]}`\n"
            f"💵 Monto: ${p[2]:.2f}\n"
            f"💳 Método: {p[3]}\n"
            f"📌 Estado: {p[5]}\n"
            f"📅 {p[6]}"
        )

    text = "💳 **GESTIÓN DE PAGOS**\n\n" + "\n\n".join(lines)

await callback.message.edit_text(
    text,
    reply_markup=nav_buttons("owner_panel"),
    parse_mode="Markdown"
)
await callback.answer()

@router.callback_query(F.data == "owner_coupons")
async def cb_owner_coupons(callback: CallbackQuery):
if not is_owner(callback.from_user.id):
await callback.answer("❌ Acceso denegado.", show_alert=True)
return

conn = sqlite3.connect(DB_NAME)
cur = conn.cursor()
cur.execute(
    "SELECT code, discount_type, value, uses_left, expires_at "
    "FROM coupons ORDER BY code LIMIT 50"
)
coupons = cur.fetchall()
conn.close()

if not coupons:
    text = "🎟️ **GESTIÓN DE CUPONES**\n\nNo hay cupones registrados."
else:
    lines = []
    for c in coupons:
        discount = (
            f"{c[2]:.0f}%"
            if c[1].lower() == "percent"
            else f"${c[2]:.2f}"
        )
        expiry = c[4] or "Sin vencimiento"
        lines.append(
            f"🎟️ `{c[0]}`\n"
            f"💎 Descuento: **{discount}**\n"
            f"🔢 Usos restantes: **{c[3]}**\n"
            f"📅 Vence: {expiry}"
        )

    text = "🎟️ **GESTIÓN DE CUPONES**\n\n" + "\n\n".join(lines)

await callback.message.edit_text(
    text,
    reply_markup=nav_buttons("owner_panel"),
    parse_mode="Markdown"
)
await callback.answer()

@router.callback_query(F.data == "owner_settings")
async def cb_owner_settings(callback: CallbackQuery):
if not is_owner(callback.from_user.id):
await callback.answer("❌ Acceso denegado.", show_alert=True)
return

conn = sqlite3.connect(DB_NAME)
cur = conn.cursor()
cur.execute("SELECT key, value FROM settings ORDER BY key")
settings = cur.fetchall()
conn.close()

if not settings:
    text = (
        "🔧 **CONFIGURACIÓN**\n\n"
        "No hay configuraciones personalizadas registradas."
    )
else:
    lines = [
        f"⚙️ **{key}**\n└ {value}"
        for key, value in settings
    ]
    text = "🔧 **CONFIGURACIÓN DEL SISTEMA**\n\n" + "\n\n".join(lines)

await callback.message.edit_text(
    text,
    reply_markup=nav_buttons("owner_panel"),
    parse_mode="Markdown"
)
await callback.answer()

@router.callback_query(F.data == "owner_logs")
async def cb_owner_logs(callback: CallbackQuery):
if not is_owner(callback.from_user.id):
await callback.answer("❌ Acceso denegado.", show_alert=True)
return

conn = sqlite3.connect(DB_NAME)
cur = conn.cursor()

cur.execute(
    "SELECT id, user_id, product_name, price, date, status "
    "FROM purchases ORDER BY id DESC LIMIT 20"
)
purchases = cur.fetchall()

cur.execute(
    "SELECT id, user_id, amount, method, status, date "
    "FROM payments ORDER BY id DESC LIMIT 20"
)
payments = cur.fetchall()

conn.close()

lines = []

for p in purchases:
    lines.append(
        f"🛒 Venta #{p[0]} • Usuario `{p[1]}`\n"
        f"📦 {p[2]} • 💵 ${p[3]:.2f}\n"
        f"📅 {p[4]} • 📌 {p[5]}"
    )

for p in payments:
    lines.append(
        f"💳 Pago #{p[0]} • Usuario `{p[1]}`\n"
        f"💵 ${p[2]:.2f} • {p[3]}\n"
        f"📅 {p[5]} • 📌 {p[4]}"
    )

text = (
    "📜 **REGISTROS DEL SISTEMA**\n\n"
    + ("\n\n".join(lines) if lines else "No hay registros disponibles.")
)

await callback.message.edit_text(
    text,
    reply_markup=nav_buttons("owner_panel"),
    parse_mode="Markdown"
)
await callback.answer()
@router.callback_query(F.data == "owner_broadcast")
async def cb_owner_broadcast(callback: CallbackQuery, state: FSMContext):
if not is_owner(callback.from_user.id):
await callback.answer("❌ Acceso denegado.", show_alert=True)
return

await state.set_state(AdminStates.waiting_for_broadcast)
await callback.message.edit_text(
    "📢 **DIFUSIÓN DEL OWNER**\n\n"
    "Envía el mensaje que deseas enviar a los usuarios "
    "no baneados de la tienda.\n\n"
    "⚠️ El mensaje será enviado tal como lo recibamos.",
    reply_markup=nav_buttons("owner_panel"),
    parse_mode="Markdown"
)
await callback.answer()

@router.callback_query(F.data == "owner_admins")
async def cb_manage_admins(callback: CallbackQuery):
if not is_owner(callback.from_user.id):
await callback.answer("❌ Acceso denegado.", show_alert=True)
return

conn = sqlite3.connect(DB_NAME)
cur = conn.cursor()
cur.execute("SELECT user_id FROM admins ORDER BY user_id")
admins = [row[0] for row in cur.fetchall()]
conn.close()

if admins:
    admin_list = "\n".join(f"👤 `{uid}`" for uid in admins)
else:
    admin_list = "No hay administradores registrados."

kb = InlineKeyboardMarkup(inline_keyboard=[
    [
        InlineKeyboardButton(
            text="➕ Agregar Admin",
            callback_data="owner_add_admin"
        ),
        InlineKeyboardButton(
            text="➖ Quitar Admin",
            callback_data="owner_remove_admin"
        )
    ],
    [
        InlineKeyboardButton(
            text="🏠 Inicio",
            callback_data="main_menu"
        ),
        InlineKeyboardButton(
            text="⬅️ Atrás",
            callback_data="owner_panel"
        )
    ]
])

await callback.message.edit_text(
    "⚙️ **ADMINISTRADORES**\n\n"
    "👥 Administradores actuales:\n\n"
    f"{admin_list}",
    reply_markup=kb,
    parse_mode="Markdown"
)
await callback.answer()

@router.callback_query(F.data == "owner_add_admin")
async def cb_add_admin(callback: CallbackQuery, state: FSMContext):
if not is_owner(callback.from_user.id):
await callback.answer("❌ Acceso denegado.", show_alert=True)
return

await state.set_state(AdminStates.waiting_for_admin_id)
await state.update_data(admin_action="add")

await callback.message.edit_text(
    "➕ **AGREGAR ADMINISTRADOR**\n\n"
    "Envía ahora el ID numérico del usuario que deseas "
    "convertir en administrador.\n\n"
    "Ejemplo:\n"
    "`123456789`",
    reply_markup=nav_buttons("owner_admins"),
    parse_mode="Markdown"
)
await callback.answer()

@router.callback_query(F.data == "owner_remove_admin")
async def cb_remove_admin(callback: CallbackQuery, state: FSMContext):
if not is_owner(callback.from_user.id):
await callback.answer("❌ Acceso denegado.", show_alert=True)
return

await state.set_state(AdminStates.waiting_for_admin_id)
await state.update_data(admin_action="remove")

await callback.message.edit_text(
    "➖ **QUITAR ADMINISTRADOR**\n\n"
    "Envía el ID numérico del administrador que deseas quitar.\n\n"
    "Ejemplo:\n"
    "`123456789`",
    reply_markup=nav_buttons("owner_admins"),
    parse_mode="Markdown"
)
await callback.answer()

@router.message(AdminStates.waiting_for_admin_id)
async def process_admin_change(message: Message, state: FSMContext):
if not is_owner(message.from_user.id):
await state.clear()
return

raw_id = (message.text or "").strip()

if not raw_id.isdigit():
    await message.answer(
        "❌ El ID debe contener únicamente números.",
        reply_markup=nav_buttons("owner_admins"),
        parse_mode="Markdown"
    )
    return

target_id = int(raw_id)
data = await state.get_data()
action = data.get("admin_action")

conn = sqlite3.connect(DB_NAME)
cur = conn.cursor()

if action == "add":
    cur.execute(
        "INSERT OR IGNORE INTO admins (user_id) VALUES (?)",
        (target_id,)
    )
    changed = cur.rowcount > 0
    result = (
        "✅ Usuario agregado como administrador."
        if changed
        else "ℹ️ Ese usuario ya es administrador."
    )
else:
    cur.execute(
        "DELETE FROM admins WHERE user_id = ?",
        (target_id,)
    )
    changed = cur.rowcount > 0
    result = (
        "✅ Administrador eliminado correctamente."
        if changed
        else "ℹ️ Ese usuario no estaba registrado como administrador."
    )

conn.commit()
conn.close()
await state.clear()

await message.answer(
    f"⚙️ **GESTIÓN DE ADMINISTRADORES**\n\n"
    f"👤 ID: `{target_id}`\n"
    f"{result}",
    reply_markup=nav_buttons("owner_admins"),
    parse_mode="Markdown"
)

@router.callback_query(F.data.startswith("payment_approve_"))
async def cb_approve_payment(callback: CallbackQuery):
if not is_admin_or_owner(callback.from_user.id):
await callback.answer("❌ Sin permisos.", show_alert=True)
return

try:
    payment_id = int(callback.data.split("_")[-1])
except (ValueError, IndexError):
    await callback.answer("❌ Solicitud inválida.", show_alert=True)
    return

conn = sqlite3.connect(DB_NAME)
cur = conn.cursor()

cur.execute(
    "SELECT user_id, amount, status FROM payments WHERE id = ?",
    (payment_id,)
)
payment = cur.fetchone()

if not payment:
    conn.close()
    await callback.answer("❌ Pago no encontrado.", show_alert=True)
    return

user_id, amount, status = payment

if status != "Pendiente":
    conn.close()
    await callback.answer(
        f"⚠️ Este pago ya está marcado como {status}.",
        show_alert=True
    )
    return

cur.execute(
    "UPDATE payments SET status = 'Aprobado' WHERE id = ?",
    (payment_id,)
)

cur.execute(
    "UPDATE users SET balance = balance + ? WHERE id = ?",
    (amount, user_id)
)

conn.commit()
conn.close()

try:
    await callback.bot.send_message(
        user_id,
        "✅ **RECARGA APROBADA**\n\n"
        f"💰 Monto acreditado: **${amount:.2f}**\n"
        f"🧾 Solicitud: `#{payment_id}`\n\n"
        "Tu saldo ha sido actualizado correctamente.",
        parse_mode="Markdown"
    )
except TelegramAPIError:
    pass

await callback.message.edit_text(
    "✅ **PAGO APROBADO**\n\n"
    f"🧾 Solicitud: `#{payment_id}`\n"
    f"👤 Usuario: `{user_id}`\n"
    f"💰 Monto: **${amount:.2f}**\n"
    "📌 Estado: **Aprobado**",
    reply_markup=nav_buttons("admin_payments"),
    parse_mode="Markdown"
)
await callback.answer("Pago aprobado correctamente.")

@router.callback_query(F.data.startswith("payment_reject_"))
async def cb_reject_payment(callback: CallbackQuery):
if not is_admin_or_owner(callback.from_user.id):
await callback.answer("❌ Sin permisos.", show_alert=True)
return

try:
    payment_id = int(callback.data.split("_")[-1])
except (ValueError, IndexError):
    await callback.answer("❌ Solicitud inválida.", show_alert=True)
    return

conn = sqlite3.connect(DB_NAME)
cur = conn.cursor()

cur.execute(
    "SELECT user_id, amount, status FROM payments WHERE id = ?",
    (payment_id,)
)
payment = cur.fetchone()

if not payment:
    conn.close()
    await callback.answer("❌ Pago no encontrado.", show_alert=True)
    return

user_id, amount, status = payment

if status != "Pendiente":
    conn.close()
    await callback.answer(
        f"⚠️ Este pago ya está marcado como {status}.",
        show_alert=True
    )
    return

cur.execute(
    "UPDATE payments SET status = 'Rechazado' WHERE id = ?",
    (payment_id,)
)
conn.commit()
conn.close()

try:
    await callback.bot.send_message(
        user_id,
        "❌ **RECARGA RECHAZADA**\n\n"
        f"🧾 Solicitud: `#{payment_id}`\n"
        f"💰 Monto: **${amount:.2f}**\n\n"
        "Tu comprobante no fue aprobado. "
        "Si consideras que hubo un error, contacta con soporte.",
        parse_mode="Markdown"
    )
except TelegramAPIError:
    pass

await callback.message.edit_text(
    "❌ **PAGO RECHAZADO**\n\n"
    f"🧾 Solicitud: `#{payment_id}`\n"
    f"👤 Usuario: `{user_id}`\n"
    f"💰 Monto: **${amount:.2f}**\n"
    "📌 Estado: **Rechazado**",
    reply_markup=nav_buttons("admin_payments"),
    parse_mode="Markdown"
)
await callback.answer("Pago rechazado correctamente.")
@router.callback_query(F.data.startswith("user_ban_"))
async def cb_user_ban(callback: CallbackQuery):
if not is_admin_or_owner(callback.from_user.id):
await callback.answer("❌ Sin permisos.", show_alert=True)
return

try:
    user_id = int(callback.data.split("_")[-1])
except (ValueError, IndexError):
    await callback.answer("❌ Usuario inválido.", show_alert=True)
    return

if is_owner(user_id):
    await callback.answer(
        "❌ No puedes modificar al Owner.",
        show_alert=True
    )
    return

conn = sqlite3.connect(DB_NAME)
cur = conn.cursor()
cur.execute(
    "UPDATE users SET is_banned = 1 WHERE id = ?",
    (user_id,)
)
changed = cur.rowcount > 0
conn.commit()
conn.close()

if not changed:
    await callback.answer("❌ Usuario no encontrado.", show_alert=True)
    return

try:
    await callback.bot.send_message(
        user_id,
        "🚫 **CUENTA RESTRINGIDA**\n\n"
        "Tu acceso a la tienda ha sido restringido por un administrador.",
        parse_mode="Markdown"
    )
except TelegramAPIError:
    pass

await callback.answer("✅ Usuario baneado correctamente.")
await callback.message.edit_text(
    "🚫 **USUARIO BLOQUEADO**\n\n"
    f"🆔 ID: `{user_id}`\n"
    "📌 Estado: **Baneado**",
    reply_markup=nav_buttons("admin_users"),
    parse_mode="Markdown"
)

@router.callback_query(F.data.startswith("user_unban_"))
async def cb_user_unban(callback: CallbackQuery):
if not is_admin_or_owner(callback.from_user.id):
await callback.answer("❌ Sin permisos.", show_alert=True)
return

try:
    user_id = int(callback.data.split("_")[-1])
except (ValueError, IndexError):
    await callback.answer("❌ Usuario inválido.", show_alert=True)
    return

conn = sqlite3.connect(DB_NAME)
cur = conn.cursor()
cur.execute(
    "UPDATE users SET is_banned = 0 WHERE id = ?",
    (user_id,)
)
changed = cur.rowcount > 0
conn.commit()
conn.close()

if not changed:
    await callback.answer("❌ Usuario no encontrado.", show_alert=True)
    return

try:
    await callback.bot.send_message(
        user_id,
        "✅ **CUENTA RESTAURADA**\n\n"
        "Tu acceso a la tienda ha sido restaurado.",
        parse_mode="Markdown"
    )
except TelegramAPIError:
    pass

await callback.answer("Usuario desbloqueado.")
await callback.message.edit_text(
    "✅ **USUARIO DESBLOQUEADO**\n\n"
    f"🆔 ID: `{user_id}`\n"
    "📌 Estado: **Activo**",
    reply_markup=nav_buttons("admin_users"),
    parse_mode="Markdown"
)

@router.callback_query(F.data.startswith("user_premium_"))
async def cb_user_premium(callback: CallbackQuery):
if not is_admin_or_owner(callback.from_user.id):
await callback.answer("❌ Sin permisos.", show_alert=True)
return

try:
    user_id = int(callback.data.split("_")[-1])
except (ValueError, IndexError):
    await callback.answer("❌ Usuario inválido.", show_alert=True)
    return

conn = sqlite3.connect(DB_NAME)
cur = conn.cursor()
cur.execute(
    "SELECT is_premium FROM users WHERE id = ?",
    (user_id,)
)
user = cur.fetchone()

if not user:
    conn.close()
    await callback.answer("❌ Usuario no encontrado.", show_alert=True)
    return

new_status = 0 if user[0] else 1

cur.execute(
    "UPDATE users SET is_premium = ? WHERE id = ?",
    (new_status, user_id)
)
conn.commit()
conn.close()

status_text = "ACTIVADO 💎" if new_status else "DESACTIVADO ❌"

try:
    await callback.bot.send_message(
        user_id,
        f"💎 **PREMIUM {status_text}**\n\n"
        + (
            "Tu membresía Premium ha sido activada."
            if new_status
            else "Tu membresía Premium ha sido desactivada."
        ),
        parse_mode="Markdown"
    )
except TelegramAPIError:
    pass

await callback.message.edit_text(
    "💎 **ESTADO PREMIUM ACTUALIZADO**\n\n"
    f"🆔 Usuario: `{user_id}`\n"
    f"📌 Estado: **{'Activo' if new_status else 'Inactivo'}**",
    reply_markup=nav_buttons("admin_users"),
    parse_mode="Markdown"
)
await callback.answer("Estado Premium actualizado.")

@router.callback_query(F.data.startswith("product_delete_"))
async def cb_product_delete(callback: CallbackQuery):
if not is_owner(callback.from_user.id):
await callback.answer("❌ Solo el Owner puede eliminar productos.", show_alert=True)
return

try:
    product_id = int(callback.data.split("_")[-1])
except (ValueError, IndexError):
    await callback.answer("❌ Producto inválido.", show_alert=True)
    return

conn = sqlite3.connect(DB_NAME)
cur = conn.cursor()
cur.execute(
    "SELECT name FROM products WHERE id = ?",
    (product_id,)
)
product = cur.fetchone()

if not product:
    conn.close()
    await callback.answer("❌ Producto no encontrado.", show_alert=True)
    return

cur.execute(
    "DELETE FROM products WHERE id = ?",
    (product_id,)
)
conn.commit()
conn.close()

await callback.message.edit_text(
    "🗑️ **PRODUCTO ELIMINADO**\n\n"
    f"📦 Producto: **{product[0]}**\n"
    f"🆔 ID: `{product_id}`\n\n"
    "El producto fue eliminado correctamente.",
    reply_markup=nav_buttons("owner_products"),
    parse_mode="Markdown"
)
await callback.answer("Producto eliminado.")

@router.callback_query(F.data.startswith("coupon_delete_"))
async def cb_coupon_delete(callback: CallbackQuery):
if not is_owner(callback.from_user.id):
await callback.answer("❌ Solo el Owner puede eliminar cupones.", show_alert=True)
return

code = callback.data[len("coupon_delete_"):].strip().upper()

if not code:
    await callback.answer("❌ Cupón inválido.", show_alert=True)
    return

conn = sqlite3.connect(DB_NAME)
cur = conn.cursor()
cur.execute(
    "SELECT code FROM coupons WHERE code = ?",
    (code,)
)
coupon = cur.fetchone()

if not coupon:
    conn.close()
    await callback.answer("❌ Cupón no encontrado.", show_alert=True)
    return

cur.execute(
    "DELETE FROM coupons WHERE code = ?",
    (code,)
)
conn.commit()
conn.close()

await callback.message.edit_text(
    "🗑️ **CUPÓN ELIMINADO**\n\n"
    f"🎟️ Código: `{code}`\n\n"
    "El cupón fue eliminado correctamente.",
    reply_markup=nav_buttons("owner_coupons"),
    parse_mode="Markdown"
)
await callback.answer("Cupón eliminado.")
