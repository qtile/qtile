=====================================
Running Qtile as a Wayland Compositor
=====================================

.. _wayland:

Some functionality may not yet be implemented in the Wayland compositor. Please
see the discussion `here <https://github.com/qtile/qtile/discussions/2409>`__ to
see the current state of development. See `here
<https://github.com/qtile/qtile/labels/Wayland>`__ for unresolved
Wayland-specific issues and see :ref:`troubleshooting <debugging-wayland>` for
tips on how to debug Wayland problems.

.. note::
   The currently supported wlroots and pylwroots versions are 0.15.x.

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
