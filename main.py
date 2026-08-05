import os,sqlite3,time,logging
from threading import Thread
from flask import Flask
from aiogram import Bot,Dispatcher,F
from aiogram.types import Message,CallbackQuery,InlineKeyboardMarkup,InlineKeyboardButton
logging.basicConfig(level=logging.INFO)
w=Flask(__name__)
@w.route('/')
def h():return"OK"
Thread(target=lambda:w.run(host="0.0.0.0",port=int(os.environ.get("PORT",8080))),daemon=True).start()
T,O=os.getenv("BOT_TOKEN","8799688315:AAH3afiU9b8RdEuWtCtj3ooBTopEgaJMFFg"),int(os.getenv("OWNER_ID","7939709543"))
b,d=Bot(token=T),Dispatcher()
B="https://i.ibb.co/3m20gX28/51614.jpg"
def db():
 c=sqlite3.connect("r.db")
 x=c.cursor()
 x.execute("CREATE TABLE IF NOT EXISTS u(user_id INT PRIMARY KEY,first TEXT,uname TEXT,saldo REAL DEFAULT 0,rango TEXT DEFAULT 'Cliente',prem INT DEFAULT 0,reg TEXT,ban INT DEFAULT 0)")
 x.execute("CREATE TABLE IF NOT EXISTS p(id INTEGER PRIMARY KEY AUTOINCREMENT,cat TEXT,nombre TEXT,precio REAL,desc TEXT,stock INT)")
 x.execute("CREATE TABLE IF NOT EXISTS a(user_id INT PRIMARY KEY)")
 x.execute("CREATE TABLE IF NOT EXISTS c(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INT,prod TEXT,precio REAL,fecha TEXT)")
 c.commit();c.close()
db()
def ao(u):
 if u==O:return True
 c=sqlite3.connect("r.db");x=c.cursor();x.execute("SELECT user_id FROM a WHERE user_id=?",(u,));r=x.fetchone();c.close();return r is not None
def ban(u):
 c=sqlite3.connect("r.db");x=c.cursor();x.execute("SELECT ban FROM u WHERE user_id=?",(u,));r=x.fetchone();c.close();return r and r[0]==1
def m_u(u):
 k=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🛍️ Catálogo",callback_data="cat"),InlineKeyboardButton(text="👤 Perfil",callback_data="per")],[InlineKeyboardButton(text="💳 Recargar",callback_data="rec"),InlineKeyboardButton(text="🎟️ Cupones",callback_data="cup")],[InlineKeyboardButton(text="💎 Premium",callback_data="pre"),InlineKeyboardButton(text="📦 Mis Compras",callback_data="com")],[InlineKeyboardButton(text="📞 Soporte",url="https://t.me/StoreFixersXiters"),InlineKeyboardButton(text="📢 Canal",url="https://t.me/StoreFixersXiters")]])
 if u==O:k.inline_keyboard.append([InlineKeyboardButton(text="👑 Panel Owner",callback_data="po")])
 elif ao(u):k.inline_keyboard.append([InlineKeyboardButton(text="⚙️ Panel Admin",callback_data="pa")])
 return k
def t_u(u,f):
 c=sqlite3.connect("r.db");x=c.cursor();x.execute("SELECT saldo,rango,prem FROM u WHERE user_id=?",(u,));r=x.fetchone();c.close()
 s,rg,pm=r[0] if r else 0.0,r[1] if r else "Cliente","💎 Sí" if r and r[2]==1 else "No"
 return f"⚡ **RAYO FIX STORE** ⚡\n━━━━━━━━━━━━━━━━━━━━━━\n👤 **Cliente:** {f}\n🆔 **ID:** `{u}`\n💰 **Saldo:** `${s:.2f} USD`\n⭐ **Rango:** {rg} | **Membresía:** {pm}\n━━━━━━━━━━━━━━━━━━━━━━\nSelecciona una opción:"
async def up(q,txt,mk):
 try:
  if q.message.photo:await b.edit_message_caption(chat_id=q.message.chat.id,message_id=q.message.message_id,caption=txt,reply_markup=mk,parse_mode="Markdown")
  else:await b.edit_message_text(chat_id=q.message.chat.id,message_id=q.message.message_id,text=txt,reply_markup=mk,parse_mode="Markdown")
 except Exception:pass
@d.message(F.text.startswith("/start"))
async def s(m:Message):
 u=m.from_user.id
 if ban(u):return await m.answer("❌ Cuenta suspendida.")
 f,un,dt=m.from_user.first_name,m.from_user.username or "N/D",time.strftime("%Y-%m-%d %H:%M:%S")
 c=sqlite3.connect("r.db");x=c.cursor();x.execute("INSERT OR IGNORE INTO u(user_id,first,uname,reg) VALUES(?,?,?,?)",(u,f,un,dt));c.commit();c.close()
 try:await m.answer_photo(photo=B,caption=t_u(u,f),reply_markup=m_u(u),parse_mode="Markdown")
 except Exception:await m.answer(t_u(u,f),reply_markup=m_u(u),parse_mode="Markdown")
@d.callback_query()
async def cb(q:CallbackQuery):
 await q.answer();u=q.from_user.id
 if ban(u):return await q.answer("❌ Cuenta suspendida.",show_alert=True)
 dt,f=q.data,q.from_user.first_name
 try:
  if dt=="inicio":await up(q,t_u(u,f),m_u(u))
  elif dt=="cat":await up(q,"📂 **CATÁLOGO**\n\nElige categoría:",InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📱 Android",callback_data="ca_Android")],[InlineKeyboardButton(text="🍎 iPhone / iOS",callback_data="ca_iOS")],[InlineKeyboardButton(text="🖥️ Windows / PC",callback_data="ca_PC")],[InlineKeyboardButton(text="🏠 Inicio",callback_data="inicio")]]))
  elif dt.startswith("ca_"):
   cg=dt.split("_")[1]
   if cg=="PC":return await up(q,"🖥️ **WINDOWS / PC**\n\n🚧 Próximamente...",InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Atrás",callback_data="cat")],[InlineKeyboardButton(text="🏠 Inicio",callback_data="inicio")]]))
   c=sqlite3.connect("r.db");x=c.cursor();x.execute("SELECT id,nombre,precio FROM p WHERE cat=?",(cg,));ps=x.fetchall();c.close()
   kb=[[InlineKeyboardButton(text=f"📦 {n} - ${p:.2f}",callback_data=f"vp_{i}")] for i,n,p in ps]
   kb.append([InlineKeyboardButton(text="⬅️ Atrás",callback_data="cat"),InlineKeyboardButton(text="🏠 Inicio",callback_data="inicio")])
   await up(q,f"📂 **CATEGORÍA: {cg.upper()}**\n\nSelecciona producto:" if ps else f"📂 **CATEGORÍA: {cg.upper()}**\n\n⚠️ Sin stock.",InlineKeyboardMarkup(inline_keyboard=kb))
  elif dt.startswith("vp_"):
   pid=int(dt.split("_")[1])
   c=sqlite3.connect("r.db");x=c.cursor();x.execute("SELECT nombre,precio,desc,stock,cat FROM p WHERE id=?",(pid,));pr=x.fetchone();c.close()
   if pr:
    n,p,ds,st,cg=pr
    await up(q,f"📦 **{n}**\n\n📝 {ds}\n💰 `${p:.2f} USD`\n📦 Stock: `{st}`",InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"🛒 Comprar (${p:.2f})",callback_data=f"cp_{pid}")],[InlineKeyboardButton(text="⬅️ Atrás",callback_data=f"ca_{cg}"),InlineKeyboardButton(text="🏠 Inicio",callback_data="inicio")]]))
  elif dt.startswith("cp_"):
   pid=int(dt.split("_")[1])
   c=sqlite3.connect("r.db");x=c.cursor()
   x.execute("SELECT saldo FROM u WHERE user_id=?",(u,));sd=x.fetchone()[0]
   x.execute("SELECT nombre,precio,stock FROM p WHERE id=?",(pid,));pr=x.fetchone()
   if pr:
    n,p,st=pr
    if st<=0:await q.answer("❌ Sin stock.",show_alert=True)
    elif sd<p:await q.answer("❌ Saldo insuficiente.",show_alert=True)
    else:
     x.execute("UPDATE u SET saldo=saldo-? WHERE user_id=?",(p,u))
     x.execute("UPDATE p SET stock=stock-1 WHERE id=?",(pid,))
     x.execute("INSERT INTO c(user_id,prod,precio,fecha) VALUES(?,?,?,?)",(u,n,p,time.strftime("%Y-%m-%d %H:%M:%S")))
     c.commit();await q.answer("✅ Compra exitosa!",show_alert=True)
     try:await b.send_message(O,f"🔔 **Compra**\n👤 `{u}`\n📦 {n}\n💰 `${p:.2f}`",parse_mode="Markdown")
     except Exception:pass
   c.close();await up(q,"🎉 ¡Gracias por tu compra!",InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Inicio",callback_data="inicio")]]))
  elif dt=="per":
   c=sqlite3.connect("r.db");x=c.cursor();x.execute("SELECT saldo,rango,prem,reg FROM u WHERE user_id=?",(u,));r=x.fetchone();x.execute("SELECT COUNT(*) FROM c WHERE user_id=?",(u,));tc=x.fetchone()[0];c.close()
   sd,rg,pm,rg_dt=r[0] if r else 0,"Cliente","Sí" if r and r[2]==1 else "No",r[3] if r else ""
   await up(q,f"👤 **PERFIL**\n\n• Nombre: {f}\n• ID: `{u}`\n• Saldo: `${sd:.2f}`\n• Membresía: {pm}\n• Compras: {tc}\n• Registro: {rg_dt}",InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Inicio",callback_data="inicio")]]))
  elif dt=="rec":await up(q,"💳 **RECARGA**\n\nYape / Plin / Binance Pay / USDT.\nEnvía comprobante a soporte.",InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Inicio",callback_data="inicio")]]))
  elif dt=="cup":await up(q,"🎟️ **CUPÓN**\n\nEnvía tu código a soporte.",InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Inicio",callback_data="inicio")]]))
  elif dt=="pre":await up(q,"💎 **PREMIUM**\n\n10% de descuento. Contacta a soporte.",InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Inicio",callback_data="inicio")]]))
  elif dt=="com":
   c=sqlite3.connect("r.db");x=c.cursor();x.execute("SELECT prod,precio,fecha FROM c WHERE user_id=?",(u,));cs=x.fetchall();c.close()
   tx="📦 **HISTORIAL**\n\n" + ("\n".join([f"• {pr} - ${prc:.2f} ({dt_c})" for pr,prc,dt_c in cs]) if cs else "Sin compras.")
   await up(q,tx,InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Inicio",callback_data="inicio")]]))
  elif dt=="po":
   if u!=O:return
   await up(q,"👑 **PANEL OWNER**",InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="➕ Agregar Prod",callback_data="oa"),InlineKeyboardButton(text="🗑️ Eliminar Prod",callback_data="od")],[InlineKeyboardButton(text="💰 Dar Saldo",callback_data="os"),InlineKeyboardButton(text="🛡️ Dar Admin",callback_data="oa_d")],[InlineKeyboardButton(text="📊 Estadísticas",callback_data="ost")],[InlineKeyboardButton(text="🏠 Inicio",callback_data="inicio")]]))
  elif dt=="oa":await up(q,"➕ **AGREGAR**\n\nUsa: `/addprod Cat Nombre Precio Stock Desc`",InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Atrás",callback_data="po")],[InlineKeyboardButton(text="🏠 Inicio",callback_data="inicio")]]))
  elif dt=="od":
   c=sqlite3.connect("r.db");x=c.cursor();x.execute("SELECT id,nombre FROM p");ps=x.fetchall();c.close()
   kb=[[InlineKeyboardButton(text=f"❌ {n}",callback_data=f"dp_{i}")] for i,n in ps]
   kb.append([InlineKeyboardButton(text="⬅️ Atrás",callback_data="po"),InlineKeyboardButton(text="🏠 Inicio",callback_data="inicio")])
   await up(q,"🗑️ **ELIMINAR**",InlineKeyboardMarkup(inline_keyboard=kb))
  elif dt.startswith("dp_"):
   pid=int(dt.split("_")[1])
   c=sqlite3.connect("r.db");x=c.cursor();x.execute("DELETE FROM p WHERE id=?",(pid,));c.commit();c.close()
   await q.answer("✅ Eliminado.",show_alert=True)
   await up(q,"✅ Producto eliminado.",InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 Inicio",callback_data="inicio")]]))
  elif dt=="os":await up(q,"💰 **DAR SALDO**\n\nUsa: `/darsaldo ID Monto`",InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Atrás",callback_data="po")],[InlineKeyboardButton(text="🏠 Inicio",callback_data="inicio")]]))
  elif dt=="oa_d":await up(q,"🛡️ **DAR ADMIN**\n\nUsa: `/daradmin ID`",InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Atrás",callback_data="po")],[InlineKeyboardButton(text="🏠 Inicio",callback_data="inicio")]]))
  elif dt=="ost":
   c=sqlite3.connect("r.db");x=c.cursor()
   x.execute("SELECT COUNT(*) FROM u");tu=x.fetchone()[0]
   x.execute("SELECT COUNT(*) FROM u WHERE prem=1");tp=x.fetchone()[0]
   x.execute("SELECT COUNT(*),SUM(precio) FROM c");v,ig=x.fetchone()
   c.close()
   await up(q,f"📊 **ESTADÍSTICAS**\n\n👥 Users: `{tu}`\n💎 Premium: `{tp}`\n📦 Ventas: `{v or 0}`\n💵 Ingresos: `${ig or 0:.2f}`",InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Atrás",callback_data="po")],[InlineKeyboardButton(text="🏠 Inicio",callback_data="inicio")]]))
  elif dt=="pa":
   if not ao(u):return
   await up(q,"⚙️ **PANEL ADMIN**",InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💰 Dar Saldo",callback_data="os")],[InlineKeyboardButton(text="🏠 Inicio",callback_data="inicio")]]))
 except Exception:pass
@d.message(F.text.startswith("/addprod"))
async def ap(m:Message):
 if m.from_user.id!=O:return
 try:
  _,cg,n,pr,st,ds=m.text.split(maxsplit=5)
  c=sqlite3.connect("r.db");x=c.cursor();x.execute("INSERT INTO p(cat,nombre,precio,stock,desc) VALUES(?,?,?,?,?)",(cg,n,float(pr),int(st),ds));c.commit();c.close()
  await m.reply(f"✅ Agregado: **{n}**",parse_mode="Markdown")
 except Exception:await m.reply("❌ Error. Uso: `/addprod Cat Nombre Precio Stock Desc`",parse_mode="Markdown")
@d.message(F.text.startswith("/darsaldo"))
async def ds(m:Message):
 if not ao(m.from_user.id):return
 try:
  _,tid,mnt=m.text.split();tid,mnt=int(tid),float(mnt)
  c=sqlite3.connect("r.db");x=c.cursor();x.execute("UPDATE u SET saldo=saldo+? WHERE user_id=?",(mnt,tid));c.commit();c.close()
  await m.reply(f"✅ Agregados `${mnt:.2f}` a `{tid}`.",parse_mode="Markdown")
 except Exception:await m.reply("❌ Uso: `/darsaldo ID Monto`",parse_mode="Markdown")
@d.message(F.text.startswith("/daradmin"))
async def da(m:Message):
 if m.from_user.id!=O:return
 try:
  tid=int(m.text.split()[1])
  c=sqlite3.connect("r.db");x=c.cursor();x.execute("INSERT OR IGNORE INTO a(user_id) VALUES(?)",(tid,));x.execute("UPDATE u SET rango='Administrador' WHERE user_id=?",(tid,));c.commit();c.close()
  await m.reply(f"✅ `{tid}` es Admin.",parse_mode="Markdown")
 except Exception:await m.reply("❌ Uso: `/daradmin ID`",parse_mode="Markdown")
if __name__=="__main__":
 import asyncio
 while True:
  try:asyncio.run(d.start_polling(b,skip_updates=True))
  except Exception:time.sleep(15)
    
