import asyncio

from aiogram.types import Chat
from aiogram.types import User as TelegramUser

from bot import (
    Base,
    UserRole,
    admin_balance_amount,
    async_session_maker,
    can_deliver_keys,
    can_manage_products,
    cmd_agregas,
    cmd_broadcast,
    cmd_saldo,
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
        self.chat = Chat(id=user.id, type="private")
        self.answers = []

    async def answer(self, text, **kwargs):
        self.answers.append(text)


class FakeState:
    def __init__(self):
        self.cleared = False
        self.states = []

    async def clear(self):
        self.cleared = True

    async def set_state(self, state):
        self.states.append(state)

    async def update_data(self, **kwargs):
        return None

    async def get_data(self):
        return {}


class FakeBot:
    async def send_message(self, *args, **kwargs):
        return None


async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_maker() as session:
        socio_tg = TelegramUser(id=200, is_bot=False, first_name="Socio")
        socio = await get_or_create_user(socio_tg, session)
        socio.role = UserRole.SOCIO

        usuario_tg = TelegramUser(id=250, is_bot=False, first_name="Usuario")
        usuario = await get_or_create_user(usuario_tg, session)
        usuario.role = UserRole.USUARIO

        admin_tg = TelegramUser(id=300, is_bot=False, first_name="Admin")
        admin = await get_or_create_user(admin_tg, session)
        admin.role = UserRole.ADMIN

        owner_tg = TelegramUser(id=settings.OWNER_ID, is_bot=False, first_name="Owner")
        owner = await get_or_create_user(owner_tg, session)
        assert owner.role == UserRole.DUENO
        await session.commit()

        assert not is_staff(socio) and not is_admin(socio) and not is_owner(socio)
        assert not is_staff(usuario) and not is_admin(usuario)
        assert is_admin(admin) and is_staff(admin)
        assert is_owner(owner) and can_manage_products(owner)
        assert can_manage_products(admin) and can_deliver_keys(admin)
        assert not can_manage_products(socio) and not can_deliver_keys(socio)

        bot = FakeBot()

        socio_saldo = FakeMessage(socio_tg, "/saldo 123 10 USD")
        await cmd_saldo(socio_saldo, bot, session, current_user=socio)
        assert "Permisos insuficientes" in socio_saldo.answers[0]

        socio_broadcast = FakeMessage(socio_tg, "/broadcast")
        await cmd_broadcast(socio_broadcast, FakeState(), session, current_user=socio)
        assert "Solo Administradores" in socio_broadcast.answers[0]

        admin_saldo = FakeMessage(admin_tg, "/saldo 999 10 USD")
        await cmd_saldo(admin_saldo, bot, session, current_user=admin)
        assert "Usuario no encontrado" in admin_saldo.answers[0]

        admin_agregas = FakeMessage(admin_tg, "/agregas")
        await cmd_agregas(admin_agregas, FakeState(), session, current_user=admin)
        assert "NUEVO PRODUCTO" in admin_agregas.answers[0]

        socio_balance = FakeMessage(socio_tg, "10")
        socio_state = FakeState()
        await admin_balance_amount(socio_balance, socio_state, session, current_user=socio)
        assert socio_state.cleared and not socio_balance.answers

    print("PERMISSIONS_OK")


if __name__ == "__main__":
    asyncio.run(main())

