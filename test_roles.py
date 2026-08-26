import asyncio

from aiogram.types import User as TelegramUser

from bot import (
    Base,
    UserRole,
    async_session_maker,
    cmd_ban,
    cmd_desban,
    cmd_rango,
    cmd_rol,
    engine,
    get_or_create_user,
    is_admin,
    is_owner,
    is_staff,
    settings,
)


class FakeMessage:
    def __init__(self, user, text):
        self.from_user = user
        self.text = text
        self.answers = []

    async def answer(self, text, **kwargs):
        self.answers.append((text, kwargs))


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_maker() as session:
        owner_tg = TelegramUser(id=settings.OWNER_ID, is_bot=False, first_name="Owner")
        owner = await get_or_create_user(owner_tg, session)
        assert owner.role == UserRole.DUENO
        assert is_owner(owner) and is_admin(owner) and is_staff(owner)

        user_tg = TelegramUser(id=999, is_bot=False, first_name="Normal")
        user = await get_or_create_user(user_tg, session)
        assert user.role == UserRole.USUARIO
        assert user.rank_title == "Cliente Nuevo"
        assert not is_owner(user) and not is_admin(user) and not is_staff(user)

        await cmd_rol(FakeMessage(owner_tg, "/rol 999 socio"), session, current_user=owner)
        await session.refresh(user)
        assert user.role == UserRole.SOCIO
        assert not is_staff(user) and not is_admin(user)

        await cmd_rango(FakeMessage(owner_tg, "/rango 999 Socio Elite"), session, current_user=owner)
        await session.refresh(user)
        assert user.rank_title == "Socio Elite"

        banned_message = FakeMessage(owner_tg, "/ban 999 prueba")
        await cmd_ban(banned_message, session, current_user=owner)
        await session.refresh(user)
        assert user.is_banned and user.ban_reason == "prueba"
        assert "Baneo permanente" in banned_message.answers[0][0]

        await cmd_desban(FakeMessage(owner_tg, "/desban 999"), session, current_user=owner)
        await session.refresh(user)
        assert not user.is_banned and user.ban_reason is None

        protected = FakeMessage(owner_tg, "/rol 123 admin")
        await cmd_rol(protected, session, current_user=owner)
        assert "protegido" in protected.answers[0][0]

    print("ROLES_OK")


if __name__ == "__main__":
    asyncio.run(main())

