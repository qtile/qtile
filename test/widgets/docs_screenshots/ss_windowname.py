import pytest

from libqtile.widget import windowname


@pytest.fixture
def widget():
    yield windowname.WindowName


def ss_windowname(screenshot_manager):
    screenshot_manager.test_window("One")
    screenshot_manager.take_screenshot()

    screenshot_manager.c.window.toggle_maximize()
    screenshot_manager.take_screenshot()

    screenshot_manager.c.window.toggle_minimize()
    screenshot_manager.take_screenshot()

    screenshot_manager.c.window.toggle_minimize()
    screenshot_manager.c.window.toggle_floating()
    screenshot_manager.take_screenshot()
