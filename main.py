import os, sqlite3, time, logging
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

logging.basicConfig(level=logging.INFO)
w = Flask(__name__)

@w.route('/')
def h():
    return "OK"

Thread(target=lambda: w.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080))), daemon=True).start()

TOKEN = os.getenv("BOT_TOKEN", "8799688315:AAH3afiU9b8RdEuWtCtj3ooBTopEgaJMFFg")
OWNER_ID = int(os.getenv("OWNER_ID", "7939709543"))
bot = Bot(token=TOKEN)
dp = Dispatcher()
BANNER = "https://i.ibb.co/3m20gX28/51614.jpg"

def db():
    conn = sqlite3.connect("r.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS u(user_id INT PRIMARY KEY, first TEXT, uname TEXT, saldo REAL DEFAULT 0, rango TEXT DEFAULT 'Cliente', prem INT DEFAULT 0, reg TEXT, ban INT DEFAULT 0)")
    cursor.execute("CREATE TABLE IF NOT EXISTS p(id INTEGER PRIMARY KEY AUTOINCREMENT, cat TEXT, nombre TEXT, precio REAL, desc TEXT, stock INT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS a(user_id INT PRIMARY KEY)")
    cursor.execute("CREATE TABLE IF NOT EXISTS c(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INT, prod TEXT, precio REAL, fecha TEXT)")
    conn.commit()
    conn.close()

db()

def es_admin(u):
    if u == OWNER_ID:
        return True
    conn = sqlite3.connect("r.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM a WHERE user_id=?", (u,))
    r = cursor.fetchone()
    conn.close()
    return r is not None

def esta_baneado(u):
    conn = sqlite3.connect("r.db")
    cursor = conn.cursor()
    cursor.execute("SELECT ban FROM u WHERE user_id=?", (u,))
    r = cursor.fetchone()
    conn.close()
    return r and r[0] == 1

def menu_principal(u):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛍️ Catálogo", callback_data="cat"), InlineKeyboardButton(text="👤 Perfil", callback_data="per")],
        [InlineKeyboardButton(text="💳 Recargar", callback_data="rec"), InlineKeyboardButton(text="🎟️ Cupones", callback_data="cup")],
        [InlineKeyboardButton(text="💎 Premium", callback_data="pre"), InlineKeyboardButton(text="📦 Mis Compras", callback_data="com")],
        [InlineKeyboardButton(text="📞 Soporte", url="https://t.me/StoreFixersXiters"), InlineKeyboardButton(text="📢 Canal", url="https://t.me/StoreFixersXiters")]
    ])
    if u == OWNER_ID:
        kb.inline_keyboard.append([InlineKeyboardButton(text="👑 Panel Owner", callback_data="po")])
    elif es_admin(u):
        kb.inline_keyboard.append([InlineKeyboardButton(text="⚙️ Panel Admin", callback_data="pa")])
    return kb

def texto_inicio(u, f):
    conn = sqlite3.connect("r.db")
    cursor = conn.cursor()
    cursor.execute("SELECT saldo, rango, prem FROM u WHERE user_id=?", (u,))
    r = cursor.fetchone()
    conn.close()
    s = r[0] if r else 0.0
    rg = r[1] if r else "Cliente"
    pm = "💎 Sí" if (r and r[2] == 1) else "No"
    return (
        f"⚡ **RAYO FIX STORE** ⚡\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 **Cliente:** {f}\n"
        f"🆔 **ID:** `{u}`\n"
        f"💰 **Saldo:** `${s:.2f} USD`\n"
        f"⭐ **Rango:** {rg} | **Membresía:** {pm}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Selecciona una opción:"
    )

async def actualizar(q, txt, mk):
    try:
        msg = q.message
        if msg.photo:
            await bot.edit_message_caption(chat_id=msg.chat.id, message_id=msg.message_id, caption=txt, reply_markup=mk, parse_mode="Markdown")
        else:
            await bot.edit_message_text(chat_id=msg.chat.id, message_id=msg.message_id, text=txt, reply_markup=mk, parse_mode="Markdown")
    except Exception:
        pass

@dp.message(F.text.startswith("/start"))
async def start_cmd(m: Message):
    u = m.from_user.id
    if esta_baneado(u):
        await m.answer("❌ Tu cuenta está suspendida.")
        return
    f, un, dt = m.from_user.first_name, m.from_user.username or "N/D", time.strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect("r.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO u(user_id, first, uname, reg) VALUES(?,?,?,?)", (u, f, un, dt))
    conn.commit()
    conn.close()
    try:
        await m.answer_photo(photo=BANNER, caption=texto_inicio(u, f), reply_markup=menu_principal(u), parse_mode="Markdown")
    except Exception:
        await m.answer(texto_inicio(u, f), reply_markup=menu_principal(u), parse_mode="Markdown")

@dp.callback_query()
async def callbacks(q: CallbackQuery):
    await q.answer()
    u = q.from_user.id
    if esta_baneado(u):
        return await q.answer("❌ Cuenta suspendida.", show_alert=True)
    dt, f = q.data, q.from_user.first_name

    try:
        if dt == "inicio":
            await actualizar(q, texto_inicio(u, f), menu_principal(u))
        elif dt == "cat":
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📱 Android", callback_data="ca_Android")],
                [InlineKeyboardButton(text="🍎 iPhone / iOS", callback_data="ca_iOS")],
                [InlineKeyboardButton(text="🖥️ Windows / PC", callback_data="ca_PC")],
                [InlineKeyboardButton(text="🏠 Inicio", callback_data="inicio")]
            ])
            await actualizar(q, "📂 **CATÁLOGO**\n\nElige categoría:", kb)
        elif dt.startswith("ca_"):
            cg = dt.split("_")[1]
            if cg == "PC":
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Atrás", callback_data="cat")],
                    [InlineKeyboardButton(text="🏠 Inicio", callback_data="inicio")]
                ])
                return await actualizar(q, "🖥️ **WINDOWS / PC**\n\n🚧 Próximamente...", kb)
            conn = sqlite3.connect("r.db")
            cursor = conn.cursor()
            cursor.execute("SELECT id, nombre, precio FROM p WHERE cat=?", (cg,))
            ps = cursor.fetchall()
            conn.close()
            kb = [[InlineKeyboardButton(text=f"📦 {n} - ${p:.2f}", callback_data=f"vp_{i}")] for i, n, p in ps]
            kb.append([InlineKeyboardButton(text="⬅️ Atrás", callback_data="cat"), InlineKeyboardButton(text="🏠 Inicio", callback_data="inicio")])
            txt = f"📂 **CATEGORÍA: {cg.upper()}**\n\nSelecciona producto:" if ps else f"📂 **CATEGORÍA: {cg.upper()}**\n\n⚠️ Sin stock disponible."
            await actualizar(q, txt, InlineKeyboardMarkup(inline_keyboard=kb))
        elif dt.startswith("vp_"):
            pid = int(dt.split("_")[1])
            conn = sqlite3.connect("r.db")
            cursor = conn.cursor()
            cursor.execute("SELECT nombre, precio, desc, stock, cat FROM p WHERE id=?", (pid,))
            pr = cursor.fetchone()
            conn.close()
            if pr:
                n, p, ds, st, cg = pr
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=f"🛒 Comprar (${p:.2f})", callback_data=f"cp_{pid}")],
                    [InlineKeyboardButton(text="⬅️ Atrás", callback_data=f"ca_{cg}"), InlineKeyboardButton(text="🏠 Inicio", callback_data="inicio")]
                ])
                await actualizar(q, f"📦 **{n}**\n\n📝 {ds}\n💰 `${p:.2f} USD`\n📦 Stock: `{st}`", kb)
        elif dt.startswith("cp_"):
            pid = int(dt.split("_")[1])
            conn = sqlite3.connect("r.db")
            cursor = conn.cursor()
            cursor.execute("SELECT saldo FROM u WHERE user_id=?", (u,))
            sd = cursor.fetchone()[0]
            cursor.execute("SELECT nombre, precio, stock FROM p WHERE id=?", (pid,))
            pr = cursor.fetchone()
            if pr:
                n, p, st = pr
                if st <= 0:
                    await q.answer("❌ Sin stock.", show_alert=True)
                elif sd < p:
                    await q.answer("❌ Saldo insuficiente.", show_alert=True)
                else:
                    cursor.execute("UPDATE u SET saldo=saldo-? WHERE user_id=?", (p, u))
                    cursor.execute("UPDATE p SET stock=stock-1 WHERE id=?", (pid,))
                    cursor.execute("INSERT INTO c(user_id, prod, precio, fecha) VALUES(?,?,?,?)", (u, n, p, time.strftime("%Y-%m-%d %H:%M:%S")))
                    conn.commit()
                    await q.answer("✅ Compra exitosa!", show_alert=True)
                    try:
                        await bot.send_message(OWNER_ID, f"🔔 **Nueva Compra**\n👤 Usuario: `{u}`\n📦 Producto: {n}\n💰 Precio: `${p:.2f}`", parse_mode="Markdown")
                    except Exception:
                        pass
            conn.close()
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Inicio", callback_data="inicio")]])
            await actualizar(q, "🎉 ¡Gracias por tu compra!", kb)
        elif dt == "per":
            conn = sqlite3.connect("r.db")
            cursor = conn.cursor()
            cursor.execute("SELECT saldo, rango, prem, reg FROM u WHERE user_id=?", (u,))
            r = cursor.fetchone()
            cursor.execute("SELECT COUNT(*) FROM c WHERE user_id=?", (u,))
            tc = cursor.fetchone()[0]
            conn.close()
            sd, rg, pm, reg_dt = (r[0] if r else 0, r[1] if r else "Cliente", "Sí" if (r and r[2] == 1) else "No", r[3] if r else "")
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Inicio", callback_data="inicio")]])
            await actualizar(q, f"👤 **PERFIL**\n\n• Nombre: {f}\n• ID: `{u}`\n• Saldo: `${sd:.2f}`\n• Membresía: {pm}\n• Compras: {tc}\n• Registro: {reg_dt}", kb)
        elif dt == "rec":
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Inicio", callback_data="inicio")]])
            await actualizar(q, "💳 **RECARGA**\n\nYape / Plin / Binance Pay / USDT.\nEnvía tu comprobante al soporte con tu ID.", kb)
        elif dt == "cup":
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Inicio", callback_data="inicio")]])
            await actualizar(q, "🎟️ **CUPÓN**\n\nEnvía tu código promocional a soporte.", kb)
        elif dt == "pre":
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Inicio", callback_data="inicio")]])
            await actualizar(q, "💎 **PREMIUM**\n\nObtén 10% de descuento y beneficios exclusivos comunicándote con soporte.", kb)
        elif dt == "com":
            conn = sqlite3.connect("r.db")
            cursor = conn.cursor()
            cursor.execute("SELECT prod, precio, fecha FROM c WHERE user_id=?", (u,))
            cs = cursor.fetchall()
            conn.close()
            tx = "📦 **HISTORIAL**\n\n" + ("\n".join([f"• {pr} - ${prc:.2f} ({dt_c})" for pr, prc, dt_c in cs]) if cs else "No tienes compras.")
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Inicio", callback_data="inicio")]])
            await actualizar(q, tx, kb)
        elif dt == "po":
            if u != OWNER_ID:
                return
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Agregar Prod", callback_data="oa"), InlineKeyboardButton(text="🗑️ Eliminar Prod", callback_data="od")],
                [InlineKeyboardButton(text="💰 Dar Saldo", callback_data="os"), InlineKeyboardButton(text="🛡️ Dar Admin", callback_data="oa_d")],
                [InlineKeyboardButton(text="📊 Estadísticas", callback_data="ost")],
                [InlineKeyboardButton(text="🏠 Inicio", callback_data="inicio")]
            ])
            await actualizar(q, "👑 **PANEL OWNER**", kb)
        elif dt == "oa":
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Atrás", callback_data="po")],
                [InlineKeyboardButton(text="🏠 Inicio", callback_data="inicio")]
            ])
            await actualizar(q, "➕ **AGREGAR PRODUCTO**\n\nUsa en el chat:\n`/addprod Categoria Nombre Precio Stock Descripcion`", kb)
        elif dt == "od":
            conn = sqlite3.connect("r.db")
            cursor = conn.cursor()
            cursor.execute("SELECT id, nombre FROM p")
            ps = cursor.fetchall()
            conn.close()
            kb = [[InlineKeyboardButton(text=f"❌ {n}", callback_data=f"dp_{i}")] for i, n in ps]
            kb.append([InlineKeyboardButton(text="⬅️ Atrás", callback_data="po"), InlineKeyboardButton(text="🏠 Inicio", callback_data="inicio")])
            await actualizar(q, "🗑️ **ELIMINAR PRODUCTO**\n\nSelecciona el producto:", InlineKeyboardMarkup(inline_keyboard=kb))
        elif dt.startswith("dp_"):
            pid = int(dt.split("_")[1])
            conn = sqlite3.connect("r.db")
            cursor = conn.cursor()
            cursor.execute("DELETE FROM p WHERE id=?", (pid,))
            conn.commit()
            conn.close()
            await q.answer("✅ Eliminado.", show_alert=True)
            kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Inicio", callback_data="inicio")]])
            await actualizar(q, "✅ Producto eliminado con éxito.", kb)
        elif dt == "os":
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Atrás", callback_data="po")],
                [InlineKeyboardButton(text="🏠 Inicio", callback_data="inicio")]
            ])
            await actualizar(q, "💰 **DAR SALDO**\n\nUsa en el chat:\n`/darsaldo ID_USUARIO MONTO`", kb)
        elif dt == "oa_d":
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Atrás", callback_data="po")],
                [InlineKeyboardButton(text="🏠 Inicio", callback_data="inicio")]
            ])
            await actualizar(q, "🛡️ **DAR ADMIN**\n\nUsa en el chat:\n`/daradmin ID_USUARIO`", kb)
        elif dt == "ost":
            conn = sqlite3.connect("r.db")
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM u")
            tu = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM u WHERE prem=1")
            tp = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*), SUM(precio) FROM c")
            res = cursor.fetchone()
            v, ig = res[0] or 0, res[1] or 0.0
            conn.close()
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Atrás", callback_data="po")],
                [InlineKeyboardButton(text="🏠 Inicio", callback_data="inicio")]
            ])
            await actualizar(q, f"📊 **ESTADÍSTICAS**\n\n👥 Usuarios: `{tu}`\n💎 Premium: `{tp}`\n📦 Ventas: `{v}`\n💵 Ingresos: `${ig:.2f}`", kb)
        elif dt == "pa":
            if not es_admin(u):
                return
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💰 Dar Saldo", callback_data="os")],
                [InlineKeyboardButton(text="🏠 Inicio", callback_data="inicio")]
            ])
            await actualizar(q, "⚙️ **PANEL ADMIN**", kb)
    except Exception:
        pass

@dp.message(F.text.startswith("/addprod"))
async def addprod_cmd(m: Message):
    if m.from_user.id != OWNER_ID:
        return
    try:
        _, cg, n, pr, st, ds = m.text.split(maxsplit=5)
        conn = sqlite3.connect("r.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO p(cat, nombre, precio, stock, desc) VALUES(?,?,?,?,?)", (cg, n, float(pr), int(st), ds))
        conn.commit()
        conn.close()
        await m.reply(f"✅ Producto **{n}** agregado con éxito.", parse_mode="Markdown")
    except Exception:
        await m.reply("❌ Formato incorrecto. Uso:\n`/addprod Android DripMod 5.00 10 APK Mod`", parse_mode="Markdown")

@dp.message(F.text.startswith("/darsaldo"))
async def darsaldo_cmd(m: Message):
    if not es_admin(m.from_user.id):
        return
    try:
        _, tid, mnt = m.text.split()
        tid, mnt = int(tid), float(mnt)
        conn = sqlite3.connect("r.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE u SET saldo=saldo+? WHERE user_id=?", (mnt, tid))
        conn.commit()
        conn.close()
        await m.reply(f"✅ Se agregaron **${mnt:.2f} USD** al usuario `{tid}`.", parse_mode="Markdown")
    except Exception:
        await m.reply("❌ Uso incorrecto. Ejemplo:\n`/darsaldo 123456789 10`", parse_mode="Markdown")

@dp.message(F.text.startswith("/daradmin"))
async def daradmin_cmd(m: Message):
    if m.from_user.id != OWNER_ID:
        return
    try:
        tid = int(m.text.split()[1])
        conn = sqlite3.connect("r.db")
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO a(user_id) VALUES(?)", (tid,))
        cursor.execute("UPDATE u SET rango='Administrador' WHERE user_id=?", (tid,))
        conn.commit()
        conn.close()
        await m.reply(f"✅ Usuario `{tid}` ascendido a Administrador.", parse_mode="Markdown")
    except Exception:
        await m.reply("❌ Uso incorrecto. Ejemplo:\n`/daradmin 123456789`", parse_mode="Markdown")

if __name__ == "__main__":
    import asyncio
    while True:
        try:
            asyncio.run(dp.start_polling(bot, skip_updates=True))
        except Exception:
            time.sleep(15)
             
