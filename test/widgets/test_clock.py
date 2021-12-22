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

# Widget specific tests

import datetime
import sys
from importlib import reload

import pytest

import libqtile.config
from libqtile.widget import clock
from test.widgets.conftest import FakeBar


def no_op(*args, **kwargs):
    pass


# Mock Datetime object that returns a set datetime and also
# has a simplified timezone method to check functionality of
# the widget.
class MockDatetime(datetime.datetime):
    @classmethod
    def now(cls, *args, **kwargs):
        return cls(2021, 1, 1, 10, 20, 30)

    def astimezone(self, tzone=None):
        if tzone is None:
            return self
        return self + datetime.timedelta(hours=tzone)


@pytest.fixture
def patched_clock(monkeypatch):
    # Stop system importing these modules in case they exist on environment
    monkeypatch.setitem(sys.modules, "pytz", None)
    monkeypatch.setitem(sys.modules, "dateutil", None)
    monkeypatch.setitem(sys.modules, "dateutil.tz", None)

    # Reload module to force ImportErrors
    reload(clock)

    # Override datetime.
    # This is key for testing as we can fix time.
    monkeypatch.setattr("libqtile.widget.clock.datetime", MockDatetime)


def test_clock(fake_qtile, monkeypatch, fake_window):
    """test clock output with default settings"""
    monkeypatch.setattr("libqtile.widget.clock.datetime", MockDatetime)
    clk1 = clock.Clock()
    fakebar = FakeBar([clk1], window=fake_window)
    clk1._configure(fake_qtile, fakebar)
    text = clk1.poll()
    assert text == "10:20"


@pytest.mark.usefixtures("patched_clock")
def test_clock_invalid_timezone(fake_qtile, monkeypatch, fake_window):
    """test clock widget with invalid timezone (and no pytz or dateutil modules)"""

    class FakeDateutilTZ:
        @classmethod
        def tz(cls):
            return cls

        @classmethod
        def gettz(cls, val):
            return None

    # pytz and dateutil must not be in the sys.modules dict...
    monkeypatch.delitem(sys.modules, "pytz")
    monkeypatch.delitem(sys.modules, "dateutil")

    # Set up references to pytz and dateutil so we know these aren't being used
    # If they're called, the widget would try to run None(self.timezone) which
    # would raise an exception
    clock.pytz = None
    clock.dateutil = FakeDateutilTZ

    # Fake datetime module just adds the timezone value to the time
    clk2 = clock.Clock(timezone="1")

    fakebar = FakeBar([clk2], window=fake_window)
    clk2._configure(fake_qtile, fakebar)

    # An invalid timezone current causes a TypeError
    with pytest.raises(TypeError):
        clk2.poll()


@pytest.mark.usefixtures("patched_clock")
def test_clock_datetime_timezone(fake_qtile, monkeypatch, fake_window):
    """test clock with datetime timezone"""

    class FakeDateutilTZ:
        class TZ:
            @classmethod
            def gettz(cls, val):
                None

        tz = TZ

    # Set up references to pytz and dateutil so we know these aren't being used
    # If they're called, the widget would try to run None(self.timezone) which
    # would raise an exception
    clock.pytz = None
    clock.dateutil = FakeDateutilTZ

    # Fake datetime module just adds the timezone value to the time
    clk3 = clock.Clock(timezone=1)

    fakebar = FakeBar([clk3], window=fake_window)
    clk3._configure(fake_qtile, fakebar)
    text = clk3.poll()

    # Default time is 10:20 and we add 1 hour for the timezone
    assert text == "11:20"


@pytest.mark.usefixtures("patched_clock")
def test_clock_pytz_timezone(fake_qtile, monkeypatch, fake_window):
    """test clock with pytz timezone"""

    class FakeDateutilTZ:
        class TZ:
            @classmethod
            def gettz(cls, val):
                None

        tz = TZ

    class FakePytz:
        # pytz timezone is a string so convert it to an int and add 1
        # to show that this code is being run
        @classmethod
        def timezone(cls, value):
            return int(value) + 1

    # We need pytz in the sys.modules dict
    monkeypatch.setitem(sys.modules, "pytz", True)

    # Set up references to pytz and dateutil so we know these aren't being used
    # If they're called, the widget would try to run None(self.timezone) which
    # would raise an exception
    clock.pytz = FakePytz
    clock.dateutil = FakeDateutilTZ

    # Pytz timezone must be a string
    clk4 = clock.Clock(timezone="1")

    fakebar = FakeBar([clk4], window=fake_window)
    clk4._configure(fake_qtile, fakebar)
    text = clk4.poll()

    # Default time is 10:20 and we add 1 hour for the timezone plus and extra
    # 1 for the pytz function
    assert text == "12:20"


@pytest.mark.usefixtures("patched_clock")
def test_clock_dateutil_timezone(fake_qtile, monkeypatch, fake_window):
    """test clock with dateutil timezone"""

    class FakeDateutilTZ:
        class TZ:
            @classmethod
            def gettz(cls, val):
                return int(val) + 2

        tz = TZ

    # pytz must not be in the sys.modules dict...
    monkeypatch.delitem(sys.modules, "pytz")

    # ...but dateutil must be
    monkeypatch.setitem(sys.modules, "dateutil", True)

    # Set up references to pytz and dateutil so we know these aren't being used
    # If they're called, the widget would try to run None(self.timezone) which
    # would raise an exception
    clock.pytz = None
    clock.dateutil = FakeDateutilTZ

    # Pytz timezone must be a string
    clk5 = clock.Clock(timezone="1")

    fakebar = FakeBar([clk5], window=fake_window)
    clk5._configure(fake_qtile, fakebar)
    text = clk5.poll()

    # Default time is 10:20 and we add 1 hour for the timezone plus and extra
    # 1 for the pytz function
    assert text == "13:20"


@pytest.mark.usefixtures("patched_clock")
def test_clock_tick(manager_nospawn, minimal_conf_noscreen, monkeypatch):
    """Test clock ticks"""

    class FakeDateutilTZ:
        class TZ:
            @classmethod
            def gettz(cls, val):
                return int(val) + 2

        tz = TZ

    class TickingDateTime(datetime.datetime):
        offset = 0

        @classmethod
        def now(cls, *args, **kwargs):
            return cls(2021, 1, 1, 10, 20, 30)

        # This will return 10:20 on first call and 10:21 on all
        # subsequent calls
        def astimezone(self, tzone=None):
            extra = datetime.timedelta(minutes=TickingDateTime.offset)
            if TickingDateTime.offset < 1:
                TickingDateTime.offset += 1

            if tzone is None:
                return self + extra
            return self + datetime.timedelta(hours=tzone) + extra

    # pytz must not be in the sys.modules dict...
    monkeypatch.delitem(sys.modules, "pytz")

    # ...but dateutil must be
    monkeypatch.setitem(sys.modules, "dateutil", True)

    # Override datetime
    monkeypatch.setattr("libqtile.widget.clock.datetime", TickingDateTime)

    # Set up references to pytz and dateutil so we know these aren't being used
    # If they're called, the widget would try to run None(self.timezone) which
    # would raise an exception
    clock.pytz = None
    clock.dateutil = FakeDateutilTZ

    # set a long update interval as we'll tick manually
    clk6 = clock.Clock(update_interval=100)

    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(top=libqtile.bar.Bar([clk6], 10))]

    manager_nospawn.start(config)

    topbar = manager_nospawn.c.bar["top"]
    manager_nospawn.c.widget["clock"].eval("self.tick()")
    assert topbar.info()["widgets"][0]["text"] == "10:21"
