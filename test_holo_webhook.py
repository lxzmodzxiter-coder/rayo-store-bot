import asyncio
import os
from unittest.mock import patch

os.environ.setdefault("BOT_TOKEN", "123456:TEST_TOKEN")
os.environ.setdefault("OWNER_ID", "999")
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./holo_webhook_test.db"

import bot as app


class FakeResponse:
    status = 201

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None

    async def json(self, content_type=None):
        return {"success": True, "key": "HOLOVIP-TEST-123", "duration": "7 Días", "deliveryText": "KEY ENTREGADA :\\n\\nKEY : HOLOVIP-TEST-123\\n\\nDURACIÓN: 7 Días\\n\\nGRACIAS POR TU COMPRA Y TU CONFIANZA"}


class FakeSession:
    def __init__(self, *args, **kwargs):
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        assert kwargs["json"] == {"requestId": "LXZ-ORDER-123", "product": "HOLO VIP", "duration": "7 Días", "buyerId": "123456789", "deviceLimit": 1}
        assert kwargs["headers"]["x-holo-webhook-secret"] == "test-secret"
        return FakeResponse()


async def run():
    app.settings.HOLO_WEBHOOK_URL = "https://ezteamweb-qyebjgnv.manus.space/api/webhooks/holo-vip/purchase-confirmed"
    app.settings.HOLO_WEBHOOK_SECRET = "test-secret"
    with patch.object(app.aiohttp, "ClientSession", FakeSession):
        result = await app.request_holo_vip_delivery("LXZ-ORDER-123", 123456789, "7 Días")
    assert result["key"] == "HOLOVIP-TEST-123"
    assert result["duration"] == "7 Días"
    assert "KEY ENTREGADA" in result["delivery_text"]


class DeliveryBot:
    def __init__(self, fail_first=False):
        self.sent = []
        self.fail_first = fail_first

    async def send_message(self, chat_id, text, **kwargs):
        if self.fail_first:
            self.fail_first = False
            raise RuntimeError("telegram unavailable")
        self.sent.append((chat_id, text))


async def delivery_checks():
    success_bot = DeliveryBot()
    assert await app.deliver_holo_vip_to_buyer(success_bot, 123456789, "KEY ENTREGADA", "LXZ-ORDER-123")
    assert success_bot.sent[0][0] == 123456789
    failed_bot = DeliveryBot(fail_first=True)
    assert not await app.deliver_holo_vip_to_buyer(failed_bot, 123456789, "KEY ENTREGADA", "LXZ-ORDER-124")
    assert len(failed_bot.sent) == 1


_original_run = run


async def run_all():
    await _original_run()
    await delivery_checks()


if __name__ == "__main__":
    asyncio.run(run_all())
    print("HOLO_WEBHOOK_CLIENT_OK")
