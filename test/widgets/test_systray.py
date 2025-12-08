import sys
from pathlib import Path

import pytest

import libqtile.bar
import libqtile.config
from libqtile import widget
from test.helpers import Retry


def test_no_duplicates_multiple_instances(manager_nospawn, minimal_conf_noscreen, backend_name):
    """Check only one instance of Systray widget."""
    if backend_name == "wayland":
        pytest.skip("Skipping test on Wayland.")

    assert not widget.Systray._instances
    config = minimal_conf_noscreen
    config.screens = [
        libqtile.config.Screen(top=libqtile.bar.Bar([widget.Systray(), widget.Systray()], 10))
    ]

    manager_nospawn.start(config)

    widgets = manager_nospawn.c.bar["top"].info()["widgets"]
    assert len(widgets) == 2
    assert widgets[1]["name"] == "configerrorwidget"


def test_no_duplicates_mirror(manager_nospawn, minimal_conf_noscreen, backend_name):
    """Check systray is not mirrored."""
    if backend_name == "wayland":
        pytest.skip("Skipping test on Wayland.")

    assert not widget.Systray._instances
    systray = widget.Systray()
    config = minimal_conf_noscreen
    config.fake_screens = [
        libqtile.config.Screen(
            top=libqtile.bar.Bar([systray], 10),
            x=0,
            y=0,
            width=300,
            height=300,
        ),
        libqtile.config.Screen(
            top=libqtile.bar.Bar([systray], 10),
            x=0,
            y=300,
            width=300,
            height=300,
        ),
    ]

    manager_nospawn.start(config)

    # Second screen has tried to mirror the Systray instance
    widgets = manager_nospawn.c.screen[1].bar["top"].info()["widgets"]
    assert len(widgets) == 1
    assert widgets[0]["name"] == "configerrorwidget"


def test_systray_reconfigure_screens(manager_nospawn, minimal_conf_noscreen, backend_name):
    """Check systray does not crash when reconfiguring screens."""
    if backend_name == "wayland":
        pytest.skip("Skipping test on Wayland.")

    assert not widget.Systray._instances
    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(top=libqtile.bar.Bar([widget.Systray()], 10))]

    manager_nospawn.start(config)

    assert manager_nospawn.c.bar["top"].info()["widgets"][0]["name"] == "systray"

    manager_nospawn.c.reconfigure_screens()

    assert manager_nospawn.c.bar["top"].info()["widgets"][0]["name"] == "systray"


def test_systray_icons(manager_nospawn, minimal_conf_noscreen, backend_name):
    """Check icons are placed correctly."""

    @Retry(ignore_exceptions=(AssertionError))
    def wait_for_icons():
        assert int(manager_nospawn.c.widget["systray"].eval("len(self.tray_icons)")) == 2

    if backend_name == "wayland":
        pytest.skip("Skipping test on Wayland.")

    script = Path(__file__).parent.parent / "scripts" / "systray.py"

    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(top=libqtile.bar.Bar([widget.Systray()], 40))]

    manager_nospawn.start(config)

    # No icons at this stage so length is 0
    assert manager_nospawn.c.widget["systray"].info()["widget"]["length"] == 0

    manager_nospawn.c.spawn(f"{sys.executable} {script.as_posix()} --name qtile")
    manager_nospawn.c.spawn(f"{sys.executable} {script.as_posix()} --name systray")

    wait_for_icons()

    # We now have two icons so widget should expand to leave space in bar for icons
    assert manager_nospawn.c.widget["systray"].info()["widget"]["length"] > 0

    # Check positioning of icon
    x = manager_nospawn.c.widget["systray"].eval("self.tray_icons[0].x")
    y = manager_nospawn.c.widget["systray"].eval("self.tray_icons[0].y")

    # Positions are relative to bar
    assert (int(x), int(y)) == (3, 10)

    # Icons should be in alphabetical order
    order = manager_nospawn.c.widget["systray"].eval("[i.name for i in self.tray_icons]")

    assert order == "['qtile', 'systray']"
