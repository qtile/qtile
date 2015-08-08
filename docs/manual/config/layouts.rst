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

Qtile uses python's inbuilt object serialization (pickle) for restarts.
For custom layouts it is required that if you have unpickelable objects
within your layout, then you have to add an exception for your layout
in state.py. You will have to manually restore those specific attributes in
state.py. Some examples of unpickelable objects within qtile are a delegate
layout, a window object, a group object etc. For window objects, the current
procedure handles most of the trivial cases. However it is possible that your
layout might need some special handling. For details on how to restore
them manually for restart to work, see state.py.

See :doc:`/manual/ref/layouts` for a listing of available layouts.


Example
=======

::

    from libqtile import layout
    layouts = [
        layout.Max(),
        layout.Stack(stacks=2)
    ]
