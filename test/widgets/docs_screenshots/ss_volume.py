# Copyright (c) 2022 elParaguayo
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
import os
import shutil

import pytest

from libqtile.widget import Volume
from test.widgets.conftest import DATA_DIR

ICON = os.path.join(DATA_DIR, "svg", "audio-volume-muted.svg")
TEMP_DIR = os.path.join(DATA_DIR, "ss_temp")


@pytest.fixture
def widget():
    os.mkdir(TEMP_DIR)
    for i in (
        "audio-volume-high.svg",
        "audio-volume-low.svg",
        "audio-volume-medium.svg",
        "audio-volume-muted.svg",
    ):
        shutil.copy(ICON, os.path.join(TEMP_DIR, i))

    yield Volume

    shutil.rmtree(TEMP_DIR)


@pytest.mark.parametrize(
    "screenshot_manager",
    [{"theme_path": TEMP_DIR}, {"emoji": True}, {"fmt": "Vol: {}"}],
    indirect=True,
)
def ss_volume(screenshot_manager):
    widget = screenshot_manager.c.widget["volume"]
    widget.eval("self.volume=-1")
    widget.eval("self._update_drawer()")
    widget.eval("self.bar.draw()")
    screenshot_manager.take_screenshot()
