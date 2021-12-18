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
import sys
from importlib import reload

import pytest

from test.widgets.test_keyboardkbdd import Mockconstants, MockSpawn, mock_signal_receiver


@pytest.fixture
def widget(monkeypatch):
    monkeypatch.setitem(sys.modules, "dbus_next.constants", Mockconstants("dbus_next.constants"))
    from libqtile.widget import keyboardkbdd

    reload(keyboardkbdd)
    monkeypatch.setattr("libqtile.widget.keyboardkbdd.MessageType", Mockconstants.MessageType)
    monkeypatch.setattr(
        "libqtile.widget.keyboardkbdd.KeyboardKbdd.call_process", MockSpawn.call_process
    )
    monkeypatch.setattr("libqtile.widget.keyboardkbdd.add_signal_receiver", mock_signal_receiver)
    return keyboardkbdd.KeyboardKbdd


@pytest.mark.parametrize(
    "screenshot_manager", [{"configured_keyboards": ["gb", "us"]}], indirect=True
)
def ss_keyboardkbdd(screenshot_manager):
    screenshot_manager.take_screenshot()
