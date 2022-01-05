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

# The test_widget_init_config will cover the scenario where `kbdd` is not
# running and will also run the asyncio _config_async method.

# This test file covers the remaining widget code

import sys
from importlib import reload
from types import ModuleType

import pytest

from test.widgets.conftest import FakeBar


async def mock_signal_receiver(*args, **kwargs):
    return True


class Mockconstants(ModuleType):
    class MessageType:
        SIGNAL = 1


class MockSpawn:
    call_count = 0

    @classmethod
    def call_process(cls, *args, **kwargs):
        if cls.call_count == 0:
            cls.call_count += 1
            return ""
        return "kbdd"


class MockMessage:
    def __init__(self, is_signal=True, body=0):
        self.message_type = 1 if is_signal else 0
        self.body = [body]


@pytest.fixture
def patched_widget(monkeypatch):
    monkeypatch.setitem(sys.modules, "dbus_next.constants", Mockconstants("dbus_next.constants"))
    from libqtile.widget import keyboardkbdd

    reload(keyboardkbdd)

    # The next line shouldn't be necessary but I got occasional failures without it when testing locally
    monkeypatch.setattr("libqtile.widget.keyboardkbdd.MessageType", Mockconstants.MessageType)
    monkeypatch.setattr(
        "libqtile.widget.keyboardkbdd.KeyboardKbdd.call_process", MockSpawn.call_process
    )
    monkeypatch.setattr("libqtile.widget.keyboardkbdd.add_signal_receiver", mock_signal_receiver)
    return keyboardkbdd


def test_keyboardkbdd_process_running(fake_qtile, patched_widget, fake_window):
    MockSpawn.call_count = 1
    kbd = patched_widget.KeyboardKbdd(configured_keyboards=["gb", "us"])
    fakebar = FakeBar([kbd], window=fake_window)
    kbd._configure(fake_qtile, fakebar)
    assert kbd.is_kbdd_running
    assert kbd.keyboard == "gb"

    # Create a message with the index of the active keyboard
    message = MockMessage(body=1)
    kbd._signal_received(message)
    assert kbd.keyboard == "us"

    # Test non-"signal" message
    message = MockMessage(body=0, is_signal=False)
    kbd._signal_received(message)
    assert kbd.keyboard == "us"


def test_keyboardkbdd_process_not_running(fake_qtile, patched_widget, fake_window):
    MockSpawn.call_count = 0
    kbd = patched_widget.KeyboardKbdd(configured_keyboards=["gb", "us"])
    fakebar = FakeBar([kbd], window=fake_window)
    kbd._configure(fake_qtile, fakebar)
    assert not kbd.is_kbdd_running
    assert kbd.keyboard == "N/A"

    # Second call of _check_kbdd will confirm process running
    # so widget should now show layout
    kbd.poll()
    assert kbd.keyboard == "gb"


# Custom colours are not set until a signal is received
# TO DO: This should be fixed so the colour is set on __init__
def test_keyboard_kbdd_colours(fake_qtile, patched_widget, fake_window):
    MockSpawn.call_count = 1
    kbd = patched_widget.KeyboardKbdd(
        configured_keyboards=["gb", "us"], colours=["#ff0000", "#00ff00"]
    )
    fakebar = FakeBar([kbd], window=fake_window)
    kbd._configure(fake_qtile, fakebar)

    # Create a message with the index of the active keyboard
    message = MockMessage(body=0)
    kbd._signal_received(message)
    assert kbd.layout.colour == "#ff0000"

    # Create a message with the index of the active keyboard
    message = MockMessage(body=1)
    kbd._signal_received(message)
    assert kbd.layout.colour == "#00ff00"

    # No change where self.colours is a string
    kbd.colours = "#ffff00"
    kbd._set_colour(1)
    assert kbd.layout.colour == "#00ff00"

    # Colours list is shorter than length of layouts
    kbd.colours = ["#ff00ff"]

    # Should pick second item in colours list but it doesn't exit
    # so widget looks for previous item
    kbd._set_colour(1)
    assert kbd.layout.colour == "#ff00ff"
