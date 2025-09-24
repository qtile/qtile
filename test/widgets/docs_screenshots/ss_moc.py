import pytest

from libqtile.widget.textbox import TextBox


@pytest.fixture
def widget():
    yield TextBox


def ss_moc(screenshot_manager):
    screenshot_manager.c.widget["textbox"].update("♫ Rick Astley - Never Gonna Give You Up")
    screenshot_manager.take_screenshot()
