import pytest

from libqtile.widget.textbox import TextBox


@pytest.fixture
def widget():
    yield TextBox


@pytest.mark.parametrize("screenshot_manager", [{}], indirect=True)
def ss_wttr(screenshot_manager):
    screenshot_manager.c.widget["textbox"].update("Home: +17°C")
    screenshot_manager.take_screenshot()
