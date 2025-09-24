import pytest

from libqtile.widget import VerticalClock
from test.widgets.docs_screenshots.conftest import vertical_bar, widget_config


@pytest.fixture
def widget():
    yield VerticalClock


@vertical_bar
@widget_config(
    [{}, dict(format=["%H", "%M", "", "%d", "%m", "%y"], fontsize=[12, 12, 10, 10, 10, 10])]
)
def ss_clock(screenshot_manager):
    screenshot_manager.take_screenshot()
