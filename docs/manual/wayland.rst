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
The Wayland backend supports animations for various window events, configured
via the ``wl_animation`` option in your config.

Configuration
-------------
Set ``wl_animation`` to a :class:`~libqtile.config.WaylandAnimations` object to configure
animations, or ``None`` to disable all animations entirely.

:class:`~libqtile.config.WaylandAnimations` accepts the following fields, each taking an
:class:`~libqtile.config.Animation` object with ``duration`` (ms) and ``ease`` parameters:

- ``slide`` — group switching animations
- ``spawn`` — window spawn/move/resize animations
- ``kill`` — window kill animations
- ``dropdown`` — scratchpad (dropdown) animations
- ``default`` — fallback for any unspecified animation type

All fields default to ``Animation(duration=200, ease="out_cubic")``.

Easing Functions
----------------
Available easing functions, each can be prefixed with ``in_``, ``out_``, or ``in_out_``:

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

   from libqtile.config import Animation, WaylandAnimations

   # Use defaults (200ms, out_cubic) for everything
   wl_animation = WaylandAnimations()

   # Customize individual animation types
   wl_animation = WaylandAnimations(
       default=Animation(duration=300, ease="out_quint"),
       slide=Animation(duration=400, ease="in_out_sine"),
       spawn=Animation(duration=150, ease="out_quart"),
   )

   # Disable all animations
   wl_animation = None

Input Device Configuration
==========================

.. qtile_class:: libqtile.backend.wayland.InputConfig

If you want to change keyboard configuration during runtime, you can use the
core's `set_keymap` command (see below).

Core Commands
=============

See the :ref:`wayland_backend_commands` section in the API Commands documentation.
