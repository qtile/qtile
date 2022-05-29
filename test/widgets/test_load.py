# Copyright (c) 2022 elParaguayo
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
import sys
from importlib import reload
from types import ModuleType

import pytest

import libqtile.config
import libqtile.widget
from libqtile.bar import Bar


class MockPsutil(ModuleType):
    @classmethod
    def getloadavg(cls):
        return (0.73046875, 0.77587890625, 0.9521484375)


@pytest.fixture
def load_manager(monkeypatch, manager_nospawn, minimal_conf_noscreen, request):
    widget_config = getattr(request, "param", dict())

    monkeypatch.setitem(sys.modules, "psutil", MockPsutil("psutil"))
    from libqtile.widget import load

    reload(load)
    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(top=Bar([load.Load(**widget_config)], 10))]

    manager_nospawn.start(config)
    yield manager_nospawn


def test_load_times_button_click(load_manager):
    """Test cycling of loads via button press"""
    widget = load_manager.c.widget["load"]
    assert widget.info()["text"] == "Load(1m):0.73"

    load_manager.c.bar["top"].fake_button_press(0, "top", 0, 0, button=1)
    assert widget.info()["text"] == "Load(5m):0.78"

    load_manager.c.bar["top"].fake_button_press(0, "top", 0, 0, button=1)
    assert widget.info()["text"] == "Load(15m):0.95"

    load_manager.c.bar["top"].fake_button_press(0, "top", 0, 0, button=1)
    assert widget.info()["text"] == "Load(1m):0.73"


def test_load_times_command(load_manager):
    """Test cycling of loads via exposed command"""
    widget = load_manager.c.widget["load"]
    assert widget.info()["text"] == "Load(1m):0.73"

    widget.next_load()
    assert widget.info()["text"] == "Load(5m):0.78"

    widget.next_load()
    assert widget.info()["text"] == "Load(15m):0.95"

    widget.next_load()
    assert widget.info()["text"] == "Load(1m):0.73"


@pytest.mark.parametrize("load_manager", [{"format": "{time}: {load:.1f}"}], indirect=True)
def test_load_times_formatting(load_manager):
    """Test formatting of load times"""
    widget = load_manager.c.widget["load"]
    assert widget.info()["text"] == "1m: 0.7"

    widget.next_load()
    assert widget.info()["text"] == "5m: 0.8"

    widget.next_load()
    assert widget.info()["text"] == "15m: 1.0"

    widget.next_load()
    assert widget.info()["text"] == "1m: 0.7"
