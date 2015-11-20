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

    from libqtile.config import Screen
    from libqtile import bar, widget

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

Bars support background colors and gradients, e.g. :code:`bar.Bar(...,
background="#000000")` will give you a black back ground (the default), while
:code:`bar.Bar(..., background=["#000000", "#FFFFFF"])` will give you a
background that fades from black to white.

Third-party bars
================

There might be some reasons to use third-party bars. For instance you can come
from another window manager and you have already configured dzen2, xmobar, or
something else. They definitely can be used with Qtile too. In fact, any
additional configurations aren't needed. Just run the bar and qtile will adapt.
