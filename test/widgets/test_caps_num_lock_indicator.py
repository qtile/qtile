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

import subprocess
from typing import List

import pytest

from libqtile.widget import caps_num_lock_indicator
from test.widgets.conftest import FakeBar


class MockCapsNumLockIndicator:
    CalledProcessError = None

    info: List[List[str]] = []
    is_error = False
    index = 0

    @classmethod
    def reset(cls):
        cls.info = [
            [
                "Keyboard Control:",
                "  auto repeat:  on    key click percent:  0    LED mask:  00000002",
                "  XKB indicators:",
                "    00: Caps Lock:   off    01: Num Lock:    on     02: Scroll Lock: off",
                "    03: Compose:     off    04: Kana:        off    05: Sleep:       off",
            ],
            [
                "Keyboard Control:",
                "  auto repeat:  on    key click percent:  0    LED mask:  00000002",
                "  XKB indicators:",
                "    00: Caps Lock:   on     01: Num Lock:    on     02: Scroll Lock: off",
                "    03: Compose:     off    04: Kana:        off    05: Sleep:       off",
            ],
        ]
        cls.index = 0
        cls.is_error = False

    @classmethod
    def call_process(cls, cmd):
        if cls.is_error:
            raise subprocess.CalledProcessError(-1, cmd=cmd, output="Couldn't call xset.")

        if cmd[1:] == ["q"]:
            track = cls.info[cls.index]
            output = "\n".join(track)
            return output


def no_op(*args, **kwargs):
    pass


@pytest.fixture
def patched_cnli(monkeypatch):
    MockCapsNumLockIndicator.reset()
    monkeypatch.setattr(
        "libqtile.widget.caps_num_lock_indicator.subprocess", MockCapsNumLockIndicator
    )
    monkeypatch.setattr(
        "libqtile.widget.caps_num_lock_indicator.subprocess.CalledProcessError",
        subprocess.CalledProcessError,
    )

    monkeypatch.setattr(
        "libqtile.widget.caps_num_lock_indicator.base.ThreadPoolText.call_process",
        MockCapsNumLockIndicator.call_process,
    )
    return caps_num_lock_indicator


def test_cnli(fake_qtile, patched_cnli, fake_window):
    widget = patched_cnli.CapsNumLockIndicator()
    fakebar = FakeBar([widget], window=fake_window)
    widget._configure(fake_qtile, fakebar)
    text = widget.poll()

    assert text == "Caps off Num on"


def test_cnli_caps_on(fake_qtile, patched_cnli, fake_window):
    widget = patched_cnli.CapsNumLockIndicator()

    # Simulate Caps on
    MockCapsNumLockIndicator.index = 1

    fakebar = FakeBar([widget], window=fake_window)
    widget._configure(fake_qtile, fakebar)
    text = widget.poll()

    assert text == "Caps on Num on"


def test_cnli_error_handling(fake_qtile, patched_cnli, fake_window):
    widget = patched_cnli.CapsNumLockIndicator()

    # Simulate a CalledProcessError exception
    MockCapsNumLockIndicator.is_error = True

    fakebar = FakeBar([widget], window=fake_window)
    widget._configure(fake_qtile, fakebar)
    text = widget.poll()

    # Widget does nothing with error message so text is blank
    assert text == ""
