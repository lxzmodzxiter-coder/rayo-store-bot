from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from user import UserRole

def get_main_menu_keyboard(role: UserRole) -> InlineKeyboardMarkup:
    # Botones públicos (para todos)
    buttons = [
        [InlineKeyboardButton(text="🛍️ Catálogo", callback_data="menu_catalog"),
         InlineKeyboardButton(text="👤 Mi Perfil", callback_data="menu_profile")],
        [InlineKeyboardButton(text="📦 Mis Compras", callback_data="menu_purchases"),
         InlineKeyboardButton(text="💳 Recargar Saldo", callback_data="menu_balance")],
        [InlineKeyboardButton(text="🎟️ Cupones", callback_data="menu_coupons"),
         InlineKeyboardButton(text="💎 Premium", callback_data="menu_premium")],
        [InlineKeyboardButton(text="🎁 Referidos", callback_data="menu_referrals"),
         InlineKeyboardButton(text="📞 Soporte", callback_data="menu_support")],
        [InlineKeyboardButton(text="📢 Canal Oficial", url="https://t.me/lxzstorechannel")] # Reemplaza en Railway
    ]

    # Botones exclusivos para Admins y Owner
    if role in (UserRole.ADMIN, UserRole.OWNER):
        buttons.append([InlineKeyboardButton(text="⚙️ Panel Admin", callback_data="menu_admin")])

    # Botón exclusivo solo para el Owner
    if role == UserRole.OWNER:
        buttons.append([InlineKeyboardButton(text="👑 Panel Owner", callback_data="menu_owner")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_back_keyboard() -> InlineKeyboardMarkup:
    # Botón global para regresar
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Atrás", callback_data="nav_back"),
             InlineKeyboardButton(text="🏠 Inicio", callback_data="nav_home")]
        ]
)
  
