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

import libqtile.widget
from test.widgets.test_check_updates import MockPopen, MockSpawn


@pytest.fixture
def widget(monkeypatch):
    monkeypatch.setattr("libqtile.widget.base.subprocess.check_output", MockSpawn.call_process)
    monkeypatch.setattr("libqtile.widget.check_updates.Popen", MockPopen)
    yield libqtile.widget.CheckUpdates


@pytest.mark.parametrize(
    "screenshot_manager",
    [
        {"no_update_string": "No updates"},
    ],
    indirect=True,
)
def ss_checkupdates(screenshot_manager):
    # First screenshot shows updates available
    screenshot_manager.take_screenshot()

    # Polling mocks updates being installed
    screenshot_manager.c.widget["checkupdates"].eval("self.update(self.poll())")

    # Second screenshot means there are no updates to install
    screenshot_manager.take_screenshot()
