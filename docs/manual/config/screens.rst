Screens
=======

The ``screens`` configuration variable is where the physical screens, their
associated ``bars``, and the ``widgets`` contained within the bars are defined.



Please see :doc:`Widgets Reference </manual/ref/widgets>` for a listing
of built-in widgets.


Example
-------

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
