import asyncio
import os
from decimal import Decimal

from aiogram.types import User as TelegramUser

os.environ.setdefault("BOT_TOKEN", "test-token")
os.environ.setdefault("OWNER_ID", "123")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_benefits.db")

from bot import (
    Base,
    UserRole,
    async_session_maker,
    engine,
    get_or_create_user,
    partner_confirm,
    premium_confirm,
)


class FakeMessage:
    async def edit_text(self, text, **kwargs):
        self.text = text


class FakeCallback:
    def __init__(self, user):
        self.from_user = user
        self.message = FakeMessage()
        self.answers = []

    async def answer(self, text="", **kwargs):
        self.answers.append(text)


async def main():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

        async with async_session_maker() as session:
            owner_tg = TelegramUser(id=123, is_bot=False, first_name="Owner")
            owner = await get_or_create_user(owner_tg, session)
            owner.balance = Decimal("0.00")
            await session.commit()

            socio_callback = FakeCallback(owner_tg)
            await partner_confirm(socio_callback, session, current_user=owner)
            assert owner.is_partner is True
            assert owner.role == UserRole.DUENO
            assert owner.balance == Decimal("0.00")
            assert "SOCIO OFICIAL ACTIVADO" in socio_callback.message.text
            assert "saldo infinito" in socio_callback.message.text

            premium_callback = FakeCallback(owner_tg)
            await premium_confirm(premium_callback, session, current_user=owner)
            assert owner.is_premium is True
            assert owner.role == UserRole.DUENO
            assert owner.balance == Decimal("0.00")
            assert "PREMIUN ACTIVADO" in premium_callback.message.text
            assert "saldo infinito" in premium_callback.message.text
    finally:
        try:
            os.remove("test_benefits.db")
        except FileNotFoundError:
            pass
        await engine.dispose()

    print("BENEFITS_OK")


if __name__ == "__main__":
    asyncio.run(main())

