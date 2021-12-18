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
import pytest

from test.widgets.test_mpris2widget import (  # noqa: F401
    METADATA_PAUSED,
    METADATA_PLAYING,
    patched_module,
)


@pytest.fixture
def widget(monkeypatch, patched_module):  # noqa: F811
    patched_module.Mpris2.PLAYING = METADATA_PLAYING
    patched_module.Mpris2.PAUSED = METADATA_PAUSED
    return patched_module.Mpris2


@pytest.mark.parametrize(
    "screenshot_manager",
    [{}, {"scroll_chars": 45}, {"display_metadata": ["xesam:url"]}],
    indirect=True,
)
def ss_mpris2(screenshot_manager):
    widget = screenshot_manager.c.widget["mpris2"]
    widget.eval("self.message(self.PLAYING)")
    widget.eval("self.scroll_text()")
    screenshot_manager.take_screenshot()


@pytest.mark.parametrize(
    "screenshot_manager", [{"stop_pause_text": "Player paused"}], indirect=True
)
def ss_mpris2_paused(screenshot_manager):
    widget = screenshot_manager.c.widget["mpris2"]
    widget.eval("self.message(self.PAUSED)")
    widget.eval("self.scroll_text()")
    screenshot_manager.take_screenshot()
