=====
Mouse
=====

The ``mouse`` config file variable defines a set of global mouse actions, and
is a list of :class:`~libqtile.config.Click` and :class:`~libqtile.config.Drag`
objects, which define what to do when a window is clicked or dragged.

Default Mouse Bindings
----------------------

By default, holding your ``mod`` key and left-clicking (and holding) a window will
allow you to drag it around as a floating window. Holding your ``mod`` key and right-clicking
(and holding) a window will resize the window (and also make it float if it is not already floating).

Example
=======

::

    from libqtile.config import Click, Drag
    mouse = [
        Drag([mod], "Button1", lazy.window.set_position_floating(),
            start=lazy.window.get_position()),
        Drag([mod], "Button3", lazy.window.set_size_floating(),
            start=lazy.window.get_size()),
        Click([mod], "Button2", lazy.window.bring_to_front())
    ]

The above example can also be written more concisely with the help of
the ``EzClick`` and ``EzDrag`` helpers::

    from libqtile.config import EzClick as Click, EzDrag as Drag

    mouse = [
        Drag("M-1", lazy.window.set_position_floating(),
            start=lazy.window.get_position()),
        Drag("M-3", lazy.window.set_size_floating(),
            start=lazy.window.get_size()),
        Click("M-2", lazy.window.bring_to_front())
    ]

Reference
=========

.. qtile_class:: libqtile.config.Click
   :no-commands:

.. qtile_class:: libqtile.config.Drag
   :no-commands:

.. qtile_class:: libqtile.config.EzClick
   :no-commands:
