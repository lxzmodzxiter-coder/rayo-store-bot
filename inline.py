from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from user import UserRole


def kb(rows):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t, callback_data=c) if c else InlineKeyboardButton(text=t, url=u) for t, c, u in row] for row in rows])


def main_menu(role: UserRole, channel_url: str = "") -> InlineKeyboardMarkup:
    rows = [
        [("🛍️ Catálogo", "menu:catalog", None), ("👤 Mi Perfil", "menu:profile", None)],
        [("📦 Mis Compras", "menu:purchases", None), ("💳 Recargar Saldo", "menu:balance", None)],
        [("🎟️ Cupones", "menu:coupons", None), ("💎 Premium", "menu:premium", None)],
        [("🎁 Referidos", "menu:referrals", None), ("📞 Soporte", "menu:support", None)],
    ]
    if channel_url:
        rows.append([("📢 Canal Oficial", None, channel_url)])
    if role in (UserRole.ADMIN, UserRole.OWNER):
        rows.append([("⚙️ Panel Admin", "admin:home", None)])
    if role == UserRole.OWNER:
        rows.append([("👑 Panel Owner", "owner:home", None)])
    return kb(rows)


def nav(home: bool = True, back: str = "menu:home") -> InlineKeyboardMarkup:
    rows = []
    if back:
        rows.append([("⬅️ Atrás", back, None)])
    if home:
        rows.append([("🏠 Inicio", "menu:home", None)])
    return kb(rows)


def categories(categories: list[str]) -> InlineKeyboardMarkup:
    rows = [[(f"{name}", f"cat:{name}", None)] for name in categories]
    rows.append([("🔎 Buscar producto", "product:search", None)])
    rows.extend([[ ("🏠 Inicio", "menu:home", None) ]])
    return kb(rows)


def product_list(items, page: int, pages: int, category: str) -> InlineKeyboardMarkup:
    rows = [[(f"📦 {p.name} · {p.price:.2f}", f"product:{p.id}", None)] for p in items]
    pager = []
    if page > 0:
        pager.append(("◀️ Anterior", f"products:{category}:{page-1}", None))
    if page + 1 < pages:
        pager.append(("▶️ Siguiente", f"products:{category}:{page+1}", None))
    if pager:
        rows.append(pager)
    rows.append([("⬅️ Categorías", "menu:catalog", None)])
    return kb(rows)


def product_detail(product_id: int, back: str) -> InlineKeyboardMarkup:
    return kb([
        [("🛒 Comprar", f"buy:{product_id}", None)],
        [("⬅️ Atrás", back, None), ("🏠 Inicio", "menu:home", None)],
    ])


def confirm(action: str, cancel: str = "menu:home") -> InlineKeyboardMarkup:
    return kb([[ ("✅ Confirmar", action, None), ("❌ Cancelar", cancel, None) ]])


def payment_methods(yape_enabled: bool = True, binance_enabled: bool = True) -> InlineKeyboardMarkup:
    rows = []
    if yape_enabled:
        rows.append([("🇵🇪 Yape / Plin", "topup:method:yape", None)])
    if binance_enabled:
        rows.append([("💰 Binance USDT", "topup:method:binance", None)])
    rows.append([("⬅️ Atrás", "menu:home", None)])
    return kb(rows)


def admin_home(owner: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [("👥 Usuarios", "admin:users", None), ("📦 Productos", "admin:products", None)],
        [("💳 Pagos", "admin:payments", None), ("📊 Estadísticas", "admin:stats", None)],
        [("📢 Difusión", "admin:broadcast", None), ("🎟️ Cupones", "admin:coupons", None)],
        [("💰 Créditos", "admin:credits", None), ("🚫 Seguridad", "admin:security", None)],
    ]
    if owner:
        rows.extend([
            [("⚙️ Administradores", "owner:admins", None), ("📜 Registros", "owner:logs", None)],
            [("🔧 Configuración", "owner:config", None)],
        ])
    rows.append([("🏠 Inicio", "menu:home", None)])
    return kb(rows)
