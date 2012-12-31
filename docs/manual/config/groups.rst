Groups
======

A group is a container for a bunch of windows,
analogous to workspaces in other window managers. Each
client window managed by the window manager belongs to
exactly one group. The ``groups`` config file variable
should be initialized to a list of ``DGroup`` objects.

``DGroup`` objects provide several options for group configuration. Groups can
be configured to show and hide themselves when they're not empty, spawn
applications for them when they start, automatically acquire certain groups,
and various other options.

.. autoclass:: libqtile.config.Match
    :members: __init__

.. autoclass:: libqtile.config.Group
    :members: __init__

.. autofunction:: libqtile.dgroups.simple_key_binder

Example
~~~~~~~

::

    from libqtile.config import Group, Match
    groups = [
        Group("a"),
        Group("b"),
        Group("c", match=Match(title=["Firefox"])),
    ]

    # allow mod3+1 through mod3+0 to bind to groups; if you bind your groups
    # by hand in your config, you don't need to do this.
    from libqtile.dgroups simple_key_binder
    dgroups_key_binder = simple_key_binder("mod3")

