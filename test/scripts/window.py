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

import gi

gi.require_version('Gdk', '3.0')
gi.require_version('Gtk', '3.0')
from gi.repository import Gdk, Gtk

# GTK consumes the `--name <class>` args
if len(sys.argv) > 1:
    title = sys.argv[1]
else:
    title = "TestWindow"

if len(sys.argv) > 2:
    window_type = sys.argv[2]
else:
    window_type = "normal"

win = Gtk.Window(title=title)
win.connect("destroy", Gtk.main_quit)
win.connect("key-press-event", Gtk.main_quit)
win.set_default_size(100, 100)

if window_type == "notification":
    if os.environ["GDK_BACKEND"] == "wayland":
        try:
            gi.require_version('GtkLayerShell', '0.1')
            from gi.repository import GtkLayerShell
        except ValueError:
            sys.exit(1)
        win.add(Gtk.Label(label='This is a test notification'))
        GtkLayerShell.init_for_window(win)

    else:
        win.set_type_hint(Gdk.WindowTypeHint.NOTIFICATION)

elif window_type == "normal":
    win.set_type_hint(Gdk.WindowTypeHint.NORMAL)

win.show_all()
Gtk.main()
