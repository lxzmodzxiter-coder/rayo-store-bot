import os

os.environ.setdefault("BOT_TOKEN", "123456:TEST_TOKEN")
os.environ.setdefault("OWNER_ID", "999")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from inline import main_menu, payment_methods
from user import Base, UserRole


def test_role_menus_are_scoped():
    user_markup = main_menu(UserRole.USER)
    owner_markup = main_menu(UserRole.OWNER)
    user_callbacks = [button.callback_data for row in user_markup.inline_keyboard for button in row if button.callback_data]
    owner_callbacks = [button.callback_data for row in owner_markup.inline_keyboard for button in row if button.callback_data]
    assert "admin:home" not in user_callbacks
    assert "owner:home" not in user_callbacks
    assert "admin:home" in owner_callbacks
    assert "owner:home" in owner_callbacks


def test_payment_menu_hides_unconfigured_methods():
    markup = payment_methods(False, False)
    callbacks = [button.callback_data for row in markup.inline_keyboard for button in row if button.callback_data]
    assert callbacks == ["menu:home"]


def test_schema_contains_core_tables():
    expected = {"users", "products", "purchases", "topup_requests", "coupons", "coupon_redemptions", "balance_transactions", "audit_logs"}
    assert expected.issubset(Base.metadata.tables)
