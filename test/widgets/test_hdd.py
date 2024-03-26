# Copyright (c) 2024 Florian G. Hechler

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Widget specific tests

import sys
import tempfile
from importlib import reload
from types import ModuleType

import pytest

import libqtile.config
import libqtile.widget
from libqtile.bar import Bar


class MockPsutil(ModuleType):
    pass


# Set ticks of fake stat file
def set_io_ticks(temp_file, io_ticks):
    temp_file.truncate(0)
    temp_file.write(
        f"13850 7547 1201386 14536 12612 60213 1838656 73847 0 {io_ticks} 112672 0 0 0 0 2116 24287"
    )
    temp_file.flush()


@pytest.fixture
def hdd_manager(monkeypatch, manager_nospawn, minimal_conf_noscreen):
    monkeypatch.setitem(sys.modules, "psutil", MockPsutil("psutil"))
    from libqtile.widget import hdd

    reload(hdd)

    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(top=Bar([hdd.HDD()], 10))]

    manager_nospawn.start(config)
    yield manager_nospawn


def test_hdd(hdd_manager):
    # Create a fake stat file
    fake_stat_file = tempfile.NamedTemporaryFile(mode="w+", delete=False)

    widget = hdd_manager.c.widget["hdd"]
    widget.eval(f"self.path = '{fake_stat_file.name}'")

    set_io_ticks(fake_stat_file, 0)
    widget.eval("self.update(self.poll())")
    assert widget.info()["text"] == "HDD 0.0%"

    set_io_ticks(fake_stat_file, 300000)
    widget.eval("self.update(self.poll())")
    assert widget.info()["text"] == "HDD 50.0%"

    set_io_ticks(fake_stat_file, 900000)
    widget.eval("self.update(self.poll())")
    assert widget.info()["text"] == "HDD 100.0%"

    set_io_ticks(fake_stat_file, 2000000)
    widget.eval("self.update(self.poll())")
    assert widget.info()["text"] == "HDD 100.0%"

    set_io_ticks(fake_stat_file, 0)
    widget.eval("self.update(self.poll())")
    assert widget.info()["text"] == "HDD 0.0%"
