from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from user import User


class AuthMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]], event: TelegramObject, data: dict[str, Any]) -> Any:
        session: AsyncSession | None = data.get("session")
        if session is None or not isinstance(event, (Message, CallbackQuery)) or not event.from_user:
            return await handler(event, data)
        user = (await session.execute(select(User).where(User.telegram_id == event.from_user.id))).scalar_one_or_none()
        if user and user.is_banned:
            if isinstance(event, CallbackQuery):
                await event.answer("🚫 Acceso restringido.", show_alert=True)
            else:
                await event.answer("🚫 <b>ACCESO RESTRINGIDO</b>\n\nTu acceso a LXZ STORE BEST se encuentra limitado.")
            return
        data["current_user"] = user
        return await handler(event, data)
