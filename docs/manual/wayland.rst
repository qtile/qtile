=====================================
Running Qtile as a Wayland Compositor
=====================================

.. _wayland:

Some functionality may not yet be implemented in the Wayland compositor.
Please see the `Wayland GitHub Project Board <https://github.com/
orgs/qtile/projects/2>`__ for the current state of development. Also
checkout the `unresolved Wayland-specific issues <https://github.com/
qtile/qtile/issues?q=is%3Aissue+is%3Aopen+label%3A%22core%3A+wayland%22>`__
and :ref:`troubleshooting <debugging-wayland>` for tips on how to debug Wayland
problems.

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

Qtile supports XWayland but requires that `wlroots` were built
with XWayland support, and that XWayland is installed on the system from
startup. XWayland will be started the first time it is needed.

XWayland windows sometimes don't receive mouse events
-----------------------------------------------------

There is currently a known bug (https://github.com/qtile/qtile/issues/3675) which causes pointer events (hover/click/scroll) to propagate to the wrong window when switching focus.

Animations
==========

The Wayland backend supports animations for various window events. These can
be configured globally or individually for different types of events.

Configuration Options
---------------------

The following options control the duration (in milliseconds) and easing
functions used for animations:

- ``wl_default_duration`` (default: ``200``)
- ``wl_default_ease`` (default: ``"out_cubic"``)
- ``wl_spawn_duration`` (default: ``200``)
- ``wl_spawn_ease`` (default: ``"out_cubic"``)
- ``wl_kill_duration`` (default: ``200``)
- ``wl_kill_ease`` (default: ``"out_cubic"``)
- ``wl_slide_group_duration`` (default: ``200``)
- ``wl_slide_group_ease`` (default: ``"out_cubic"``)
- ``wl_dropdown_duration`` (default: ``200``)
- ``wl_dropdown_ease`` (default: ``"out_cubic"``)

Easing Functions
----------------

Available easing functions include the following types, which can be prefixed
with ``in_``, ``out_``, or ``in_out_``:

- ``sine``
- ``cubic``
- ``quint``
- ``circ``
- ``elastic``
- ``quad``
- ``quart``
- ``expo``
- ``back``
- ``bounce``

Example Usage
-------------

.. code-block:: python

   # In your config.py
   wl_default_duration = 300
   wl_default_ease = "out_quint"

   # Specifically override group switching animation
   wl_slide_group_duration = 400
   wl_slide_group_ease = "in_out_sine"

Input Device Configuration
==========================

.. qtile_class:: libqtile.backend.wayland.InputConfig

If you want to change keyboard configuration during runtime, you can use the
core's `set_keymap` command (see below).

Core Commands
=============

See the :ref:`wayland_backend_commands` section in the API Commands documentation.
