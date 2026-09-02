import asyncio
import os
from decimal import Decimal
from unittest.mock import AsyncMock, patch

os.environ.setdefault("BOT_TOKEN", "123456:TEST_TOKEN")
os.environ.setdefault("OWNER_ID", "999")
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./holo_buy_flow_test.db"

from aiogram.types import User as TelegramUser
from sqlalchemy import select

import bot as app


class FakeMessage:
    def __init__(self):
        self.edits = []

    async def edit_text(self, text, **kwargs):
        self.edits.append(text)


class FakeCallback:
    def __init__(self, telegram_id, data):
        self.from_user = TelegramUser(id=telegram_id, is_bot=False, first_name="Cliente")
        self.data = data
        self.message = FakeMessage()
        self.answers = []

    async def answer(self, text=None, **kwargs):
        self.answers.append(text)


class FakeBot:
    def __init__(self):
        self.sent = []

    async def send_message(self, chat_id, text, **kwargs):
        self.sent.append((chat_id, text))


async def main():
    async with app.engine.begin() as connection:
        await connection.run_sync(app.Base.metadata.drop_all)
        await connection.run_sync(app.Base.metadata.create_all)

    async with app.async_session_maker() as session:
        customer = app.User(telegram_id=424242, first_name="Cliente", balance=Decimal("40.00"), role=app.UserRole.USUARIO)
        product = app.Product(name="PROYECTO HOLOGRAMA VIP", category="Android", description="", price=Decimal("0.00"), stock=2, is_active=True)
        session.add_all([customer, product])
        await session.flush()
        variant = app.ProductVariant(product_id=product.id, name="7 Días", price=Decimal("15.00"), stock=2)
        session.add(variant)
        await session.commit()
        await session.refresh(customer)

        callback = FakeCallback(424242, f"buyconfirm:{product.id}:7 Días")
        telegram = FakeBot()
        remote = AsyncMock(return_value={"key": "HOLOVIP-INTEGRATED", "duration": "7 Días", "delivery_text": "KEY ENTREGADA :\\n\\nKEY : HOLOVIP-INTEGRATED\\n\\nDURACIÓN: 7 Días\\n\\nGRACIAS POR TU COMPRA Y TU CONFIANZA"})
        with patch.object(app, "request_holo_vip_delivery", remote):
            await app.buy_confirm(callback, telegram, session, current_user=customer)

        purchase = await session.scalar(select(app.Purchase).where(app.Purchase.user_id == customer.id))
        delivery = await session.scalar(select(app.KeyDelivery).where(app.KeyDelivery.purchase_id == purchase.id))
        assert purchase is not None and purchase.product_name.endswith("(7 Días)")
        assert delivery is not None and delivery.key_value == "HOLOVIP-INTEGRATED" and delivery.duration == "7 Días"
        remote.assert_awaited_once_with(purchase.order_id, 424242, "7 Días")
        assert any(chat_id == 424242 and "HOLOVIP-INTEGRATED" in text for chat_id, text in telegram.sent)

        failing_callback = FakeCallback(424242, f"buyconfirm:{product.id}:7 Días")
        failing_bot = FakeBot()
        remote_failure = AsyncMock(side_effect=RuntimeError("web unavailable"))
        with patch.object(app, "request_holo_vip_delivery", remote_failure):
            await app.buy_confirm(failing_callback, failing_bot, session, current_user=customer)
        purchases = (await session.execute(select(app.Purchase).where(app.Purchase.user_id == customer.id))).scalars().all()
        assert len(purchases) == 2
        assert any("Entrega HOLO VIP pendiente" in text for text in failing_callback.message.edits)
        assert any("ENTREGA HOLO VIP PENDIENTE" in text for _, text in failing_bot.sent)

    await app.engine.dispose()
    os.remove("./holo_buy_flow_test.db")
    print("HOLO_BUY_FLOW_OK")


if __name__ == "__main__":
    asyncio.run(main())
