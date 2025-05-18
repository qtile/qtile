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

import builtins
import sys
from importlib import reload
from types import ModuleType

import pytest

import libqtile.config
from libqtile.bar import Bar


def no_op(*args, **kwargs):
    pass


def mock_open(output):
    class MockOpen:
        def __init__(self, *args):
            self.output = output

        def __enter__(self):
            return self

        def __exit__(*exc):
            return None

        def read(self):
            return self.output

    return MockOpen


class MockIwlib(ModuleType):
    DATA = {
        "wlan0": {
            "NWID": b"Auto",
            "Frequency": b"5.18 GHz",
            "Access Point": b"12:34:56:78:90:AB",
            "BitRate": b"650 Mb/s",
            "ESSID": b"QtileNet",
            "Mode": b"Managed",
            "stats": {"quality": 49, "level": 190, "noise": 0, "updated": 75},
        },
        "wlan1": {
            "ESSID": None,
        },
    }

    @classmethod
    def get_iwconfig(cls, interface):
        return cls.DATA.get(interface, dict())


# Patch the widget with our mock iwlib module.
@pytest.fixture
def patched_wlan(monkeypatch):
    monkeypatch.setitem(sys.modules, "iwlib", MockIwlib("iwlib"))
    from libqtile.widget import wlan

    # Reload fixes cases where psutil may have been imported previously
    reload(wlan)

    yield wlan


@pytest.mark.parametrize(
    "kwargs,expected",
    [
        ({}, "QtileNet 49/70"),
        ({"format": "{essid} {percent:2.0%}"}, "QtileNet 70%"),
        ({"interface": "wlan1"}, "Disconnected"),
    ],
)
def test_wlan_display(minimal_conf_noscreen, manager_nospawn, patched_wlan, kwargs, expected):
    widget = patched_wlan.Wlan(**kwargs)
    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(top=Bar([widget], 10))]
    manager_nospawn.start(config)

    text = manager_nospawn.c.bar["top"].info()["widgets"][0]["text"]
    assert text == expected


def test_wlan_display_escape_essid(
    minimal_conf_noscreen, manager_nospawn, patched_wlan, monkeypatch
):
    """Test escaping of pango markup in ESSID"""
    monkeypatch.setitem(MockIwlib.DATA["wlan0"], "ESSID", b"A&B")
    widget = patched_wlan.Wlan(format="{essid}")
    assert widget.poll() == "A&amp;B"


@pytest.mark.parametrize(
    "kwargs,state,expected",
    [
        ({"interface": "wlan1", "use_ethernet": True}, "up", "eth"),
        ({"interface": "wlan1", "use_ethernet": True}, "down", "Disconnected"),
        (
            {"interface": "wlan1", "use_ethernet": True, "ethernet_message_format": "Wired"},
            "up",
            "Wired",
        ),
    ],
)
def test_ethernet(
    minimal_conf_noscreen, manager_nospawn, patched_wlan, kwargs, state, expected, monkeypatch
):
    monkeypatch.setattr(builtins, "open", mock_open(state))
    widget = patched_wlan.Wlan(**kwargs)
    assert widget.poll() == expected
