from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from session import async_session_maker  # Importa desde tu archivo session.py

class DatabaseMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Abre una conexión a PostgreSQL
        async with async_session_maker() as session:
            # Pone la sesión disponible para que el bot la use
            data["session"] = session
            
            # Pasa al siguiente paso (procesar el comando o botón)
            return await handler(event, data)
          
