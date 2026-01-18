import pytest

from libqtile.widget.textbox import TextBox


@pytest.fixture
def widget():
    return TextBox


@pytest.mark.parametrize(
    "screenshot_manager",
    [
        {},
    ],
    indirect=True,
)
def ss_caps_num_lock_indicator(screenshot_manager):
    screenshot_manager.c.widget["textbox"].update("Caps on Num on")
    screenshot_manager.take_screenshot()
