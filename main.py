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
