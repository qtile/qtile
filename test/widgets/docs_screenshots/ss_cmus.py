import pytest

from libqtile.widget.textbox import TextBox


@pytest.fixture
def widget():
    yield TextBox


@pytest.mark.parametrize("screenshot_manager", [{}], indirect=True)
def ss_cmus(screenshot_manager):
    screenshot_manager.c.widget["textbox"].update("♫ Rick Astley - Never Gonna Give You Up")
    screenshot_manager.take_screenshot()
