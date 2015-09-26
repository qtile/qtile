=======
Layouts
=======

A layout is an algorithm for laying out windows in a group on your screen.
Since Qtile is a tiling window manager, this usually means that we try to use
space as efficiently as possible, and give the user ample commands that can be
bound to keys to interact with layouts.

The ``layouts`` variable defines the list of layouts you will use with Qtile.
The first layout in the list is the default. If you define more than one
layout, you will probably also want to define key bindings to let you switch to
the next and previous layouts.

See :doc:`/manual/ref/layouts` for a listing of available layouts.


Example
=======

::

    from libqtile import layout
    layouts = [
        layout.Max(),
        layout.Stack(stacks=2)
    ]
