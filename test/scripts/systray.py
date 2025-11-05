#!/usr/bin/env python3
"""
This creates a minimal system tray icon using GTK.

GTK sets the systray class via `--name <class>` like:

    python systray.py --name <class>

The window will close itself when clicked.
"""
# flake8: noqa

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

systray = Gtk.StatusIcon()
systray.connect("activate", Gtk.main_quit)

Gtk.main()
