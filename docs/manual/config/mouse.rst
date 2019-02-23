=====
Mouse
=====

The ``mouse`` config file variable defines a set of global mouse actions, and
is a list of :class:`~liblavinder.config.Click` and :class:`~liblavinder.config.Drag`
objects, which define what to do when a window is clicked or dragged.

Example
=======

::

    from liblavinder.config import Click, Drag
    mouse = [
        Drag([mod], "Button1", lazy.window.set_position_floating(),
            start=lazy.window.get_position()),
        Drag([mod], "Button3", lazy.window.set_size_floating(),
            start=lazy.window.get_size()),
        Click([mod], "Button2", lazy.window.bring_to_front())
    ]

The above example can also be written more concisely with the help of
the ``EzClick`` and ``EzDrag`` helpers::

    from liblavinder.config import EzClick as Click, EzDrag as Drag

    mouse = [
        Drag("M-1", lazy.window.set_position_floating(),
            start=lazy.window.get_position()),
        Drag("M-3", lazy.window.set_size_floating(),
            start=lazy.window.get_size()),
        Click("M-2", lazy.window.bring_to_front())
    ]

Reference
=========

.. lavinder_class:: liblavinder.config.Click
   :no-commands:

.. lavinder_class:: liblavinder.config.Drag
   :no-commands:
