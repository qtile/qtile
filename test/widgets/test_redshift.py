# Copyright (c) 2024 Saath Satheeshkumar (saths008)
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

from libqtile.config import Bar, Screen
from libqtile.confreader import Config
from libqtile.widget import redshift


def mock_run(argv, check):
    pass


@pytest.fixture(scope="function")
def patched_redshift(monkeypatch):
    class PatchedRedshift(redshift.Redshift):
        def __init__(self, **config):
            monkeypatch.setattr("subprocess.run", mock_run)
            redshift.Redshift.__init__(self, **config)
            self.name = "redshift"

    yield PatchedRedshift


@pytest.fixture(scope="function")
def redshift_manager(manager_nospawn, request, patched_redshift):
    if manager_nospawn.backend.name == "wayland":
        pytest.skip("Skipping test on Wayland.")

    class GroupConfig(Config):
        screens = [
            Screen(
                top=Bar(
                    [
                        patched_redshift(
                            update_interval=10,
                            **getattr(request, "param", dict()),
                        )
                    ],
                    30,
                )
            )
        ]

    manager_nospawn.start(GroupConfig)

    yield manager_nospawn


def config(**kwargs):
    return pytest.mark.parametrize("redshift_manager", [kwargs], indirect=True)


def test_defaults(redshift_manager):
    widget = redshift_manager.c.widget["redshift"]

    def text():
        return widget.info()["text"]

    def click():
        redshift_manager.c.bar["top"].fake_button_press(0, 0, 1)

    disabled_txt = "󱠃"
    enabled_txt = "󰛨"
    assert text() == disabled_txt

    scroll_vals = [
        "Brightness: 1.0",
        "Temperature: 1700",
        "Gamma: 1.0:1.0:1.0",
        enabled_txt,
    ]

    click()

    for _, val in enumerate(scroll_vals):
        widget.scroll_up()
        assert text() == val

    click()
    for _ in range(len(scroll_vals)):
        widget.scroll_down()
        # Test that scroll only works when
        # widget is enabled
        assert text() == disabled_txt


@config(disabled_txt="Redshift disabled", enabled_txt="Redshift enabled")
def test_changed_default_txt_non_fmted(redshift_manager):
    widget = redshift_manager.c.widget["redshift"]

    def text():
        return widget.info()["text"]

    def click():
        redshift_manager.c.bar["top"].fake_button_press(0, 0, 1)

    disabled_txt = "Redshift disabled"
    enabled_txt = "Redshift enabled"

    assert text() == disabled_txt

    click()
    assert text() == enabled_txt

    scroll_vals = [
        "Brightness: 1.0",
        "Temperature: 1700",
        "Gamma: 1.0:1.0:1.0",
        enabled_txt,
    ]

    for _, val in enumerate(scroll_vals):
        widget.scroll_up()
        assert text() == val

    # move enabled_txt to the first index
    scroll_vals.remove(enabled_txt)
    scroll_vals = [enabled_txt] + scroll_vals

    for _, val in enumerate(reversed(scroll_vals)):
        widget.scroll_down()
        assert text() == val


@config(
    brightness=0.4,
    disabled_txt="brightness{brightness}, temp{temperature}, r{gamma_red}, g{gamma_green}, b{gamma_blue}, is_enabled{is_enabled}",
    enabled_txt="brightness{brightness}, temp{temperature}, r{gamma_red}, g{gamma_green}, b{gamma_blue}, is_enabled{is_enabled}",
    gamma_red=0.2,
    gamma_green=0.2,
    gamma_blue=0.2,
    temperature=1200,
)
def test_changed_default_txt_fmted(redshift_manager):
    widget = redshift_manager.c.widget["redshift"]

    def text():
        return widget.info()["text"]

    def click():
        redshift_manager.c.bar["top"].fake_button_press(0, 0, 1)

    brightness = 0.4
    gamma_red = 0.2
    gamma_green = 0.2
    gamma_blue = 0.2
    gamma_val = redshift.GammaGroup(gamma_red, gamma_green, gamma_blue)
    temp = 1200

    comm_str = f"brightness{brightness}, temp{temp}, r{gamma_red}, g{gamma_green}, b{gamma_blue}"
    disabled_txt = comm_str + f", is_enabled{False}"
    enabled_txt = comm_str + f", is_enabled{True}"

    assert text() == disabled_txt

    click()
    assert text() == enabled_txt

    scroll_vals = [
        f"Brightness: {brightness}",
        f"Temperature: {temp}",
        f"Gamma: {gamma_val._redshift_fmt()}",
        enabled_txt,
    ]

    for _, val in enumerate(scroll_vals):
        widget.scroll_up()
        assert text() == val

    scroll_vals.remove(enabled_txt)
    scroll_vals = [enabled_txt] + scroll_vals

    for _, val in enumerate(reversed(scroll_vals)):
        widget.scroll_down()
        assert text() == val


@config(
    disabled_txt="Disabled",
    enabled_txt="Enabled t:{temperature} b:{brightness}",
    brightness=0.5,
    brightness_step=0.2,
    temperature=1200,
    temperature_step=101,
)
def test_increase_decrease_temp_brightness(redshift_manager):
    widget = redshift_manager.c.widget["redshift"]

    def text():
        return widget.info()["text"]

    def click():
        redshift_manager.c.bar["top"].fake_button_press(0, 0, 1)

    def right_click():
        redshift_manager.c.bar["top"].fake_button_press(0, 0, 3)

    disabled_txt = "Disabled"
    enabled_txt = "Enabled t:1200 b:0.5"

    assert text() == disabled_txt

    click()

    assert text() == enabled_txt

    widget.scroll_up()

    # Test that the right click respects brightness boundaries
    brightness_vals = [0.5, 0.7, 0.9, 1.0, 1.0, 1.0]
    for _, val in enumerate(brightness_vals):
        assert text() == f"Brightness: {val}"
        right_click()

    # Test that the left click respects brightness boundaries
    brightness_vals = [1.0, 0.8, 0.6, 0.4, 0.2, 0.1, 0.1]
    for _, val in enumerate(brightness_vals):
        assert text() == f"Brightness: {val}"
        click()

    widget.scroll_down()  # Enabled

    assert text() == "Enabled t:1200 b:0.1"

    widget.scroll_down()  # Gamma
    widget.scroll_down()  # Temperature

    # Test that the right click respects temperature boundaries
    temp_vals = [1200]

    temp_lower_bound = 1000
    temp_upper_bound = 25000
    while temp_vals[-1] < temp_upper_bound:
        new_temp_val = temp_vals[-1] + 101
        new_temp_val = min(new_temp_val, temp_upper_bound)
        temp_vals.append(new_temp_val)

    for _, val in enumerate(temp_vals):
        assert text() == f"Temperature: {val}"
        right_click()

    # Test that the left click respects temperature boundaries
    temp_vals = [temp_upper_bound]
    while temp_vals[-1] > temp_lower_bound:
        new_temp_val = temp_vals[-1] - 101
        new_temp_val = max(new_temp_val, temp_lower_bound)
        temp_vals.append(new_temp_val)

    for _, val in enumerate(temp_vals):
        assert text() == f"Temperature: {val}"
        click()

    widget.scroll_up()  # Gamma
    widget.scroll_up()  # Temperature
    assert text() == "Enabled t:1000 b:0.1"
