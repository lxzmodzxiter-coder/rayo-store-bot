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
        seller_tg = TelegramUser(id=200, is_bot=False, first_name="Seller")
        seller = await get_or_create_user(seller_tg, session)
        seller.role = UserRole.SELLER

        support_tg = TelegramUser(id=250, is_bot=False, first_name="Support")
        support = await get_or_create_user(support_tg, session)
        support.role = UserRole.SUPPORT

        admin_tg = TelegramUser(id=300, is_bot=False, first_name="Admin")
        admin = await get_or_create_user(admin_tg, session)
        admin.role = UserRole.ADMIN

        owner_tg = TelegramUser(id=123, is_bot=False, first_name="Owner")
        owner = await get_or_create_user(owner_tg, session)
        owner.role = UserRole.OWNER
        await session.commit()

        assert is_staff(seller) and not is_admin(seller) and not is_owner(seller)
        assert is_staff(support) and not is_admin(support)
        assert is_admin(admin) and is_staff(admin)
        assert is_owner(owner) and can_manage_products(owner)
        assert can_manage_products(seller) and can_deliver_keys(seller)
        assert not can_manage_products(support) and not can_deliver_keys(support)

        bot = FakeBot()

        seller_saldo = FakeMessage(seller_tg, "/saldo 123 10 USD")
        await cmd_saldo(seller_saldo, bot, session, current_user=seller)
        assert "Permisos insuficientes" in seller_saldo.answers[0]

        support_broadcast = FakeMessage(support_tg, "/broadcast")
        await cmd_broadcast(support_broadcast, FakeState(), session, current_user=support)
        assert "Solo Administradores" in support_broadcast.answers[0]

        seller_broadcast = FakeMessage(seller_tg, "/broadcast")
        await cmd_broadcast(seller_broadcast, FakeState(), session, current_user=seller)
        assert "Solo Administradores" in seller_broadcast.answers[0]

        admin_saldo = FakeMessage(admin_tg, "/saldo 999 10 USD")
        await cmd_saldo(admin_saldo, bot, session, current_user=admin)
        assert "Usuario no encontrado" in admin_saldo.answers[0]

        seller_agregas = FakeMessage(seller_tg, "/agregas")
        await cmd_agregas(seller_agregas, FakeState(), session, current_user=seller)
        assert "NUEVO PRODUCTO" in seller_agregas.answers[0]

        support_balance = FakeMessage(support_tg, "10")
        support_state = FakeState()
        await admin_balance_amount(support_balance, support_state, session, current_user=support)
        assert support_state.cleared and not support_balance.answers

    print("PERMISSIONS_OK")


if __name__ == "__main__":
    asyncio.run(main())

