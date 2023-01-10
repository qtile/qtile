.. _config-keys:

====
Keys
====

The ``keys`` variable defines Qtile's key bindings. 

Default Key Bindings
--------------------

The mod key for the default config is ``mod4``, which is typically bound to
the "Super" keys, which are things like the windows key and the mac command
key. The basic operation is:

* ``mod + k`` or ``mod + j``: switch windows on the current stack
* ``mod + <space>``: put focus on the other pane of the stack (when in stack
  layout)
* ``mod + <tab>``: switch layouts
* ``mod + w``: close window
* ``mod + <ctrl> + r``: reload the config
* ``mod + <group name>``: switch to that group
* ``mod + <shift> + <group name>``: send a window to that group
* ``mod + <enter>``: start terminal guessed by ``libqtile.utils.guess_terminal``
* ``mod + r``: start a little prompt in the bar so users can run arbitrary
  commands

The default config defines one screen and 8 groups, one for each letter in
``asdfuiop``. It has a basic bottom bar that includes a group box, the current
window name, a little text reminder that you're using the default config,
a system tray, and a clock.

The default configuration has several more advanced key combinations, but the
above should be enough for basic usage of qtile.

See :ref:`Keybindings in images <keybinding-img>` for visual
keybindings in keyboard layout.

Defining key bindings
---------------------

Individual key bindings are
defined with :class:`~libqtile.config.Key` as demonstrated in the following
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
:class:`~libqtile.config.EzKey` helper class. The following example is
functionally equivalent to the above::

    from libqtile.config import EzKey as Key

    keys = [
       Key("M-S-a", callback, ...),
       Key("C-p",   callback, ...),
       Key("M-A-<Tab>", callback, ...),
    ]

The :class:`~libqtile.config.EzKey` modifier keys (i.e. ``MASC``) can be
overwritten through the ``EzKey.modifier_keys`` dictionary. The defaults are::

    modifier_keys = {
       'M': 'mod4',
       'A': 'mod1',
       'S': 'shift',
       'C': 'control',
    }

Callbacks can also be configured to work only under certain conditions by using
the :meth:`~libqtile.lazy.LazyCall.when` method. Currently, the following
conditions are supported:

::  

    from libqtile.config import Key

    keys = [
        # Only trigger callback for a specific layout
        Key(
            [mod, 'shift'],
            "j",
            lazy.layout.grow().when(layout='verticaltile'),
            lazy.layout.grow_down().when(layout='columns')
        ),

        # Limit action to when the current window is not floating (default True)
        Key([mod], "f", lazy.window.toggle_fullscreen().when(when_floating=False))

        # Also matches are supported on the current window
        # For example to match on the wm_class for fullscreen do the following
        Key([mod], "f", lazy.window.toggle_fullscreen().when(focused=Match(wm_class="yourclasshere"))
    ]

KeyChords
=========

Qtile also allows sequences of keys to trigger callbacks. These sequences are
known as chords and are defined with :class:`~libqtile.config.KeyChord`. Chords
are added to the ``keys`` section of the config file.

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

Modes
-----

Chords can optionally persist until a user presses <escape>. This can be done
by setting ``mode=True``. This can be useful for configuring a
subset of commands for a particular situations (i.e. similar to vim modes).

::

    from libqtile.config import Key, KeyChord

    keys = [
        KeyChord([mod], "z", [
            Key([], "g", lazy.layout.grow()),
            Key([], "s", lazy.layout.shrink()),
            Key([], "n", lazy.layout.normalize()),
            Key([], "m", lazy.layout.maximize())],
            mode=True,
            name="Windows"
        )
    ]

In the above example, pressing Mod + z triggers the "Windows" mode. Users can
then resize windows by just pressing g (to grow the window), s to
shrink it etc. as many times as needed. To exit the mode, press <escape>.

.. note::
    The Chord widget (:class:`~libqtile.widget.Chord`) will display the name
    of the active chord (as set by the ``name`` parameter). This is particularly
    useful where the chord is a persistent mode as this will indicate when the
    chord's mode is still active.

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

Modes can also be added to chains if required. The following example
demonstrates the behaviour when using the ``mode`` argument in chains:

::

    from libqtile.config import Key, KeyChord

    keys = [
        KeyChord([mod], "z", [
            KeyChord([], "y", [
                KeyChord([], "x", [
                    Key([], "c", lazy.spawn("xterm"))
                ], mode=True, name="inner")
            ])
        ], mode=True, name="outer")
    ]

After pressing Mod+z y x c, the "inner" mode will remain active. When pressing
<escape>, the "inner" mode is exited. Since the mode in between does not have
``mode`` set, it is also left. Arriving at the "outer" mode (which has this
argument set) stops the "leave" action and "outer" now becomes the active mode.

.. note::
    If you want to bind a custom key to leave the current mode (e.g. Control +
    G in addition to ``<escape>``), you can specify ``lazy.ungrab_chord()``
    as the key action. To leave all modes and return to the root bindings, use
    ``lazy.ungrab_all_chords()``.

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
`the code <https://github.com/qtile/qtile/blob/master/libqtile/backend/x11/xkeysyms.py>`_.
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

.. qtile_class:: libqtile.config.EzKey
   :no-commands:
