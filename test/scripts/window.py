#!/usr/bin/env python3
"""
This creates a minimal window using GTK that works the same in both X11 or Wayland.

GTK sets the window class via `--name <class>`, and then we manually set the window
title and type. Therefore this is intended to be called as:

    python window.py --name <class> <title> <type>

where <type> is "normal" or "notification"

The window will close itself if it receives any key or button press events.
"""
# flake8: noqa

# This is needed otherwise the window will use any Wayland session it can find even if
# WAYLAND_DISPLAY is not set.
import os

if os.environ.get("WAYLAND_DISPLAY"):
    os.environ["GDK_BACKEND"] = "wayland"
else:
    os.environ["GDK_BACKEND"] = "x11"

# Disable GTK ATK bridge, which appears to trigger errors with e.g. test_strut_handling
# https://wiki.gnome.org/Accessibility/Documentation/GNOME2/Mechanics
os.environ["NO_AT_BRIDGE"] = "1"

import sys
from pathlib import Path

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from dbus_next import Message
from dbus_next.constants import MessageType, PropertyAccess
from dbus_next.glib import MessageBus
from dbus_next.service import ServiceInterface, dbus_property, method, signal
from gi.repository import Gdk, Gtk

ICON = Path(__file__).parent / "qtile_icon.rgba"


class SNItem(ServiceInterface):
    """
    Simplified StatusNotifierItem interface.

    Only exports methods, properties and signals required by
    StatusNotifier widget.
    """

    def __init__(self, window, *args):
        ServiceInterface.__init__(self, *args)
        self.window = window
        self.fullscreen = False

        with open(ICON, "rb") as f:
            self.icon = f.read()

        arr = bytearray(self.icon)
        for i in range(0, len(arr), 4):
            r, g, b, a = arr[i : i + 4]
            arr[i] = a
            arr[i + 1 : i + 4] = bytearray([r, g, b])

        self.icon = bytes(arr)

    @method()
    def Activate(self, x: "i", y: "i"):
        if self.fullscreen:
            self.window.unfullscreen()
        else:
            self.window.fullscreen()

        self.fullscreen = not self.fullscreen

    @dbus_property(PropertyAccess.READ)
    def IconName(self) -> "s":
        return ""

    @dbus_property(PropertyAccess.READ)
    def IconPixmap(self) -> "a(iiay)":
        return [[32, 32, self.icon]]

    @dbus_property(PropertyAccess.READ)
    def AttentionIconPixmap(self) -> "a(iiay)":
        return []

    @dbus_property(PropertyAccess.READ)
    def OverlayIconPixmap(self) -> "a(iiay)":
        return []

    @signal()
    def NewIcon(self):
        pass

    @signal()
    def NewAttentionIcon(self):
        pass

    @signal()
    def NewOverlayIcon(self):
        pass


if __name__ == "__main__":

    # GTK consumes the `--name <class>` args
    if len(sys.argv) > 1:
        title = sys.argv[1]
    else:
        title = "TestWindow"

    if len(sys.argv) > 2:
        window_type = sys.argv[2]
    else:
        window_type = "normal"

    # Check if we want to export a StatusNotifierItem interface
    sni = "export_sni_interface" in sys.argv

    win = Gtk.Window(title=title)
    win.connect("destroy", Gtk.main_quit)
    win.connect("key-press-event", Gtk.main_quit)
    win.set_default_size(100, 100)

    if window_type == "notification":
        if os.environ["GDK_BACKEND"] == "wayland":
            try:
                gi.require_version("GtkLayerShell", "0.1")
                from gi.repository import GtkLayerShell
            except ValueError:
                sys.exit(1)
            win.add(Gtk.Label(label="This is a test notification"))
            GtkLayerShell.init_for_window(win)

        else:
            win.set_type_hint(Gdk.WindowTypeHint.NOTIFICATION)

    elif window_type == "normal":
        win.set_type_hint(Gdk.WindowTypeHint.NORMAL)

    if sni:
        bus = MessageBus().connect_sync()

        item = SNItem(win, "org.kde.StatusNotifierItem")

        # Export interfaces on the bus
        bus.export("/StatusNotifierItem", item)

        # Request the service name
        bus.request_name_sync(f"test.qtile.window-{title.replace(' ','-')}")

        msg = bus.call_sync(
            Message(
                message_type=MessageType.METHOD_CALL,
                destination="org.freedesktop.StatusNotifierWatcher",
                interface="org.freedesktop.StatusNotifierWatcher",
                path="/StatusNotifierWatcher",
                member="RegisterStatusNotifierItem",
                signature="s",
                body=[bus.unique_name],
            )
        )

    win.show_all()
    Gtk.main()
