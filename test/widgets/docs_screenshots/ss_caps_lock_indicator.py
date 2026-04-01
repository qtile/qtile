import pytest

from libqtile.widget.textbox import TextBox


@pytest.fixture
def widget():
    yield TextBox


@pytest.fixture
def widget_name():
    return "CapsNumLockIndicator"


@pytest.mark.parametrize(
    "screenshot_manager",
    [
        {},
    ],
    indirect=True,
)
def ss_caps_num_lock_indicator(screenshot_manager):
    screenshot_manager.widget.update("Caps on Num on")
    screenshot_manager.take_screenshot()
