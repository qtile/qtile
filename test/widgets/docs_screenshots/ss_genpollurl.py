import pytest

from libqtile.widget.textbox import TextBox


@pytest.fixture
def widget():
    yield TextBox


@pytest.fixture
def widget_name():
    return "GenPollUrl"


def ss_genpollurl(screenshot_manager):
    screenshot_manager.widget.update("Text from URL")
    screenshot_manager.take_screenshot()
