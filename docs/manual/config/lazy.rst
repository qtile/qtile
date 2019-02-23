============
Lazy objects
============

The ``command.lazy`` object is a special helper object to specify a command for
later execution. This object acts like the root of the object graph, which
means that we can specify a key binding command with the same syntax used to
call the command through a script or through :doc:`/manual/commands/qshell`.

Example
-------

::

    from liblavinder.config import Key
    from liblavinder.command import lazy

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

Lazy functions
==============

This is overview of the commonly used functions for the key bindings.  These
functions can be called from commands on the :ref:`lavinder_commands` object or on
another object in the command tree.

Some examples are given below.

General functions
-----------------

.. list-table::
    :widths: 20 80
    :header-rows: 1

    * - function
      - description
    * - ``lazy.spawn("application")``
      - Run the ``application``
    * - ``lazy.spawncmd()``
      - Open command prompt on the bar. See prompt widget.
    * - ``lazy.restart()``
      - Restart Qtile and reload its config. It won't close your windows
    * - ``lazy.shutdown()``
      - Close the whole Qtile

Group functions
---------------

.. list-table::
    :widths: 20 80
    :header-rows: 1

    * - function
      - description
    * - ``lazy.next_layout()``
      - Use next layout on the actual group
    * - ``lazy.prev_layout()``
      - Use previous layout on the actual group
    * - ``lazy.screen.next_group()``
      - Move to the group on the right
    * - ``lazy.screen.prev_group()``
      - Move to the group on the left
    * - ``lazy.screen.toggle_group()``
      - Move to the last visited group
    * - ``lazy.group["group_name"].toscreen()``
      - Move to the group called ``group_name``
    * - ``lazy.layout.increase_ratio()``
      - Increase the space for master window at the expense of slave windows
    * - ``lazy.layout.decrease_ratio()``
      - Decrease the space for master window in the advantage of slave windows

Window functions
----------------

.. list-table::
    :widths: 20 80
    :header-rows: 1

    * - function
      - description
    * - ``lazy.window.kill()``
      - Close the focused window
    * - ``lazy.layout.next()``
      - Switch window focus to other pane(s) of stack
    * - ``lazy.window.togroup("group_name")``
      - Move focused window to the group called ``group_name``
    * - ``lazy.window.toggle_floating()``
      - Put the focused window to/from floating mode
    * - ``lazy.window.toggle_fullscreen()``
      - Put the focused window to/from fullscreen mode

ScratchPad DropDown functions
-----------------------------

.. list-table::
    :widths: 20 80
    :header-rows: 1

    * - function
      - description
    * - ``lazy.group["group_name"].dropdown_toggle("name")``
      - Toggles the visibility of the specified DropDown window.
        On first use, the configured process is spawned.
