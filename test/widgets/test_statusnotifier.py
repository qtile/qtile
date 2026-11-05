import asyncio

import pytest
from dbus_fast import PropertyAccess
from dbus_fast.aio import MessageBus
from dbus_fast.introspection import Node
from dbus_fast.service import ServiceInterface, dbus_property

import libqtile.bar
import libqtile.config
import libqtile.confreader
import libqtile.layout
import libqtile.widget
from libqtile.widget.helpers.status_notifier.statusnotifier import StatusNotifierItem
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
    manager_nospawn.c.bar["top"].fake_button_press(10, 0, 1)
    check_fullscreen(windows, True)

    # Left click again will restore window
    manager_nospawn.c.bar["top"].fake_button_press(10, 0, 1)
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
    manager_nospawn.c.bar["left"].fake_button_press(0, 10, 1)
    check_fullscreen(windows, True)

    # Left click again will restore window
    manager_nospawn.c.bar["left"].fake_button_press(0, 10, 1)
    check_fullscreen(windows, False)

    manager_nospawn.kill_window(win)
    assert not windows()


class PixmapOnlyItem(ServiceInterface):
    """StatusNotifierItem providing just an icon pixmap, as Electron apps do."""

    def __init__(self):
        super().__init__("org.kde.StatusNotifierItem")

    @dbus_property(PropertyAccess.READ)
    def IconPixmap(self) -> "a(iiay)":  # type: ignore  # noqa: F722, F821, N802
        return [[1, 1, bytes(4)]]


class NoIntrospectionBus(MessageBus):
    """Bus whose introspection finds no interfaces, as with Electron apps."""

    async def introspect(self, bus_name, path, *args, **kwargs):
        return Node(path)


@pytest.mark.usefixtures("dbus")
def test_statusnotifier_item_without_introspection():
    """
    Items registered on a custom path that don't support introspection
    (e.g. Electron apps) should be read from that path.
    """

    async def run():
        path = "/org/chromium/StatusNotifierItem/1"
        app_bus = await MessageBus().connect()
        app_bus.export(path, PixmapOnlyItem())
        host_bus = await NoIntrospectionBus().connect()
        item = StatusNotifierItem(host_bus, app_bus.unique_name, path)
        try:
            assert await item.start()
            assert item._pixmaps.get("Icon")
        finally:
            host_bus.disconnect()
            app_bus.disconnect()

    asyncio.run(run())
