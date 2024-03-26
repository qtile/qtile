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

import sys
import tempfile
from importlib import reload

import pytest

from test.widgets.test_hdd import MockPsutil, set_io_ticks


@pytest.fixture
def widget(monkeypatch):
    monkeypatch.setitem(sys.modules, "psutil", MockPsutil("psutil"))
    from libqtile.widget import hdd

    reload(hdd)
    yield hdd.HDD


def ss_cpu(screenshot_manager):
    # Create a fake stat file
    temp_file = tempfile.NamedTemporaryFile(mode="w+", delete=False)
    widget = screenshot_manager.c.widget["hdd"]
    widget.eval(f"self.path = '{temp_file.name}'")

    set_io_ticks(temp_file, 0)
    widget.eval("self.update(self.poll())")

    set_io_ticks(temp_file, 123000)
    widget.eval("self.update(self.poll())")

    screenshot_manager.take_screenshot()
