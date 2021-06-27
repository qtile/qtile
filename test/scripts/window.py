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

import os

# Disable GTK ATK bridge, which appears to trigger errors with e.g. test_strut_handling
# https://wiki.gnome.org/Accessibility/Documentation/GNOME2/Mechanics
os.environ["NO_AT_BRIDGE"] = "1"

import sys

import gi

gi.require_version('Gdk', '3.0')
gi.require_version('Gtk', '3.0')
from gi.repository import Gdk, Gtk

# GTK consumes the `--name <class>` args
title = sys.argv[1]
window_type = sys.argv[2]

win = Gtk.Window(title=title)
win.connect("destroy", Gtk.main_quit)
win.connect("key-press-event", Gtk.main_quit)
win.set_default_size(100, 100)

if window_type == "notification":
    win.set_type_hint(Gdk.WindowTypeHint.NOTIFICATION)
elif window_type == "normal":
    win.set_type_hint(Gdk.WindowTypeHint.NORMAL)

win.show()
Gtk.main()
