import pytest

import libqtile.widget


@pytest.fixture
def widget():
    yield libqtile.widget.CurrentScreen


def ss_currentscreen(screenshot_manager):
    # First screenshot is active screen
    screenshot_manager.take_screenshot()

    # Change focus to second screen
    screenshot_manager.c.to_screen(1)

    # Widget now shows it's on an inactive screen
    screenshot_manager.take_screenshot()
