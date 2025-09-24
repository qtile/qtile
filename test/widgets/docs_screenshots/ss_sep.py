import pytest

from libqtile.widget import Sep


@pytest.fixture
def widget():
    yield Sep


@pytest.mark.parametrize(
    "screenshot_manager", [{}, {"padding": 10, "linewidth": 5, "size_percent": 50}], indirect=True
)
def ss_sep(screenshot_manager):
    screenshot_manager.take_screenshot()
