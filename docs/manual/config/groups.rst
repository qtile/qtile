Groups
======

The ``groups`` config file variable should be initialized to a list of Group
objects.

$!confobj("libqtile.manager.Group")!$


Example
~~~~~~~

::

    from libqtile.manager import Group
    groups = [
        Group("a"),
        Group("b"),
        Group("c"),
    ]
