import pytest

from libqtile.widget.textbox import TextBox


@pytest.fixture
def widget():
    yield TextBox


def ss_genpollurl(screenshot_manager):
    screenshot_manager.c.widget["textbox"].update("Text from URL")
    screenshot_manager.take_screenshot()
