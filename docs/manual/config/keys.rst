.. _config-keys:

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

KeyChords
=========

Qtile also allows sequences of keys to trigger callbacks. In Qtile, these
sequences are known as chords and are defined with
:class:`libqtile.config.KeyChord`. Chords are added to the ``keys`` section of
the config file.

::

    from libqtile.config import Key, KeyChord

    keys = [
        KeyChord([mod], "z", [
            Key([], "x", lazy.spawn("xterm"))
        ])
    ]

The above code will launch xterm when the user presses Mod + z, followed by x.

.. warning::
    Users should note that key chords are aborted by pressing <escape>. In the
    above example, if the user presses Mod + z, any following key presses will
    still be sent to the currently focussed window. If <escape> has not been
    pressed, the next press of x will launch xterm.

.. note::
    A chord can be named by specifying the name argument which is used by Chord
    widget (:class:`libqtile.widget.chord.Chord`) to display currently active
    chord on the bar.

.. note::
    When a chord is active, if you press keys that are not currently mapped in
    the chord, those keys will be sent to the window that is currently in focus.
    Set block_keyboard_on_active_chord to True in your config, to prevent
    sending keys to window in focus when a chord is active.

Modes
-----

Chords can optionally specify a "mode". When this is done, the mode will remain
active until the user presses <escape>. This can be useful for configuring a
subset of commands for a particular situations (i.e. similar to vim modes).

::

    from libqtile.config import Key, KeyChord

    keys = [
        KeyChord([mod], "z", [
            Key([], "g", lazy.layout.grow()),
            Key([], "s", lazy.layout.shrink()),
            Key([], "n", lazy.layout.normalize()),
            Key([], "m", lazy.layout.maximize())],
            mode="Windows"
        )
    ]

In the above example, pressing Mod + z triggers the "Windows" mode. Users can
then resize windows by just pressing g (to grow the window), s to
shrink it etc. as many times as needed. To exit the mode, press <escape>.

.. note::
    If using modes or naming chords, users may also wish to use the Chord widget
    (:class:`libqtile.widget.chord.Chord`) as this will display the name of the
    currently active chord on the bar.

Chains
------

Chords can also be chained to make even longer sequences.

::

    from libqtile.config import Key, KeyChord

    keys = [
        KeyChord([mod], "z", [
            KeyChord([], "x", [
                Key([], "c", lazy.spawn("xterm"))
            ])
        ])
    ]

Modes can also be added to chains if required.


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
`the code <https://github.com/qtile/qtile/blob/master/libqtile/xkeysyms.py>`_.
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

.. qtile_class:: libqtile.config.KeyChord
   :no-commands:

.. qtile_class:: libqtile.config.EzConfig
   :no-commands:
