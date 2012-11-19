Mouse
=====

The ``mouse`` config file variable defines a set of
global mouse actions, and is a list of ``Click`` and
``Drag`` objects, which define what to do when a window
is clicked or dragged.

Example
~~~~~~~

::

    from libqtile.manager import Click, Drag
    mouse = [
        Drag([mod], "Button1", lazy.window.set_position_floating(),
            start=lazy.window.get_position()),
        Drag([mod], "Button3", lazy.window.set_size_floating(),
            start=lazy.window.get_size()),
        Click([mod], "Button2", lazy.window.bring_to_front())
    ]
