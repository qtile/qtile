import pytest

from libqtile.widget import Clock


@pytest.fixture
def widget():
    yield Clock


@pytest.mark.parametrize("screenshot_manager", [{}, {"format": "%d/%m/%y %H:%M"}], indirect=True)
def ss_clock(screenshot_manager):
    screenshot_manager.take_screenshot()
