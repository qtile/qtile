# Copyright (c) 2024 Saath Satheeshkumar(saths008)
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
from types import ModuleType

import pytest

from libqtile.config import Bar, Screen
from libqtile.confreader import Config
from libqtile.widget import redshift


class MockRedshiftDriver(ModuleType):
    """
    Helper class as redshift is not available in
    the test environment, so without this mock the tests will crash
    """

    def enable(self, temperature, gamma: redshift.GammaGroup, brightness):
        pass

    def reset(self):
        pass


def get_mock_rs_driver(_):
    return MockRedshiftDriver("redshift_driver")


@pytest.fixture(scope="function")
def patched_redshift(monkeypatch):
    class PatchedRedshift(redshift.Redshift):
        def __init__(self, **config):
            monkeypatch.setattr(
                "libqtile.widget.redshift.Redshift._get_rs_driver", get_mock_rs_driver
            )
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
        disabled_txt,
    ]

    for _, val in enumerate(scroll_vals):
        widget.scroll_up()
        assert text() == val

    # move enabled_txt to the first index
    scroll_vals.remove(disabled_txt)
    scroll_vals = [disabled_txt] + scroll_vals

    for _, val in enumerate(reversed(scroll_vals)):
        widget.scroll_down()
        assert text() == val

    click()
    assert text() == enabled_txt

    click()
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

    click()

    scroll_vals = [
        f"Brightness: {brightness}",
        f"Temperature: {temp}",
        f"Gamma: {gamma_val._redshift_fmt()}",
        disabled_txt,
    ]

    for _, val in enumerate(scroll_vals):
        widget.scroll_up()
        assert text() == val

    scroll_vals.remove(disabled_txt)
    scroll_vals = [disabled_txt] + scroll_vals

    for _, val in enumerate(reversed(scroll_vals)):
        widget.scroll_down()
        assert text() == val
