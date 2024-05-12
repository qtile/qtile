Window objects
==============

The size and position of windows is determined by the current layout. Nevertheless,
windows can still change their appearance in multiple ways (toggling floating state,
fullscreen, opacity).

Windows can access objects relevant to the display of the window (i.e.
the screen, group and layout).

.. qtile_graph::
    :root: window

|

.. qtile_commands:: libqtile.backend.base
    :baseclass: libqtile.backend.base.Window
    :object-node: window
    :includebase:
    :no-title: