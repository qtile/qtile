=====================================
Running Qtile as a Wayland Compositor
=====================================

.. _wayland:

Some functionality may not yet be implemented in the Wayland compositor.
Please see the `Wayland To Do List <https://github.com/qtile/qtile/
discussions/2409>`__ discussion for the current state of development.  Also
checkout the `unresolved Wayland-specific issues <https://github.com/
qtile/qtile/issues?q=is%3Aissue+is%3Aopen+label%3A%22core%3A+wayland%22>`__
and :ref:`troubleshooting <debugging-wayland>` for tips on how to debug Wayland
problems.

.. note::
   We currently support wlroots>=0.16.0,<0.17.0 and pywlroots==0.16.4.

Backend-Specific Configuration
==============================

If you want your config file to work with different backends but want some
options set differently per backend, you can check the name of the current
backend in your config as follows:

.. code-block:: python

   from libqtile import qtile

   if qtile.core.name == "x11":
       term = "urxvt"
   elif qtile.core.name == "wayland":
       term = "foot"

Running X11-Only Programs
=========================

Qtile supports XWayland but requires that `wlroots` and `pywlroots` were built
with XWayland support, and that XWayland is installed on the system from
startup. XWayland will be started the first time it is needed.

XWayland windows sometimes don't receive mouse events
-----------------------------------------------------

There is currently a known bug (https://github.com/qtile/qtile/issues/3675) which causes pointer events (hover/click/scroll) to propagate to the wrong window when switching focus.

Input Device Configuration
==========================

.. qtile_class:: libqtile.backend.wayland.InputConfig

If you want to change keyboard configuration during runtime, you can use the
core's `set_keymap` command (see below).

Core Commands
=============

See the :ref:`wayland_backend_commands` section in the API Commands documentation.

Autostarting apps on startup
============================

Wayland doesn't have equivalent of `.xinitrc` file, so one have to use Qtile's native of doing that. You can put this in your `config.py` to achieve

.. code-block:: python
    from libqtile import hook
    import subprocess
    import os

    @hook.subscribe.startup_once
    def autostart():
        home = os.path.expanduser("~")
        subprocess.run(home + "/.config/qtile/autostart.sh")

GTK settings aren't applied
===========================

GTK have a known issue of not recognizing setted variables. You can fix this by saving below code into a script in your script directory. Then you can just put the name of the script into your autostarting script.

.. note::
    Please do not forget to place your directory into a PATH and make the script executable

.. code-block:: sh
    #!/bin/sh

    # usage: import-gsettings
    config="${XDG_CONFIG_HOME:-$HOME/.config}/gtk-3.0/settings.ini"
    if [ ! -f "$config" ]; then exit 1; fi

    gnome_schema="org.gnome.desktop.interface"
    gtk_theme="$(grep 'gtk-theme-name' "$config" | sed 's/.*\s*=\s*//')"
    icon_theme="$(grep 'gtk-icon-theme-name' "$config" | sed 's/.*\s*=\s*//')"
    cursor_theme="$(grep 'gtk-cursor-theme-name' "$config" | sed 's/.*\s*=\s*//')"
    font_name="$(grep 'gtk-font-name' "$config" | sed 's/.*\s*=\s*//')"
    gsettings set "$gnome_schema" gtk-theme "$gtk_theme"
    gsettings set "$gnome_schema" icon-theme "$icon_theme"
    gsettings set "$gnome_schema" cursor-theme "$cursor_theme"
    gsettings set "$gnome_schema" font-name "$font_name"

Gamma adjustment tool
=====================

Redshift doesn't work for Wayland, but there are alternatives like: `gammastep <https://gitlab.com/chinstrap/gammastep>`, `wlsunset <https://git.sr.ht/~kennylevinsen/wlsunset>`, `wl-gammarelay <https://github.com/jeremija/wl-gammarelay>` and `wl-gammarelay-rs <https://github.com/MaxVerevkin/wl-gammarelay-rs>`.

Screenshots
===========

As `scrot <https://github.com/dreamer/scrot>` and other similiar X11 tools doesn't work for wayland, one may be interested in: `grim <https://git.sr.ht/~emersion/grim>`/`slurp <https://github.com/emersion/slurp>`, `shotman <https://git.sr.ht/~whynothugo/shotman>`, `flameshot <https://flameshot.org/>` or `swappy <https://github.com/jtheoof/swappy>`.

Screen sharing
==============

Here is a write up on how to get screen sharing enabled in Wayland:

To get screen sharing working on Qtile Wayland, make sure `xdg-desktop-portal`, `xdg-desktop-portal-gtk`, `xdg-desktop-portal-wlr`, `python-dbus-next`, and `wlroots` are installed on your system and add the following lines to your `config.py`:

.. code-block:: python
    import os  
    from libqtile import qtile   
    if qtile.core.name == "wayland":  
        os.environ["XDG_SESSION_DESKTOP"] = "qtile:wlroots"
        os.environ["XDG_CURRENT_DESKTOP"] = "qtile:wlroots"

And add this to your autostart script:

.. code-block:: sh
    dbus-update-activation-environment --systemd WAYLAND_DISPLAY XDG_CURRENT_DESKTOP &
