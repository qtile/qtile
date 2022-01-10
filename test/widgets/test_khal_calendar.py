# Copyright (c) 2021 elParaguayo
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import datetime
import sys
from datetime import timedelta
from importlib import reload
from types import ModuleType

import pytest

from libqtile.bar import Bar
from libqtile.config import Screen

CAL_OUTPUT = (
    "Today, 2021-01-01\n"
    "10:00-11:00 Write Qtile tests\n"
    "\n"
    "Tomorrow, 2021-01-02\n"
    "12:00-16:00 Fix bugs\n"
    "\n"
)

ALL_DAY_OUTPUT = "Today, 2021-01-01\n" "Write Qtile tests\n"

NO_OUTPUT = "No events\n"

NOW = datetime.datetime(2021, 1, 1, 9, 0, 0)


class MockDateutilParser(ModuleType):
    @classmethod
    def parse(cls, str, **kwargs):
        return datetime.datetime.strptime(str, "%Y-%m-%d %H:%M")


class MockDateutil(ModuleType):
    parser = MockDateutilParser("parser")


class MockDatetime(datetime.datetime):
    _adjustment = timedelta(minutes=0)

    @classmethod
    def now(cls):
        return NOW + cls._adjustment


def mock_popen(popen_args, *args, **kwargs):
    class MockPopenObject:
        def __init__(self, output):
            self.output = output

        def communicate(self, *args, **kwargs):
            return self.output.encode("utf-8"), None

    if popen_args[-1] == "10d":
        output = NO_OUTPUT
    elif popen_args[-1] == "20d":
        output = ALL_DAY_OUTPUT
    else:
        output = CAL_OUTPUT

    return MockPopenObject(output)


@pytest.fixture
def khal_manager(monkeypatch, request, minimal_conf_noscreen, manager_nospawn):
    monkeypatch.delitem(sys.modules, "dateutil", raising=False)
    monkeypatch.delitem(sys.modules, "dateutil.parser", raising=False)
    monkeypatch.setitem(sys.modules, "dateutil", MockDateutil("dateutil"))
    monkeypatch.setitem(sys.modules, "dateutil.parser", MockDateutilParser("dateutil.parser"))

    import libqtile.widget.khal_calendar

    # Reload module to force ImportErrors
    reload(libqtile.widget.khal_calendar)

    # Handle customisation
    adjust, config = getattr(request, "param", (0, dict()))
    monkeypatch.setattr(MockDatetime, "_adjustment", timedelta(minutes=adjust))
    monkeypatch.setattr(datetime, "datetime", MockDatetime)
    monkeypatch.setattr("libqtile.widget.khal_calendar.subprocess.Popen", mock_popen)
    widget = libqtile.widget.khal_calendar.KhalCalendar(**config)

    config = minimal_conf_noscreen
    config.screens = [Screen(top=Bar([widget], 10))]
    manager_nospawn.start(config)

    yield manager_nospawn


def test_khal_calendar_next_event(khal_manager):
    widget = khal_manager.c.widget["khalcalendar"]
    info = widget.info()
    assert info["text"] == "Today 2021-01-01 10:00-11:00 Write Qtile tests"
    assert info["foreground"] == "FFFF33"


# Advance the clock by 50 and 70 mins to simulate upcoming and live events
@pytest.mark.parametrize("khal_manager", [(50, dict()), (70, dict())], indirect=True)
def test_khal_calendar_upcoming_and_live_event(khal_manager):
    """Check foreground colour changes when within reminder period."""
    widget = khal_manager.c.widget["khalcalendar"]
    info = widget.info()
    assert info["text"] == "Today 2021-01-01 10:00-11:00 Write Qtile tests"
    assert info["foreground"] == "FF0000"


# Code is patched to show no output if lookahead set to 10 days.
@pytest.mark.parametrize("khal_manager", [(0, {"lookahead": 10})], indirect=True)
def test_khal_calendar_no_events(khal_manager):
    """Check message when no events"""
    widget = khal_manager.c.widget["khalcalendar"]
    info = widget.info()
    assert info["text"] == "No appointments in next 10 days"


# Code is patched to show al day event if lookahead set to 20 days.
@pytest.mark.parametrize("khal_manager", [(0, {"lookahead": 20})], indirect=True)
def test_khal_calendar_all_day_event(khal_manager):
    """Check message when no events"""
    widget = khal_manager.c.widget["khalcalendar"]
    info = widget.info()
    assert info["text"] == "Today 2021-01-01 Write Qtile tests"
    assert info["foreground"] == "FF0000"
