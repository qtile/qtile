from datetime import datetime, timedelta

import pytest

import libqtile.widget

td = timedelta(days=1, hours=2, minutes=34, seconds=56)


@pytest.fixture
def widget():
    yield libqtile.widget.Countdown


@pytest.mark.parametrize("screenshot_manager", [{"date": datetime.now() + td}], indirect=True)
def ss_countdown(screenshot_manager):
    screenshot_manager.take_screenshot()
