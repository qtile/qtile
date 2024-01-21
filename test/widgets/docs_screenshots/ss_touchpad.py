# Copyright (c) 2024 Seweryn Rusecki
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

from libqtile.widget import touchpad


@pytest.fixture
def widget(monkeypatch):
    monkeypatch.setattr(
        touchpad.Touchpad,
        "_get_touchpad_device_name",
        lambda self: "",
    )
    monkeypatch.setattr(
        touchpad.Touchpad,
        "_get_touchpad_enabled",
        lambda self, id: True,
    )
    monkeypatch.setattr(
        touchpad.Touchpad,
        "_set_touchpad_enabled",
        lambda self, id, state: None,
    )
    yield touchpad.Touchpad


@pytest.mark.parametrize(
    "screenshot_manager", [{"format": "Touchpad: {state}", "enabled_char": "[ok]"}], indirect=True
)
def ss_touchpad(screenshot_manager):
    screenshot_manager.take_screenshot()
