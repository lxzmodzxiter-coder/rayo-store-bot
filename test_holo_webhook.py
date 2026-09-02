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


if __name__ == "__main__":
    asyncio.run(run())
    print("HOLO_WEBHOOK_CLIENT_OK")
