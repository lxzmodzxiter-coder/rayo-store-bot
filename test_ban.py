import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from aiogram.types import Chat, Message
from aiogram.types import User as TelegramUser

from bot import (
    BANNED_MARKUP,
    BANNED_TEXT,
    AuthMiddleware,
    Base,
    UserRole,
    async_session_maker,
    engine,
    get_or_create_user,
)


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_maker() as session:
        tg_user = TelegramUser(id=777, is_bot=False, first_name="Banned")
        user = await get_or_create_user(tg_user, session)
        user.role = UserRole.USUARIO
        user.is_banned = True
        user.ban_reason = "prueba permanente"
        await session.commit()

        event = Message(
            message_id=1,
            date=datetime.now(timezone.utc),
            chat=Chat(id=777, type="private"),
            from_user=tg_user,
            text="/start",
        )
        handler = AsyncMock()
        middleware = AuthMiddleware()

        with patch.object(Message, "answer", new_callable=AsyncMock) as answer:
            await middleware(handler, event, {"session": session})

        handler.assert_not_awaited()
        answer.assert_awaited_once()
        text = answer.await_args.args[0]
        assert text == BANNED_TEXT
        markup = answer.await_args.kwargs["reply_markup"]
        assert markup == BANNED_MARKUP
        assert len(markup.inline_keyboard) == 1
        assert len(markup.inline_keyboard[0]) == 1
        button = markup.inline_keyboard[0][0]
        assert button.url == "https://t.me/Lxz_Modz"
        assert button.callback_data is None

    print("BAN_OK")


if __name__ == "__main__":
    asyncio.run(main())
