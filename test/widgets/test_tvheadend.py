from datetime import datetime

import pytest

from libqtile.backend.x11 import xcbq
from libqtile.bar import Bar
from libqtile.widget import TVHWidget
from libqtile.widget.tvheadend import TVHJobServer
from test.conftest import BareConfig

NOW = int(datetime.now().timestamp())
FIVE_MINS = 5 * 60
QUARTER_HOUR = 15 * 60


FUTURE_RECS = [
    {
        'channelname': 'BBC ONE HD',
        'creator': 'elParaguayo',
        'duplicate': 0,
        'errorcode': 0,
        'filename': '',
        'start': NOW + FIVE_MINS,
        'stop': NOW + QUARTER_HOUR,
        'disp_subtitle': 'Fake Recording #1',
        'disp_title': 'TVH Widget Test',
        'uuid': '1234567890abcde'
    }
]

LIVE_RECS = [
    {
        'channelname': 'BBC ONE HD',
        'creator': 'elParaguayo',
        'duplicate': 0,
        'errorcode': 0,
        'filename': '',
        'start': NOW - FIVE_MINS,
        'stop': NOW + QUARTER_HOUR,
        'disp_subtitle': 'Fake Recording #2',
        'disp_title': 'TVH Widget Test',
        'uuid': 'edcba09876543321'
    }
]


# Need some attributes to help place the widget's popup
class FakeScreen:
    width = 0
    height = 0
    top = None


# We need to disable the widget's timeout_add function
def fake_timeout_add(timeout, func):
    return None


# Create the widget
tvh = TVHWidget()

# Disable timeout_add
tvh.timeout_add = fake_timeout_add

# Create a bar with just our widget
bar = Bar([tvh], 24)

# Add a "screen" so we can access dimensions
bar.screen = FakeScreen()

# Set the bar height
bar.height = 24

# Create a config for qtile
tvhconfig = BareConfig

# Add our bar to that config
tvhconfig.screens[0].top = bar

# Create parameters for test
popup_config = pytest.mark.parametrize("manager", [tvhconfig], indirect=True)


@popup_config
def test_tvhwidget(manager):
    # Create manager connection
    manager.conn = xcbq.Connection(manager.display)
    manager.windows_map = {}

    # Configure the bar with relevant attributes
    tvh.qtile = manager
    tvh.bar = bar
    tvh.bar.screen.width = manager.c.screen.info()["width"]
    tvh.bar.screen.height = manager.c.screen.info()["height"]
    tvh.bar.screen.top = tvh.bar
    tvh.bar.width = tvh.bar.screen.width
    tvh.offsetx = 0

    # Need a job server to parse fake responses
    tvh_js = tvh_js = TVHJobServer()

    # Test 1: No live recordings
    tvh.data = [tvh_js._tidy_prog(prog) for prog in FUTURE_RECS]
    assert not tvh.is_recording

    # Test 2: Active recording
    tvh.data = [tvh_js._tidy_prog(prog) for prog in LIVE_RECS]
    assert tvh.is_recording

    # Test 3: Check popup is created
    tvh.toggle_info()
    assert tvh.popup is not None

    # Test 4: Check popup is not in windows list as it's unmanaged
    assert len(manager.c.windows()) == 0

    # Test 5: Check popup y value is under bar (as bar is top of screen)
    assert tvh.popup.y == 24

    # Test 6: Check popup has been resized
    assert ((tvh.popup.width < tvh.bar.screen.width) and
            (tvh.popup.height < tvh.bar.screen.height))

    # Test 7: Hide the popup and check it's gone
    tvh.toggle_info()
    assert tvh.popup is None
