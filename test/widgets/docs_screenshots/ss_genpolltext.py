import pytest

import libqtile.widget


@pytest.fixture
def widget():
    yield libqtile.widget.GenPollText


@pytest.mark.parametrize(
    "screenshot_manager",
    [
        {"func": lambda: "Function text."},
    ],
    indirect=True,
)
def ss_genpolltext(screenshot_manager):
    screenshot_manager.take_screenshot()
