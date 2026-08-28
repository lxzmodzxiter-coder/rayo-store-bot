import asyncio
from decimal import Decimal

from aiogram.types import User as TelegramUser
from sqlalchemy import select

from bot import (
    Base,
    KeyDelivery,
    Product,
    Purchase,
    PurchaseStatus,
    UserRole,
    async_session_maker,
    cmd_key,
    engine,
    get_or_create_user,
)


class FakeMessage:
    def __init__(self, user, text):
        self.from_user = user
        self.text = text
        self.answers = []

    async def answer(self, text, **kwargs):
        self.answers.append(text)


class FakeBot:
    def __init__(self):
        self.sent = []

    async def send_message(self, chat_id, text, **kwargs):
        self.sent.append((chat_id, text))


async def main():
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

    async with async_session_maker() as session:
        seller_tg = TelegramUser(id=200, is_bot=False, first_name="Seller")
        seller = await get_or_create_user(seller_tg, session)
        seller.role = UserRole.OWNER
        customer_tg = TelegramUser(id=999, is_bot=False, first_name="Customer")
        customer = await get_or_create_user(customer_tg, session)
        product = Product(name="HG CHEATS", category="Android", description="7 Días | 7", price=Decimal("7.00"), stock=1, is_active=True)
        session.add(product)
        await session.flush()
        purchase = Purchase(order_id="TEST-KEY-1", user_id=customer.id, product_id=product.id, product_name="HG CHEATS (7 Días)", quantity=1, price=Decimal("7.00"), status=PurchaseStatus.PAID)
        session.add(purchase)
        await session.commit()

        bot = FakeBot()
        first = FakeMessage(seller_tg, "/key 999 KEY-ABC")
        await cmd_key(first, bot, session, current_user=seller)
        assert "KEY ENTREGADA" in first.answers[0]
        assert "7 Días" in first.answers[0]
        assert len(bot.sent) == 1 and "7 Días" in bot.sent[0][1]
        assert await session.scalar(select(KeyDelivery).where(KeyDelivery.purchase_id == purchase.id))

        second = FakeMessage(seller_tg, "/key 999 KEY-SECOND")
        await cmd_key(second, bot, session, current_user=seller)
        assert "ya tiene una Key entregada" in second.answers[0]

    print("FULFILLMENT_OK")


if __name__ == "__main__":
    asyncio.run(main())

