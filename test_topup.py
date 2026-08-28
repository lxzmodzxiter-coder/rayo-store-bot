from decimal import Decimal

from bot import TOPUP_COUNTRIES, topup_amounts


def button_texts(markup):
    return [button.text for row in markup.inline_keyboard for button in row]


first_topup_texts = button_texts(topup_amounts("USD", Decimal(1), first_topup=True))
subsequent_topup_texts = button_texts(topup_amounts("USD", Decimal(1), first_topup=False))

assert "💵 5.00 USD" not in first_topup_texts
assert "💵 10.00 USD" in first_topup_texts
assert "💵 5.00 USD" in subsequent_topup_texts
assert "💵 100.00 USD" in subsequent_topup_texts
assert [code for code, _ in TOPUP_COUNTRIES] == ["pe", "co", "ar", "ve"]

print("TOPUP_OK")

