import pytest

from libqtile.widget import Spacer


@pytest.fixture
def widget():
    yield Spacer


@pytest.mark.parametrize(
    "screenshot_manager",
    [
        {},
        {"length": 50},
    ],
    indirect=True,
)
def ss_spacer(screenshot_manager):
    screenshot_manager.take_screenshot()
