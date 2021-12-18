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

import pytest

import libqtile.widget
from test.widgets.test_mpd2widget import MockMPD


@pytest.fixture
def widget(monkeypatch):
    monkeypatch.setitem(sys.modules, "mpd", MockMPD("mpd"))
    yield libqtile.widget.Mpd2


@pytest.mark.parametrize(
    "screenshot_manager",
    [{}, {"status_format": "{play_status} {artist}/{title}"}],
    indirect=True,
)
def ss_mpd2(screenshot_manager):
    screenshot_manager.take_screenshot()


@pytest.mark.parametrize(
    "screenshot_manager",
    [
        {
            "idle_format": "{play_status} {idle_message}",
            "idle_message": "MPD not playing",
        }
    ],
    indirect=True,
)
def ss_mpd2_idle(screenshot_manager):
    widget = screenshot_manager.c.widget["mpd2"]
    widget.eval("self.client.force_idle()")
    widget.eval("self.update(self.poll())")
    widget.eval("self.bar.draw()")
    screenshot_manager.take_screenshot()
