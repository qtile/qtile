from libqtile import widget
from test.widgets.conftest import FakeBar

RESPONSE = {"data": {"base": "BTC", "currency": "GBP", "amount": "29625.02"}}


def test_set_defaults():
    crypto = widget.CryptoTicker(currency="", symbol="")
    assert crypto.currency == "USD"
    assert crypto.symbol == "$"


def test_parse(fake_qtile, fake_window):
    crypto = widget.CryptoTicker(currency="GBP", symbol="£", crypto="BTC")
    fake_bar = FakeBar([crypto], window=fake_window)
    crypto._configure(fake_qtile, fake_bar)
    assert crypto.url == "https://api.coinbase.com/v2/prices/BTC-GBP/spot"
    assert crypto.parse(RESPONSE) == "BTC: £29625.02"
