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

import libqtile.config
import libqtile.widget
from libqtile.bar import Bar


class MockPsutil(ModuleType):
    @classmethod
    def cpu_percent(cls):
        return 2.6

    @classmethod
    def cpu_freq(cls):
        class Freq:
            def __init__(self):
                self.current = 500.067
                self.min = 400.0
                self.max = 2800.0

        return Freq()


@pytest.fixture
def cpu_manager(monkeypatch, manager_nospawn, minimal_conf_noscreen):
    monkeypatch.setitem(sys.modules, "psutil", MockPsutil("psutil"))
    from libqtile.widget import cpu

    reload(cpu)

    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(top=Bar([cpu.CPU()], 10))]

    manager_nospawn.start(config)
    yield manager_nospawn


def test_cpu(cpu_manager):
    assert cpu_manager.c.widget["cpu"].info()["text"] == "CPU 0.5GHz 2.6%"
