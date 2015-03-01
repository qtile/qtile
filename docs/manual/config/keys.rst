====
Keys
====

The ``keys`` variable defines Qtile's key bindings. Individual key
bindings are defined with ``libqtile.config.Key`` as demonstrated in
the following example. Note that you may specify more than one
callback functions.

::

   from libqtile.config import Key

   keys = [
      # Pressing "Meta + Shift + a".
      Key(["mod4", "shift"], "a", callback, ...),

      # Pressing "Control + p".
      Key(["control"], "p", callback, ...),

      # Pressing "Meta + Tab".
      Key(["mod4", "mod1"], "Tab", callback, ...),
   ]

The above may also be written more concisely with the help of the
``EzKey`` helper class. The following example is functionally
equivalent to the above::

    from libqtile.config import EzKey as Key

    keys = [
       Key("M-S-a", callback, ...),
       Key("C-p",   callback, ...),
       Key("M-A-<Tab>", callback, ...),
    ]

The ``EzKey`` modifier keys (i.e. ``MASC``) can be overwritten through
the ``EzKey.modifier_keys`` dictionary. The defaults are::

    modifier_keys = {
       'M': 'mod4',
       'A': 'mod1',
       'S': 'shift',
       'C': 'control',
    }


The command.lazy object
=======================

``command.lazy`` is a special helper object to specify a command for later
execution. This object acts like the root of the object graph, which means that
we can specify a key binding command with the same syntax used to call the
command through a script or through :doc:`/manual/commands/qsh`.

Example
-------

::

    from libqtile.config import Key
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

On most systems ``mod1`` is the Alt key - you can see which modifiers, which are
enclosed in a list, map to which keys on your system by running the ``xmodmap``
command. This example binds ``Alt-k`` to the "down" command on the current
layout. This command is standard on all the included layouts, and switches to
the next window (where "next" is defined differently in different layouts). The
matching "up" command switches to the previous window.

Modifiers include: "shift", "lock", "control", "mod1", "mod2", "mod3", "mod4",
and "mod5". They can be used in combination by appending more than one modifier
to the list:

::

    Key(
        ["mod1", "control"], "k",
        lazy.layout.shuffle_down()
    )

Lazy functions
==============

This is overview of the commonly used functions for the key bindings.

General functions
-----------------

.. list-table::
    :widths: 20 80
    :header-rows: 1

    * - function
      - description
    * - ``lazy.spawn("application"))``
      - Run the ``application``
    * - ``lazy.spawncmd())``
      - Open command prompt on the bar. See prompt widget.
    * - ``lazy.restart())``
      - Restart Qtile and reload its config. It won't close your windows
    * - ``lazy.shutdown())``
      - Close the whole Qtile

Group functions
---------------

.. list-table::
    :widths: 20 80
    :header-rows: 1

    * - function
      - description
    * - ``lazy.nextlayout())``
      - Use next layout on the actual group
    * - ``lazy.prevlayout())``
      - Use previous layout on the actual group
    * - ``lazy.screen.nextgroup())``
      - Move to the group on the right
    * - ``lazy.screen.prevgroup())``
      - Move to the group on the left
    * - ``lazy.screen.togglegroup())``
      - Move to the last visited group
    * - ``lazy.group["group_name"].toscreen())``
      - Move to the group called ``group_name``
    * - ``lazy.layout.increase_ratio()``
      - Incrase the space for master window at the expense of slave windows
    * - ``lazy.layout.decrease_ratio()``
      - Decrease the space for master window in the advantage of slave windows

Window functions
----------------

.. list-table::
    :widths: 20 80
    :header-rows: 1

    * - function
      - description
    * - ``lazy.window.kill())``
      - Close the focused window
    * - ``lazy.layout.next())``
      - Switch window focus to other pane(s) of stack
    * - ``lazy.window.togroup("group_name")``
      - Move focused window to the group called ``group_name``
    * - ``lazy.window.toggle_floating()``
      - Put the focused window to/from floating mode
    * - ``lazy.window.toggle_fullscreen()``
      - Put the focused window to/from fullscreen mode


Special keys
------------

These are most commonly used special keys. For complete list please see
`the code <https://github.com/qtile/qtile/blob/develop/libqtile/xkeysyms.py>`_.
You can create bindings on them just like for the regular keys. For example
``Key(["mod1"], "F4", lazy.window.kill())``.

.. list-table::

    * - ``Return``
    * - ``BackSpace``
    * - ``Tab``
    * - ``space``
    * - ``Home``, ``End``
    * - ``Left``, ``Up``, ``Right``, ``Down``
    * - ``F1``, ``F2``, ``F3``, ...
    * -
    * - ``XF86AudioRaiseVolume``
    * - ``XF86AudioLowerVolume``
    * - ``XF86AudioMute``
    * - ``XF86AudioNext``
    * - ``XF86AudioPrev``
