from datetime import datetime, timezone
from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from user import User, UserRole
from config import settings
from inline import get_main_menu_keyboard

# Creamos un "Router", que es como un mapa para organizar comandos
router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, current_user: User | None = None):
    telegram_user = message.from_user
    if not telegram_user:
        return

    # current_user viene de nuestro AuthMiddleware (si el usuario ya existía y no está baneado)
    user = current_user

    # Si es la primera vez que entra al bot:
    if not user:
        # 1. Sistema de referidos (ejemplo: /start ref_12345)
        args = message.text.split()
        referred_by = None
        if len(args) > 1 and args[1].startswith("ref_"):
            try:
                ref_id = int(args[1].replace("ref_", ""))
                if ref_id != telegram_user.id:  # Evita auto-referidos
                    referred_by = ref_id
            except ValueError:
                pass

        # 2. Asignamos el rol Owner si el ID coincide con el tuyo
        role = UserRole.OWNER if telegram_user.id == settings.OWNER_ID else UserRole.USER
        
        # 3. Creamos el usuario en la base de datos
        user = User(
            telegram_id=telegram_user.id,
            username=telegram_user.username,
            first_name=telegram_user.first_name,
            last_name=telegram_user.last_name,
            role=role,
            referred_by=referred_by
        )
        session.add(user)
        
        # 4. Si fue invitado, le sumamos 1 a la cuenta de referidos del invitador
        if referred_by:
            ref_user_res = await session.execute(select(User).where(User.telegram_id == referred_by))
            ref_user = ref_user_res.scalar_one_or_none()
            if ref_user:
                ref_user.referrals_count += 1

        await session.commit()
    
    # Si el usuario ya existía, solo actualizamos sus datos y última conexión
    else:
        user.username = telegram_user.username
        user.first_name = telegram_user.first_name
        user.last_name = telegram_user.last_name
        user.last_activity = datetime.now(timezone.utc)
        await session.commit()

    # Mensaje de bienvenida
    welcome_text = (
        f"⚡ <b>Bienvenido a {settings.STORE_NAME}</b>\n\n"
        "La tienda digital profesional más rápida, segura y avanzada.\n"
        "Selecciona una opción del menú para continuar:"
    )

    # Enviamos el mensaje con el teclado (botones)
    await message.answer(
        welcome_text,
        reply_markup=get_main_menu_keyboard(user.role)
    )

# Comando público /cancelar
@router.message(Command("cancelar"))
async def cmd_cancel(message: Message):
    await message.answer("❌ Operación cancelada correctamente.")
              
