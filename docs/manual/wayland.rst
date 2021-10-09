=====================================
Running Qtile as a Wayland Compositor
=====================================

.. _wayland:


Some functionality may not yet be implemented in the Wayland compositor. Please
see the discussion `here <https://github.com/qtile/qtile/discussions/2409>`_ to
see the current state of development.

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


Keyboard Configuration
======================

Keyboard management is done using `xkbcommon
<https://github.com/xkbcommon/libxkbcommon>`_ via the `Python bindings
<https://github.com/sde1000/python-xkbcommon>`_. xkbcommon's initial
configuration can be set using environmental variables; see `their docs
<https://xkbcommon.org/doc/current/group__context.html>`_ for more information.
The 5 ``XKB_DEFAULT_X`` environmental variables have corresponding settings in
X11's keyboard configuration, so if you have these defined already simply copy
their values into these variables, otherwise see `X11's helpful XKB guide
<https://www.x.org/releases/X11R7.5/doc/input/XKB-Config.html>`_ to see the
syntax for these settings. Simply set these variables before starting Qtile and
the initial keyboard state will match these settings.

If you want to change keyboard configuration during runtime, you can use the
core's `set_keymap` command (see :ref:`wayland-cmds` below).


Running X11-Only Programs
=========================

Qtile does not support XWayland directly and there are no plans to implement
XWayland support. Instead, the recommended way to run any programs that do not
support Wayland themselves is to run them inside the `cage
<https://github.com/Hjdskes/cage>`_ Wayland compositor, which will contain the
program inside a window that does support XWayland. Otherwise, you could find
alternatives that support Wayland directly.


.. _wayland-cmds:

Core Commands
=============

.. qtile_class:: libqtile.backend.wayland.core.Core
