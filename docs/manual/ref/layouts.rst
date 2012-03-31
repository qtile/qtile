Built-in Layouts
================


Floating
--------

Floating layout, which does nothing with windows but handles focus order

.. list-table::
    :widths: 20 20 60
    :header-rows: 1

    * - key
      - default
      - description
    * - border_focus
      - ``"#0000ff"``
      - Border colour for the focused window.
    * - border_normal
      - ``"#000000"``
      - Border colour for un-focused winows.
    * - border_width
      - ``1``
      - Border width.
    * - max_border_width
      - ``0``
      - Border width for maximize.
    * - fullscreen_border_width
      - ``0``
      - Border width for fullscreen.
    * - name
      - ``"floating"``
      - Name of this layout.
    * - auto_float_types
      - ``set(['notification', 'splash', 'toolbar', 'utility'])``
      - default wm types to automatically float


Max
---

A simple layout that only displays one window at a time, filling the
screen. This is suitable for use on laptops and other devices with
small screens. Conceptually, the windows are managed as a stack, with
commands to switch to next and previous windows in the stack.

.. list-table::
    :widths: 20 20 60
    :header-rows: 1

    * - key
      - default
      - description
    * - name
      - ``"max"``
      - Name of this layout.


MonadTall
---------

This layout attempts to emulate the behavior of XMonad's default
tiling scheme.

Main-Pane:

A main pane that contains a single window takes up a vertical
portion of the screen based on the ratio setting. This ratio can
be adjusted with the ``cmd_grow`` and ``cmd_shrink`` methods while
the main pane is in focus.

::

    ---------------------
    |            |      |
    |            |      |
    |            |      |
    |            |      |
    |            |      |
    |            |      |
    ---------------------

Using the ``cmd_flip`` method will switch which horizontal side the
main pane will occupy. The main pane is considered the "top" of
the stack.

::

    ---------------------
    |      |            |
    |      |            |
    |      |            |
    |      |            |
    |      |            |
    |      |            |
    ---------------------

Secondary-panes:

Occupying the rest of the screen are one or more secondary panes.
The secondary panes will share the vertical space of the screen
however they can be resized at will with the ``cmd_grow`` and
``cmd_shrink`` methods. The other secondary panes will adjust their
sizes to smoothly fill all of the space.

::

    ---------------------          ---------------------
    |            |      |          |            |______|
    |            |______|          |            |      |
    |            |      |          |            |      |
    |            |______|          |            |      |
    |            |      |          |            |______|
    |            |      |          |            |      |
    ---------------------          ---------------------

Panes can be moved with the ``cmd_shuffle_up`` and ``cmd_shuffle_down``
methods. As mentioned the main pane is considered the top of the
stack; moving up is counter-clockwise and moving down is clockwise.

The opposite is true if the layout is "flipped".

::

    ---------------------          ---------------------
    |            |  2   |          |   2   |           |
    |            |______|          |_______|           |
    |            |  3   |          |   3   |           |
    |     1      |______|          |_______|     1     |
    |            |  4   |          |   4   |           |
    |            |      |          |       |           |
    ---------------------          ---------------------


Normalizing:

To restore all client windows to their default size ratios simply
use the ``cmd_normalize`` method.


Maximizing:

To toggle a client window between its minimum and maximum sizes
simply use the ``cmd_maximize`` on a focused client.

Suggested Bindings:

::

    Key([modkey], "k", lazy.layout.down()),
    Key([modkey], "j", lazy.layout.up()),
    Key([modkey, "shift"], "k", lazy.layout.shuffle_down()),
    Key([modkey, "shift"], "j", lazy.layout.shuffle_up()),
    Key([modkey], "i", lazy.layout.grow()),
    Key([modkey], "m", lazy.layout.shrink()),
    Key([modkey], "n", lazy.layout.normalize()),
    Key([modkey], "o", lazy.layout.maximize()),
    Key([modkey, "shift"], "space", lazy.layout.flip()),



.. list-table::
    :widths: 20 20 60
    :header-rows: 1

    * - key
      - default
      - description
    * - border_focus
      - ``"#ff0000"``
      - Border colour for the focused window.
    * - border_normal
      - ``"#000000"``
      - Border colour for un-focused winows.
    * - border_width
      - ``2``
      - Border width.


RatioTile
---------

Tries to tile all windows in the width/height ratio passed in

.. list-table::
    :widths: 20 20 60
    :header-rows: 1

    * - key
      - default
      - description
    * - border_focus
      - ``"#0000ff"``
      - Border colour for the focused window.
    * - border_normal
      - ``"#000000"``
      - Border colour for un-focused winows.
    * - border_width
      - ``1``
      - Border width.
    * - name
      - ``"ratiotile"``
      - Name of this layout.


Slice
-----

This layout cuts piece of screen and places a single window on that piece,
and delegates other window placement to other layout

.. list-table::
    :widths: 20 20 60
    :header-rows: 1

    * - key
      - default
      - description
    * - width
      - ``256``
      - Slice width
    * - side
      - ``"left"``
      - Side of the slice (left, right, top, bottom)
    * - name
      - ``"max"``
      - Name of this layout.


Stack
-----

The stack layout divides the screen horizontally into a set of stacks.
Commands allow you to switch between stacks, to next and previous
windows within a stack, and to split a stack to show all windows in the
stack, or unsplit it to show only the current window. At the moment,
this is the most mature and flexible layout in Qtile.

.. list-table::
    :widths: 20 20 60
    :header-rows: 1

    * - key
      - default
      - description
    * - border_focus
      - ``"#0000ff"``
      - Border colour for the focused window.
    * - border_normal
      - ``"#000000"``
      - Border colour for un-focused winows.
    * - border_width
      - ``1``
      - Border width.
    * - name
      - ``"stack"``
      - Name of this layout.


Tile
----

<missing doc string>

.. list-table::
    :widths: 20 20 60
    :header-rows: 1

    * - key
      - default
      - description
    * - border_focus
      - ``"#0000ff"``
      - Border colour for the focused window.
    * - border_normal
      - ``"#000000"``
      - Border colour for un-focused winows.
    * - border_width
      - ``1``
      - Border width.
    * - name
      - ``"tile"``
      - Name of this layout.


TreeTab
-------

This layout works just like Max but displays tree of the windows at the
left border of the screen, which allows you to overview all opened windows.
It's designed to work with ``uzbl-browser`` but works with other windows
too.

.. list-table::
    :widths: 20 20 60
    :header-rows: 1

    * - key
      - default
      - description
    * - bg_color
      - ``"000000"``
      - Background color of tabs
    * - active_bg
      - ``"000080"``
      - Background color of active tab
    * - active_fg
      - ``"ffffff"``
      - Foreground color of active tab
    * - inactive_bg
      - ``"606060"``
      - Background color of inactive tab
    * - inactive_fg
      - ``"ffffff"``
      - Foreground color of inactive tab
    * - margin_left
      - ``6``
      - Left margin of tab panel
    * - margin_y
      - ``6``
      - Vertical margin of tab panel
    * - padding_left
      - ``6``
      - Left padding for tabs
    * - padding_x
      - ``6``
      - Left padding for tab label
    * - padding_y
      - ``2``
      - Top padding for tab label
    * - border_width
      - ``2``
      - Width of the border
    * - vspace
      - ``2``
      - Space between tabs
    * - level_shift
      - ``8``
      - Shift for children tabs
    * - font
      - ``"Arial"``
      - Font
    * - fontsize
      - ``14``
      - Font pixel size.
    * - section_fontsize
      - ``11``
      - Font pixel size of section label
    * - section_fg
      - ``"ffffff"``
      - Color of section label
    * - section_top
      - ``4``
      - Top margin of section label
    * - section_bottom
      - ``6``
      - Bottom margin of section
    * - section_padding
      - ``4``
      - Bottom of magin section label
    * - section_left
      - ``4``
      - Left margin of section label
    * - panel_width
      - ``150``
      - Width of the left panel
    * - sections
      - ``['Default']``
      - Foreground color of inactive tab
    * - name
      - ``"max"``
      - Name of this layout.


Zoomy
-----

A layout with single active windows, and few other previews at the
right

.. list-table::
    :widths: 20 20 60
    :header-rows: 1

    * - key
      - default
      - description
    * - columnwidth
      - ``150``
      - Width of the right column
    * - property_name
      - ``"ZOOM"``
      - Property to set on zoomed window
    * - property_small
      - ``0.1``
      - Property value to set on zoomed window
    * - property_big
      - ``1.0``
      - Property value to set on normal window
