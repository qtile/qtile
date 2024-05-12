=======
Screens
=======

The ``screens`` configuration variable is where the physical screens, their
associated ``bars``, and the ``widgets`` contained within the bars are defined
(see :ref:`ref-widgets` for a listing of available widgets). 

Example
=======

Tying together screens, bars and widgets, we get something like this:

::

    from libqtile.config import Screen
    from libqtile import bar, widget

    window_name = widget.WindowName()

    screens = [
        Screen(
            bottom=bar.Bar([
                widget.GroupBox(),
                window_name,
                ], 30),
            ),
        Screen(
            bottom=bar.Bar([
                widget.GroupBox(),
                window_name,
                ], 30),
            )
        ]

Note that a widget can be passed to multiple bars (and likewise multiple times
to the same bar). Its contents is mirrored across all copies so this is useful
where you want identical content (e.g. the name of the focussed window, like in
this example).

Bars support both solid background colors and gradients by supplying a list of
colors that make up a linear gradient. For example, :code:`bar.Bar(...,
background="#000000")` will give you a black back ground (the default), while
:code:`bar.Bar(..., background=["#000000", "#FFFFFF"])` will give you a
background that fades from black to white.

Bars (and widgets) also support transparency by adding an alpha value to the
desired color. For example, :code:`bar.Bar(..., background="#00000000")` will
result in a fully transparent bar. Widget contents will not be impacted i.e.
this is different to the ``opacity`` parameter which sets the transparency of the
entire window.

.. note::
    In X11 backends, transparency will be disabled in a bar if the ``background``
    color is fully opaque.

Users can add borders to the bar by using the ``border_width`` and
``border_color`` parameters. Providing a single value sets the value for all
four sides while sides can be customised individually by setting four values
in a list (top, right, bottom, left) e.g. ``border_width=[2, 0, 2, 0]`` would
draw a border 2 pixels thick on the top and bottom of the bar.


Multiple Screens
================

You will see from the example above that ``screens`` is a list of individual
``Screen`` objects. The order of the screens in this list should match the order
of screens as seen by your display server.

X11
~~~

You can view the current order of your screens by running ``xrandr --listmonitors``.

Examples of how to set the order of your screens can be found on the
`Arch wiki <https://wiki.archlinux.org/title/Multihead>`_.

Wayland
~~~~~~~

The Wayland backend supports the wlr-output-management protocol for configuration of
outputs by tools such as `Kanshi <https://github.com/emersion/kanshi>`_.

Fake Screens
============

instead of using the variable `screens` the variable `fake_screens` can be used to set split a physical monitor into multiple screens.
They can be used like this:

::

    from libqtile.config import Screen
    from libqtile import bar, widget

    # screens look like this
    #     600         300
    #  |-------------|-----|
    #  |          480|     |580
    #  |   A         |  B  |
    #  |----------|--|     |
    #  |       400|--|-----|
    #  |   C      |        |400
    #  |----------|   D    |
    #     500     |--------|
    #                 400
    #
    # Notice there is a hole in the middle
    # also D goes down below the others

    fake_screens = [
      Screen(
          bottom=bar.Bar(
              [
                  widget.Prompt(),
                  widget.Sep(),
                  widget.WindowName(),
                  widget.Sep(),
                  widget.Systray(),
                  widget.Sep(),
                  widget.Clock(format='%H:%M:%S %d.%m.%Y')
              ],
              24,
              background="#555555"
          ),
          x=0,
          y=0,
          width=600,
          height=480
      ),
      Screen(
          top=bar.Bar(
              [
                  widget.GroupBox(),
                  widget.WindowName(),
                  widget.Clock()
              ],
              30,
          ),
          x=600,
          y=0,
          width=300,
          height=580
      ),
      Screen(
          top=bar.Bar(
              [
                  widget.GroupBox(),
                  widget.WindowName(),
                  widget.Clock()
              ],
              30,
          ),
          x=0,
          y=480,
          width=500,
          height=400
      ),
      Screen(
          top=bar.Bar(
              [
                  widget.GroupBox(),
                  widget.WindowName(),
                  widget.Clock()
              ],
              30,
          ),
          x=500,
          y=580,
          width=400,
          height=400
      ),
    ]

Third-party bars
================

There might be some reasons to use third-party bars. For instance you can come
from another window manager and you have already configured dzen2, xmobar, or
something else. They definitely can be used with Qtile too. In fact, any
additional configurations aren't needed. Just run the bar and qtile will adapt.

Reference
=========

.. qtile_class:: libqtile.config.Screen

.. qtile_class:: libqtile.bar.Bar

.. qtile_class:: libqtile.bar.Gap
