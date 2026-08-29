import asyncio
from decimal import Decimal

from aiogram.types import Chat
from aiogram.types import User as TelegramUser

from bot import (
    TOPUP_COUNTRIES,
    Base,
    UserRole,
    admin_balance_amount,
    admin_home,
    async_session_maker,
    balance_display,
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
    main_menu,
    membership_discount_percent,
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

        premiun_tg = TelegramUser(id=350, is_bot=False, first_name="Premiun")
        premiun = await get_or_create_user(premiun_tg, session)
        premiun.role = UserRole.PREMIUN

        owner_tg = TelegramUser(id=settings.OWNER_ID, is_bot=False, first_name="Owner")
        owner = await get_or_create_user(owner_tg, session)
        assert owner.role == UserRole.DUENO
        await session.commit()

        assert not is_staff(socio) and not is_admin(socio) and not is_owner(socio)
        assert not is_staff(usuario) and not is_admin(usuario)
        assert is_admin(admin) and is_staff(admin)
        assert is_owner(owner) and can_manage_products(owner)
        assert not can_manage_products(admin) and not can_deliver_keys(admin)
        assert not can_manage_products(socio) and not can_deliver_keys(socio)
        assert membership_discount_percent(socio) == Decimal("20.00")
        assert membership_discount_percent(premiun) == Decimal("10.00")
        assert membership_discount_percent(admin) == Decimal("0.00")
        assert "saldo infinito" in balance_display(owner)

        def callbacks(markup):
            return {button.callback_data for row in markup.inline_keyboard for button in row if button.callback_data}

        assert "owner:home" in callbacks(main_menu(UserRole.DUENO))
        assert "admin:home" not in callbacks(main_menu(UserRole.DUENO))
        assert "owner:home" in callbacks(main_menu(UserRole.OWNER))
        assert "admin:home" not in callbacks(main_menu(UserRole.OWNER))
        assert "admin:home" in callbacks(main_menu(UserRole.ADMIN))
        assert "owner:home" not in callbacks(main_menu(UserRole.ADMIN))
        admin_panel = callbacks(admin_home(UserRole.ADMIN))
        owner_panel = callbacks(admin_home(UserRole.OWNER))
        dueno_panel = callbacks(admin_home(UserRole.DUENO))
        assert admin_panel == {"admin:payments", "admin:stats", "menu:home"}
        assert "owner:admins" not in owner_panel and "owner:admins" in dueno_panel
        assert len(owner_panel) < len(dueno_panel)
        assert [code for code, _ in TOPUP_COUNTRIES] == ["ar", "bo", "br", "cl", "co", "cr", "ec", "sv", "es", "us", "gt", "hn", "mx", "ni", "pa", "py", "pe", "do", "uy", "ve"]

        bot = FakeBot()

        socio_saldo = FakeMessage(socio_tg, "/saldo 123 10 USD")
        await cmd_saldo(socio_saldo, bot, session, current_user=socio)
        assert "Permisos insuficientes" in socio_saldo.answers[0]

        socio_broadcast = FakeMessage(socio_tg, "/broadcast")
        await cmd_broadcast(socio_broadcast, FakeState(), session, current_user=socio)
        assert "Solo OWNER" in socio_broadcast.answers[0]

        admin_saldo = FakeMessage(admin_tg, "/saldo 999 10 USD")
        await cmd_saldo(admin_saldo, bot, session, current_user=admin)
        assert "Permisos insuficientes" in admin_saldo.answers[0]

        admin_agregas = FakeMessage(admin_tg, "/agregas")
        await cmd_agregas(admin_agregas, FakeState(), session, current_user=admin)
        assert "Solo OWNER" in admin_agregas.answers[0]

        socio_balance = FakeMessage(socio_tg, "10")
        socio_state = FakeState()
        await admin_balance_amount(socio_balance, socio_state, session, current_user=socio)
        assert socio_state.cleared and not socio_balance.answers

    print("PERMISSIONS_OK")


if __name__ == "__main__":
    asyncio.run(main())

