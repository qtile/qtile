import pytest

from libqtile.widget.textbox import TextBox


@pytest.fixture
def widget():
    yield TextBox


@pytest.fixture
def widget_name():
    return "StockTicker"


@pytest.mark.parametrize("screenshot_manager", [{}], indirect=True)
def ss_stock_ticker(screenshot_manager):
    screenshot_manager.widget.update("QTIL: $140.98")
    screenshot_manager.take_screenshot()
