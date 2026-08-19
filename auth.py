from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from sqlalchemy import select

from user import User  # Importamos el modelo de usuario que creaste antes

class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Obtenemos la sesión de la base de datos que nos pasó database.py
        session = data.get("session")
        
        # Verificamos si el evento viene de un usuario real
        if isinstance(event, (Message, CallbackQuery)) and event.from_user:
            telegram_user = event.from_user
            
            # Buscamos al usuario en la base de datos
            result = await session.execute(select(User).where(User.telegram_id == telegram_user.id))
            user_obj = result.scalar_one_or_none()

            # Sistema de seguridad: Bloquear si está baneado
            if user_obj and user_obj.is_banned:
                if isinstance(event, Message):
                    await event.answer("🚫 ACCESO RESTRINGIDO\n\nTu acceso a LXZ STORE BEST se encuentra limitado.")
                elif isinstance(event, CallbackQuery):
                    await event.answer("🚫 Acceso restringido.", show_alert=True)
                return # Detiene la ejecución aquí mismo

            # Guardamos el usuario para que el resto del bot lo pueda usar
            data["current_user"] = user_obj

        return await handler(event, data)
      
