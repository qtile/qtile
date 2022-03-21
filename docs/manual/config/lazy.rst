.. _lazy:

============
Lazy objects
============

The ``lazy.lazy`` object is a special helper object to specify a command for
later execution. This object acts like the root of the object graph, which
means that we can specify a key binding command with the same syntax used to
call the command through a script or through :ref:`qtile-shell`.

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

Lazy functions
==============

This is overview of the commonly used functions for the key bindings.  These
functions can be called from commands on the :ref:`qtile_commands` object or on
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
    * - ``lazy.reload_config()``
      - Reload the config.
    * - ``lazy.restart()``
      - Restart Qtile. In X11, it won't close your windows.
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
    * - ``lazy.group.next_window()``
      - Switch window focus to next window in group
    * - ``lazy.group.prev_window()``
      - Switch window focus to previous window in group
    * - ``lazy.group["group_name"].toscreen()``
      - Move to the group called ``group_name``.
        Takes an optional ``toggle`` parameter (defaults to False).
        If this group is already on the screen, it does nothing by default;
        to toggle with the last used group instead, use ``toggle=True``.
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

Screen functions
----------------

.. list-table::
    :widths: 20 80
    :header-rows: 1

    * - function
      - description
    * - ``lazy.screen.set_wallpaper(path, mode=None)``
      - Set the wallpaper to the specificied image. Possible modes: ``None`` no resizing,
        ``'fill'`` centre and resize to fill screen, ``'stretch'`` stretch to fill screen.

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
    * - ``lazy.group["group_name"].hide_all()``
      - Hides all DropDown windows.
    * - ``lazy.group["group_name"].dropdown_reconfigure("name", **configuration)``
      - Update the configuration of the named DropDown.

User-defined functions
----------------------

.. list-table::
    :widths: 20 80
    :header-rows: 1

    * - function
      - description
    * - ``lazy.function(func, *args, **kwargs)``
      - Calls ``func(qtile, *args, **kwargs)``. NB. the ``qtile`` object is
        automatically passed as the first argument.

Examples
--------

``lazy.function`` can also be used as a decorator for functions.

::

    from libqtile.config import Key
    from libqtile.command import lazy

    @lazy.function
    def my_function(qtile):
        ...

    keys = [
        Key(
            ["mod1"], "k",
            my_function
        )
    ]

Additionally, you can pass arguments to user-defined function in one of two ways:

1) In-line definition

Arguments can be added to the ``lazy.function`` call.

::

    from libqtile.config import Key
    from libqtile.command import lazy
    from libqtile.log_utils import logger

    def multiply(qtile, value, multiplier=10):
        logger.warning(f"Multiplication results: {value * multiplier}")

    keys = [
        Key(
            ["mod1"], "k",
            lazy.function(multiply, 10, multiplier=2)
        )
    ]

2) Decorator

Arguments can also be passed to the decorated function.

::

    from libqtile.config import Key
    from libqtile.command import lazy
    from libqtile.log_utils import logger

    @lazy.function
    def multiply(qtile, value, multiplier=10):
        logger.warning(f"Multiplication results: {value * multiplier}")

    keys = [
        Key(
            ["mod1"], "k",
            multiply(10, multiplier=2)
        )
    ]
