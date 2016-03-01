====
Keys
====

The ``keys`` variable defines Qtile's key bindings. Individual key bindings are
defined with :class:`libqtile.config.Key` as demonstrated in the following
example. Note that you may specify more than one callback functions.

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
:class:`libqtile.config.EzKey` helper class. The following example is
functionally equivalent to the above::

    from libqtile.config import EzKey as Key

    keys = [
       Key("M-S-a", callback, ...),
       Key("C-p",   callback, ...),
       Key("M-A-<Tab>", callback, ...),
    ]

The :class:`EzKey` modifier keys (i.e. ``MASC``) can be overwritten through the
``EzKey.modifier_keys`` dictionary. The defaults are::

    modifier_keys = {
       'M': 'mod4',
       'A': 'mod1',
       'S': 'shift',
       'C': 'control',
    }

Modifiers
=========

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

Special keys
============

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
    * - ``XF86MonBrightnessUp``
    * - ``XF86MonBrightnessDown``

Reference
=========

.. qtile_class:: libqtile.config.Key
   :no-commands:

.. qtile_class:: libqtile.config.EzConfig
   :no-commands:
