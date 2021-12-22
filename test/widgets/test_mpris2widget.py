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

from test.widgets.conftest import FakeBar


def no_op(*args, **kwargs):
    pass


async def mock_signal_receiver(*args, **kwargs):
    return True


def fake_timer(interval, func, *args, **kwargs):
    class TimerObj:
        def cancel(self):
            pass

        @property
        def _scheduled(self):
            return False

    return TimerObj()


class MockConstants(ModuleType):
    class MessageType:
        SIGNAL = 1


class MockMessage:
    def __init__(self, is_signal=True, body=None):
        self.message_type = 1 if is_signal else 0
        self.body = body


# dbus_next message data is stored in variants. The widget extracts the
# information via the `value` attribute so we just need to mock that here.
class obj:  # noqa: N801
    def __init__(self, value):
        self.value = value


# Creates a mock message body containing both metadata and playback status
def metadata_and_status(status):
    return MockMessage(
        body=(
            "",
            {
                "Metadata": obj(
                    {
                        "mpris:trackid": obj(1),
                        "xesam:url": obj("/path/to/rickroll.mp3"),
                        "xesam:title": obj("Never Gonna Give You Up"),
                        "xesam:artist": obj(["Rick Astley"]),
                        "xesam:album": obj("Whenever You Need Somebody"),
                        "mpris:length": obj(200000000),
                    }
                ),
                "PlaybackStatus": obj(status),
            },
            [],
        )
    )


# Creates a mock message body containing just playback status
def playback_status(status, signal=True):
    return MockMessage(is_signal=signal, body=("", {"PlaybackStatus": obj(status)}, []))


METADATA_PLAYING = metadata_and_status("Playing")
METADATA_PAUSED = metadata_and_status("Paused")
STATUS_PLAYING = playback_status("Playing")
STATUS_PAUSED = playback_status("Paused")
STATUS_STOPPED = playback_status("Stopped")
NON_SIGNAL = playback_status("Paused", False)


@pytest.fixture
def patched_module(monkeypatch):
    # Remove dbus_next.constants entry from modules. If it's not there, don't raise error
    monkeypatch.delitem(sys.modules, "dbus_next.constants", raising=False)
    monkeypatch.setitem(sys.modules, "dbus_next.constants", MockConstants("dbus_next.constants"))
    from libqtile.widget import mpris2widget

    # Need to force reload of the module to ensure patched module is loaded
    # This may only be needed if dbus_next is installed on testing system so helpful for
    # local tests.
    reload(mpris2widget)
    monkeypatch.setattr("libqtile.widget.mpris2widget.add_signal_receiver", mock_signal_receiver)
    return mpris2widget


def test_mpris2_signal_handling(fake_qtile, patched_module, fake_window):
    mp = patched_module.Mpris2(scroll_chars=20, scroll_wait_intervals=5)
    fakebar = FakeBar([mp], window=fake_window)
    mp.timeout_add = fake_timer
    mp._configure(fake_qtile, fakebar)

    assert mp.displaytext == ""

    # No text will be displayed if widget is not configured
    mp.message(METADATA_PLAYING)
    assert mp.displaytext == ""

    # Set configured flag, create a message with the metadata and playback status
    mp.configured = True
    mp.message(METADATA_PLAYING)
    assert mp.displaytext == "Never Gonna Give You Up - Whenever You Need Somebody - Rick Astley"
    assert mp.text == ""

    # Text is displayed after first run of scroll_text
    mp.scroll_text()
    assert (
        mp.text
        == "Never Gonna Give You Up - Whenever You Need Somebody - Rick Astley"[: mp.scroll_chars]
    )

    # Text is scrolled 1 character after `scroll_wait_intervals`runs of scroll_text
    for _ in range(mp.scroll_wait_intervals):
        mp.scroll_text()
    assert (
        mp.text
        == "Never Gonna Give You Up - Whenever You Need Somebody - Rick Astley"[
            1 : mp.scroll_chars + 1
        ]
    )

    # Non-signal type message will be ignored
    mp.message(NON_SIGNAL)
    assert (
        mp.text
        == "Never Gonna Give You Up - Whenever You Need Somebody - Rick Astley"[
            1 : mp.scroll_chars + 1
        ]
    )

    # If widget receives "paused" signal with no metadata then default message is "Paused"
    mp.message(STATUS_PAUSED)
    assert mp.displaytext == "Paused"

    # If widget receives "stopped" signal with no metadata then widget is blank
    mp.message(STATUS_STOPPED)
    assert mp.displaytext == ""

    # Reset to playing + metadata
    mp.message(METADATA_PLAYING)
    mp.scroll_text()
    assert (
        mp.text
        == "Never Gonna Give You Up - Whenever You Need Somebody - Rick Astley"[: mp.scroll_chars]
    )

    # If widget receives "paused" signal with metadata then message is "Paused: {metadata}"
    mp.message(METADATA_PAUSED)
    mp.scroll_text()
    assert (
        mp.text
        == "Paused: Never Gonna Give You Up - Whenever You Need Somebody - Rick Astley"[
            : mp.scroll_chars
        ]
    )

    # If widget now receives "playing" signal with no metadata, "paused" word is removed
    mp.message(STATUS_PLAYING)
    mp.scroll_text()
    assert (
        mp.text
        == "Never Gonna Give You Up - Whenever You Need Somebody - Rick Astley"[: mp.scroll_chars]
    )

    info = mp.cmd_info()
    assert (
        info["displaytext"]
        == "Never Gonna Give You Up - Whenever You Need Somebody - Rick Astley"
    )
    assert info["isplaying"]


def test_mpris2_custom_stop_text(fake_qtile, patched_module, fake_window):
    mp = patched_module.Mpris2(stop_pause_text="Test Paused")
    fakebar = FakeBar([mp], window=fake_window)
    mp.timeout_add = fake_timer
    mp._configure(fake_qtile, fakebar)
    mp.configured = True

    mp.message(METADATA_PLAYING)
    assert mp.displaytext == "Never Gonna Give You Up - Whenever You Need Somebody - Rick Astley"
    assert mp.text == ""
    mp.scroll_text()

    # Check our custom paused wording is shown
    mp.message(STATUS_PAUSED)
    assert mp.displaytext == "Test Paused"


def test_mpris2_no_metadata(fake_qtile, patched_module, fake_window):
    mp = patched_module.Mpris2(stop_pause_text="Test Paused")
    fakebar = FakeBar([mp], window=fake_window)
    mp.timeout_add = fake_timer
    mp._configure(fake_qtile, fakebar)
    mp.configured = True

    mp.message(STATUS_PLAYING)
    assert mp.displaytext == "No metadata for current track"


def test_mpris2_no_scroll(fake_qtile, patched_module, fake_window):
    # If no scrolling, then the update function creates the text to display
    # and draws the bar.
    mp = patched_module.Mpris2(scroll_chars=None)
    fakebar = FakeBar([mp], window=fake_window)
    mp.timeout_add = fake_timer
    mp._configure(fake_qtile, fakebar)
    mp.configured = True

    mp.message(METADATA_PLAYING)
    assert mp.text == "Never Gonna Give You Up - Whenever You Need Somebody - Rick Astley"

    mp.message(METADATA_PAUSED)
    assert mp.text == "Paused: Never Gonna Give You Up - Whenever You Need Somebody - Rick Astley"


def test_mpris2_clear_after_scroll(fake_qtile, patched_module, fake_window):
    mp = patched_module.Mpris2(scroll_chars=60, scroll_wait_intervals=2)
    fakebar = FakeBar([mp], window=fake_window)
    mp.timeout_add = fake_timer
    mp._configure(fake_qtile, fakebar)
    mp.configured = True

    mp.message(METADATA_PLAYING)

    # After 10 loops, text should be cleared as scroll reaches end of text.
    # 2 loops before starting scroll
    # 6 loops to loop over remaining text in dispay
    # 1 additional loop at end of text (so total 2 loops on that display)
    # 1 loop to clear.
    for i in range(10):
        mp.scroll_text()
    assert mp.text == ""


# TO DO: untested lines
# 85-86: Logging when unable to subscribe to dbus signal. Needs `caplog`
