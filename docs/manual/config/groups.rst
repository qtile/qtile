Groups
======

A group is a container for a bunch of windows,
analogous to workspaces in other window managers. Each
client window managed by the window manager belongs to
exactly one group. The ``groups`` config file variable
should be initialized to a list of Group objects.

Example
~~~~~~~

::

    from libqtile.manager import Group
    groups = [
        Group("a"),
        Group("b"),
        Group("c"),
    ]
