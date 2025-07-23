# Copyright (c) 2024 elParaguayo
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
from importlib import reload

import pytest

from libqtile.config import Bar, Screen
from libqtile.widget import vertical_clock
from test.helpers import BareConfig


# Mock Datetime object that returns a set datetime and also
# has a simplified timezone method to check functionality of
# the widget.
class MockDatetime(datetime.datetime):
    @classmethod
    def now(cls, *args, **kwargs):
        return cls(2024, 1, 1, 10, 20, 30)

    def astimezone(self, tzone=None):
        if tzone is None:
            return self
        return self + tzone.utcoffset(None)


@pytest.fixture
def patched_clock(monkeypatch):
    # Stop system importing these modules in case they exist on environment
    monkeypatch.setitem(sys.modules, "pytz", None)
    monkeypatch.setitem(sys.modules, "dateutil", None)
    monkeypatch.setitem(sys.modules, "dateutil.tz", None)

    # Reload module to force ImportErrors
    reload(vertical_clock)

    # Override datetime.
    # This is key for testing as we can fix time.
    monkeypatch.setattr("libqtile.widget.vertical_clock.datetime", MockDatetime)

    class TestVerticalClock(vertical_clock.VerticalClock):
        def __init__(self, **config):
            vertical_clock.VerticalClock.__init__(self, **config)
            self.name = "verticalclock"

        def info(self):
            info = vertical_clock.VerticalClock.info(self)
            info["text"] = "|".join(layout.text for layout in self.layouts)
            return info

    yield TestVerticalClock


@pytest.fixture(scope="function")
def vclock_manager(manager_nospawn, request, patched_clock):
    class VClockConfig(BareConfig):
        screens = [
            Screen(
                left=Bar(
                    [
                        patched_clock(
                            **getattr(request, "param", dict()),
                        )
                    ],
                    30,
                )
            )
        ]

    manager_nospawn.start(VClockConfig)

    yield manager_nospawn


def config(**kwargs):
    return pytest.mark.parametrize("vclock_manager", [kwargs], indirect=True)


def test_vclock_default(vclock_manager):
    assert vclock_manager.c.widget["verticalclock"].info()["text"] == "10|20"


@config(format=["%H", "%M", "-", "%d", "%m", "%Y"])
def test_vclock_extra_lines(vclock_manager):
    assert vclock_manager.c.widget["verticalclock"].info()["text"] == "10|20|-|01|01|2024"


@pytest.mark.parametrize(
    "vclock_manager",
    [
        dict(fontsize=[10]),  # too few
        dict(fontsize=[10, 20, 30, 40]),  # too many
        dict(fontsize=[10, "fff"]),  # mix values
        dict(foreground=["fff"]),  # too few
        dict(foreground=["fff"] * 4),  # too many
        dict(foreground=["fff", 10]),  # mix values
    ],
    indirect=True,
)
def test_vclock_invalid_configs(vclock_manager):
    assert vclock_manager.c.bar["left"].info()["widgets"][0]["name"] == "configerrorwidget"
