Keys
====

The ``keys`` variable defines Qtile's key bindings.

$!confobj("libqtile.manager.Key")!$

The command.lazy object
~~~~~~~~~~~~~~~~~~~~~~~

``command.lazy`` is a special helper object to specify a command for later
execution. This object acts like the root of the object graph, which means that
we can specify a key binding command with the same syntax used to call the
command through a script or through :doc:`/manual/commands/qsh`.


Example
~~~~~~~

::

    from libqtile.manager import Key
    from libqtile.command import lazy
    keys = [
        Key(
            ["mod1"], "k",
            lazy.layout.down()
        ),
        Key(
            ["mod1"], "j",
            lazy.layout.up()
        )
    ]

On my system ``mod1`` is the Alt key - you can see which modifiers map to which
keys on your system by running the ``xmodmap`` command. This example binds
``Alt-k`` to the "down" command on the current layout. This command is standard
on all the included layouts, and switches to the next window (where "next" is
defined differently in different layouts). The matching "up" command switches
to the previous window.
