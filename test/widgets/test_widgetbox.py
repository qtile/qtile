# Copyright (c) 2021-22 elParaguayo
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

import libqtile.config
from libqtile.widget import Systray, TextBox, WidgetBox
from test.widgets.conftest import FakeBar


def test_widgetbox_widget(fake_qtile, fake_window):

    tb_one = TextBox(name="tb_one", text="TB ONE")
    tb_two = TextBox(name="tb_two", text="TB TWO")

    # Give widgetbox invalid value for button location
    widget_box = WidgetBox(widgets=[tb_one, tb_two], close_button_location="middle", fontsize=10)

    # Create a bar and set attributes needed to run widget
    fakebar = FakeBar([widget_box], window=fake_window)

    # Configure the widget box
    widget_box._configure(fake_qtile, fakebar)

    # Invalid value should be corrected to default
    assert widget_box.close_button_location == "left"

    # Check only widget in bar is widgetbox
    assert fakebar.widgets == [widget_box]

    # Open box
    widget_box.cmd_toggle()

    # Check it's open
    assert widget_box.box_is_open

    # Default text position is left
    assert fakebar.widgets == [widget_box, tb_one, tb_two]

    # Close box
    widget_box.cmd_toggle()

    # Check it's closed
    assert not widget_box.box_is_open

    # Check widgets have been removed
    assert fakebar.widgets == [widget_box]

    # Move button to right-hand side
    widget_box.close_button_location = "right"

    # Re-open box with new layout
    widget_box.cmd_toggle()

    # Now widgetbox is on the right
    assert fakebar.widgets == [tb_one, tb_two, widget_box]


def test_widgetbox_mirror(manager_nospawn, minimal_conf_noscreen):
    config = minimal_conf_noscreen
    tbox = TextBox(text="Text Box")
    config.screens = [
        libqtile.config.Screen(top=libqtile.bar.Bar([tbox, WidgetBox(widgets=[tbox])], 10))
    ]

    manager_nospawn.start(config)

    manager_nospawn.c.widget["widgetbox"].toggle()
    topbar = manager_nospawn.c.bar["top"]
    widgets = [w["name"] for w in topbar.info()["widgets"]]
    assert widgets == ["textbox", "widgetbox", "mirror"]


def test_widgetbox_mouse_click(manager_nospawn, minimal_conf_noscreen):
    config = minimal_conf_noscreen
    tbox = TextBox(text="Text Box")
    config.screens = [
        libqtile.config.Screen(top=libqtile.bar.Bar([WidgetBox(widgets=[tbox])], 10))
    ]

    manager_nospawn.start(config)

    topbar = manager_nospawn.c.bar["top"]
    assert len(topbar.info()["widgets"]) == 1

    topbar.fake_button_press(0, "top", 0, 0, button=1)
    assert len(topbar.info()["widgets"]) == 2

    topbar.fake_button_press(0, "top", 0, 0, button=1)
    assert len(topbar.info()["widgets"]) == 1


def test_widgetbox_with_systray_reconfigure_screens_box_open(
    manager_nospawn, minimal_conf_noscreen, backend_name
):
    """Check that Systray does not crash when inside an open widgetbox."""
    if backend_name == "wayland":
        pytest.skip("Skipping test on Wayland.")

    config = minimal_conf_noscreen
    config.screens = [
        libqtile.config.Screen(top=libqtile.bar.Bar([WidgetBox(widgets=[Systray()])], 10))
    ]

    manager_nospawn.start(config)

    topbar = manager_nospawn.c.bar["top"]
    assert len(topbar.info()["widgets"]) == 1

    manager_nospawn.c.widget["widgetbox"].toggle()
    assert len(topbar.info()["widgets"]) == 2

    manager_nospawn.c.reconfigure_screens()

    assert len(topbar.info()["widgets"]) == 2
    names = [w["name"] for w in topbar.info()["widgets"]]
    assert names == ["widgetbox", "systray"]


def test_widgetbox_with_systray_reconfigure_screens_box_closed(
    manager_nospawn, minimal_conf_noscreen, backend_name
):
    """Check that Systray does not crash when inside a closed widgetbox."""
    if backend_name == "wayland":
        pytest.skip("Skipping test on Wayland.")

    config = minimal_conf_noscreen
    config.screens = [
        libqtile.config.Screen(top=libqtile.bar.Bar([WidgetBox(widgets=[Systray()])], 10))
    ]

    manager_nospawn.start(config)

    topbar = manager_nospawn.c.bar["top"]
    assert len(topbar.info()["widgets"]) == 1

    manager_nospawn.c.reconfigure_screens()

    assert len(topbar.info()["widgets"]) == 1

    # Check that we've still got a Systray widget in the box.
    _, name = manager_nospawn.c.widget["widgetbox"].eval("self.widgets[0].name")
    assert name == "systray"


def test_deprecated_configuration(caplog):
    tray = Systray()
    box = WidgetBox([tray])
    assert box.widgets == [tray]
    assert "The use of a positional argument in WidgetBox is deprecated." in caplog.text
