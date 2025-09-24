import pytest

import libqtile.widget
from test.widgets.test_crypto_ticker import RESPONSE


@pytest.fixture
def widget():
    ticker = libqtile.widget.CryptoTicker
    ticker.RESPONSE = RESPONSE
    yield ticker


@pytest.mark.parametrize(
    "screenshot_manager", [{}, {"format": "{crypto}:{amount:,.2f}"}], indirect=True
)
def ss_crypto_ticker(screenshot_manager):
    screenshot_manager.c.widget["cryptoticker"].eval("self.update(self.parse(self.RESPONSE))")
    screenshot_manager.take_screenshot()
