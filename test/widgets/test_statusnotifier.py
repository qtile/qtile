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
import pytest

import libqtile.bar
import libqtile.config
import libqtile.confreader
import libqtile.layout
import libqtile.widget
from test.helpers import Retry  # noqa: I001


@Retry(ignore_exceptions=(AssertionError,))
def wait_for_icon(widget, hidden=True, prop="width"):
    width = widget.info()[prop]
    if hidden:
        assert width == 0
    else:
        assert width > 0


@Retry(ignore_exceptions=(AssertionError,))
def check_fullscreen(windows, fullscreen=True):
    full = windows()[0]["fullscreen"]
    assert full is fullscreen


@pytest.fixture(scope="function")
def sni_config(request, manager_nospawn):
    """
    Fixture provides a manager instance with StatusNotifier in the bar.

    Widget can be customised via parameterize.
    """

    class SNIConfig(libqtile.confreader.Config):
        """Config for the test."""

        auto_fullscreen = True
        keys = []
        mouse = []
        groups = [
            libqtile.config.Group("a"),
        ]
        layouts = [libqtile.layout.Max()]
        floating_layout = libqtile.resources.default_config.floating_layout
        screens = [
            libqtile.config.Screen(
                top=libqtile.bar.Bar(
                    [libqtile.widget.StatusNotifier(**getattr(request, "param", dict()))],
                    50,
                ),
            )
        ]

    yield SNIConfig


@pytest.mark.usefixtures("dbus")
def test_statusnotifier_defaults(manager_nospawn, sni_config):
    """Check that widget displays and removes icon."""
    manager_nospawn.start(sni_config)
    widget = manager_nospawn.c.widget["statusnotifier"]
    assert widget.info()["width"] == 0

    win = manager_nospawn.test_window("TestSNI", export_sni=True)
    wait_for_icon(widget, hidden=False)

    # Kill it and icon disappears
    manager_nospawn.kill_window(win)
    wait_for_icon(widget, hidden=True)


@pytest.mark.usefixtures("dbus")
def test_statusnotifier_defaults_vertical_bar(manager_nospawn, sni_config):
    """Check that widget displays and removes icon."""
    screen = sni_config.screens[0]
    screen.left = screen.top
    screen.top = None
    manager_nospawn.start(sni_config)
    widget = manager_nospawn.c.widget["statusnotifier"]
    assert widget.info()["height"] == 0

    win = manager_nospawn.test_window("TestSNI", export_sni=True)
    wait_for_icon(widget, hidden=False, prop="height")

    # Kill it and icon disappears
    manager_nospawn.kill_window(win)
    wait_for_icon(widget, hidden=True, prop="height")


@pytest.mark.parametrize("sni_config", [{"icon_size": 35}], indirect=True)
@pytest.mark.usefixtures("dbus")
def test_statusnotifier_icon_size(manager_nospawn, sni_config):
    """Check that widget displays and removes icon."""
    manager_nospawn.start(sni_config)
    widget = manager_nospawn.c.widget["statusnotifier"]
    assert widget.info()["width"] == 0

    win = manager_nospawn.test_window("TestSNI", export_sni=True)
    wait_for_icon(widget, hidden=False)

    # Width should be icon_size (35) + 2 * padding (3) = 41
    assert widget.info()["width"] == 41

    manager_nospawn.kill_window(win)


@pytest.mark.usefixtures("dbus")
def test_statusnotifier_left_click(manager_nospawn, sni_config):
    """Check `activate` method when left-clicking widget."""
    manager_nospawn.start(sni_config)
    widget = manager_nospawn.c.widget["statusnotifier"]
    windows = manager_nospawn.c.windows

    assert widget.info()["width"] == 0

    win = manager_nospawn.test_window("TestSNILeftClick", export_sni=True)
    wait_for_icon(widget, hidden=False)

    # Check we have window and that it's not fullscreen
    assert len(windows()) == 1
    check_fullscreen(windows, False)

    # Left click will toggle fullscreen
    manager_nospawn.c.bar["top"].fake_button_press(0, "top", 10, 0, 1)
    check_fullscreen(windows, True)

    # Left click again will restore window
    manager_nospawn.c.bar["top"].fake_button_press(0, "top", 10, 0, 1)
    check_fullscreen(windows, False)

    manager_nospawn.kill_window(win)
    assert not windows()


@pytest.mark.usefixtures("dbus")
def test_statusnotifier_left_click_vertical_bar(manager_nospawn, sni_config):
    """Check `activate` method when left-clicking widget in vertical bar."""
    screen = sni_config.screens[0]
    screen.left = screen.top
    screen.top = None

    manager_nospawn.start(sni_config)
    widget = manager_nospawn.c.widget["statusnotifier"]
    windows = manager_nospawn.c.windows

    assert widget.info()["height"] == 0

    win = manager_nospawn.test_window("TestSNILeftClick", export_sni=True)
    wait_for_icon(widget, hidden=False, prop="height")

    # Check we have window and that it's not fullscreen
    assert len(windows()) == 1
    check_fullscreen(windows, False)

    # Left click will toggle fullscreen
    manager_nospawn.c.bar["left"].fake_button_press(0, "left", 0, 10, 1)
    check_fullscreen(windows, True)

    # Left click again will restore window
    manager_nospawn.c.bar["left"].fake_button_press(0, "left", 0, 10, 1)
    check_fullscreen(windows, False)

    manager_nospawn.kill_window(win)
    assert not windows()
