# Running Qtile as a Wayland Compositor

Some functionality may not yet be implemented in the Wayland compositor.
Please see the [Wayland To Do List](https://github.com/qtile/qtile/discussions/2409)
discussion for the current state of development.
Also checkout the [unresolved Wayland-specific issues](https://github.com/qtile/qtile/issues?q=is%3Aissue+is%3Aopen+label%3A%22core%3A+wayland%22)
and [troubleshooting][debugging-wayland] for tips on how to debug Wayland
problems.

NOTE: We currently support wlroots>=0.16.0,<0.17.0 and pywlroots==0.16.4.

## Backend-Specific Configuration

If you want your config file to work with different backends but want some
options set differently per backend, you can check the name of the current
backend in your config as follows:

```python
from libqtile import qtile

if qtile.core.name == "x11":
    term = "urxvt"
elif qtile.core.name == "wayland":
    term = "foot"
```

## Running X11-Only Programs

Qtile supports XWayland but requires that `wlroots` and `pywlroots` were built
with XWayland support, and that XWayland is installed on the system from
startup. XWayland will be started the first time it is needed.

### XWayland windows sometimes don't receive mouse events

There is currently a known bug (https://github.com/qtile/qtile/issues/3675)
which causes pointer events (hover/click/scroll) to propagate to the wrong window when switching focus.

## Input Device Configuration

.. qtile_class:: libqtile.backend.wayland.InputConfig

If you want to change keyboard configuration during runtime, you can use the
core's `set_keymap` command (see below).

## Core Commands

See the [Wayland backend commands][wayland_backend_commands] section in the API Commands documentation.
