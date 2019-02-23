=======
Screens
=======

The ``screens`` configuration variable is where the physical screens, their
associated ``bars``, and the ``widgets`` contained within the bars are defined.

See :doc:`/manual/ref/widgets` for a listing of available widgets.

Example
=======

Tying together screens, bars and widgets, we get something like this:

::

    from liblavinder.config import Screen
    from liblavinder import bar, widget

    screens = [
        Screen(
            bottom=bar.Bar([
                widget.GroupBox(),
                widget.WindowName()
                ], 30),
            ),
        Screen(
            bottom=bar.Bar([
                widget.GroupBox(),
                widget.WindowName()
                ], 30),
            )
        ]

Bars support both solid background colors and gradients by supplying a list of
colors that make up a linear gradient. For example, :code:`bar.Bar(...,
background="#000000")` will give you a black back ground (the default), while
:code:`bar.Bar(..., background=["#000000", "#FFFFFF"])` will give you a
background that fades from black to white.

Fake Screens
============

instead of using the variable `screens` the variable `fake_screens` can be used to set split a physical monitor into multiple screens.
They can be used like this:

::

    from liblavinder.config import Screen
    from liblavinder import bar, widget

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
additional configurations aren't needed. Just run the bar and lavinder will adapt.

Reference
=========

.. lavinder_class:: liblavinder.config.Screen
   :no-commands:

.. lavinder_class:: liblavinder.bar.Bar
   :no-commands:

.. lavinder_class:: liblavinder.bar.Gap
   :no-commands:
