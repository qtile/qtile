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

import sys
from importlib import reload
from types import ModuleType

import pytest

import libqtile.bar
import libqtile.config


def no_op(*args, **kwargs):
    pass


class FakePsutil(ModuleType):
    class virtual_memory:  # noqa: N801
        def __init__(self):
            self.used = 2534260736  # 2,474,864K, 2,417M, 2.36G
            self.total = 8180686848  # 7,988,952K, 7,802M, 7.72G
            self.free = 2354114560
            self.percent = 39.4
            self.buffers = 346394624
            self.active = 1132359680
            self.inactive = 3862183936
            self.shared = 516395008

    class swap_memory:  # noqa: N801
        def __init__(self):
            self.total = 8429498368
            self.used = 0
            self.free = 8429498368
            self.percent = 0.0


@pytest.fixture()
def patched_memory(
    monkeypatch,
):
    monkeypatch.setitem(sys.modules, "psutil", FakePsutil("psutil"))
    from libqtile.widget import memory

    reload(memory)
    return memory


def test_memory_defaults(manager_nospawn, minimal_conf_noscreen, patched_memory):
    """Test no text when free space over threshold"""
    widget = patched_memory.Memory()
    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(top=libqtile.bar.Bar([widget], 10))]
    manager_nospawn.start(config)
    assert manager_nospawn.c.widget["memory"].info()["text"] == " 2417M/ 7802M"


@pytest.mark.parametrize(
    "unit,expects",
    [
        ("G", " 2G/ 8G"),
        ("M", " 2417M/ 7802M"),
        ("K", " 2474864K/ 7988952K"),
        ("B", " 2534260736B/ 8180686848B"),
    ],
)
def test_memory_units(manager_nospawn, minimal_conf_noscreen, patched_memory, unit, expects):
    """Test no text when free space over threshold"""
    widget = patched_memory.Memory(measure_mem=unit)
    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(top=libqtile.bar.Bar([widget], 10))]
    manager_nospawn.start(config)
    assert manager_nospawn.c.widget["memory"].info()["text"] == expects
