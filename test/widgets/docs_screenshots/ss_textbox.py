from functools import partial

import pytest

from libqtile.widget import TextBox


@pytest.fixture
def widget():
    yield partial(TextBox, "Testing Text Box")


@pytest.mark.parametrize("screenshot_manager", [{}, {"foreground": "2980b9"}], indirect=True)
def ss_text(screenshot_manager):
    screenshot_manager.take_screenshot()
