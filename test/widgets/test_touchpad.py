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
from test.widgets.conftest import FakeBar

xinput_names = (
    "Virtual core pointer\n"
    "Virtual core XTEST pointer\n"
    "DELL0ABC:DE F123:4567 Mouse\n"
    "DELL0ABC:DE F123:4567 Touchpad\n"
    "Virtual core keyboard\n"
    "Virtual core XTEST keyboard\n"
    "Power Button\n"
    "Video Bus\n"
)

xinput_properties_enabled = (
    "Device 'DELL0ABC:DE F123:4567 Touchpad':\n"
    "	Device Enabled (159):	1\n"
    "	Coordinate Transformation Matrix (161):	1.000000, 0.000000\n"
    "	libinput Tapping Enabled (289):	0\n"
)

xinput_properties_disabled = (
    "Device 'DELL0ABC:DE F123:4567 Touchpad':\n"
    "	Device Enabled (159):	0\n"
    "	Coordinate Transformation Matrix (161):	1.000000, 0.000000\n"
    "	libinput Tapping Enabled (289):	0\n"
)


def mock_check_output(commands, *args, **kwargs):
    if commands == ["xinput", "list", "--name-only"]:
        return xinput_names
    elif commands[:2] == ["xinput", "list-props"]:
        if commands[2] == "device_enabled":
            return xinput_properties_enabled
        if commands[2] == "device_disabled":
            return xinput_properties_disabled

    assert False, "Mock functionality not implemented!"


@pytest.fixture
def patched_touchpad(monkeypatch):
    monkeypatch.setattr(
        "libqtile.widget.touchpad.subprocess.check_output",
        mock_check_output,
    )
    yield touchpad


@pytest.mark.parametrize(
    "state, expected", [(True, "Touchpad: enabled"), (False, "Touchpad: disabled")]
)
def test_touchpad_text(fake_qtile, fake_window, patched_touchpad, state, expected):
    widget = patched_touchpad.Touchpad(
        format="Touchpad: {state}",
        enabled_char="enabled",
        disabled_char="disabled",
        device_id="0",
        get_state_func=lambda id: state,
        set_state_func=lambda id, st: None,
    )
    fakebar = FakeBar([widget], window=fake_window)
    widget._configure(fake_qtile, fakebar)
    text = widget.poll()

    assert text == expected, f"Touchpad generated wrong text: {text}, expected: {expected}"


def test_get_touchpad_device_name(patched_touchpad):
    get_touchpad_device_name = patched_touchpad.get_touchpad_device_name
    result = get_touchpad_device_name()
    expected = "DELL0ABC:DE F123:4567 Touchpad"

    assert result == expected, f"Wrong device detected: {result}, expected: {expected}"


@pytest.mark.parametrize(
    "device, expected", [("device_enabled", True), ("device_disabled", False)]
)
def test_get_touchpad_enabled(patched_touchpad, device, expected):
    get_touchpad_enabled = patched_touchpad.get_touchpad_enabled
    result = get_touchpad_enabled(device)

    assert result == expected, f"Invalid device stated detected: {result}, expected: {expected}"
