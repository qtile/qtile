==========
Scratchpad
==========

By the use of the :mod:`~libqtile.scratchpad` module it is possible to define
some simple scratchpad like behaviour, in your config.py file.
Instantiate a :class:`~libqtile.scratchpad.DropDown` and define a command to
execute and bind the `toggle` property (which returns a `lazy.function`)
to a `Key` in ``keys`` for example:

.. code-block:: python

    from libqtile import scratchpad
   
    dropdown_terminal = scratchpad.DropDown('xterm')
   
    keys = [ Key( [], 'F12', dropdown_terminal.toggle), ]

The above example creates a DropDown object whose visibility is toggled by
pressing F12 key. If the DropDown is set to visible the first time, it spawns
a process by the defined command (here: xterm). The visibility of the
corresponding window can afterwards be toggled by the same key.

The DropDown appears always on the current screen if toggled to visible,
regardless in what group it was before. The DropDown can also be configured t
to vanish if another window is focused.
The position and opacity of the corresponding window can be configured as argument
to __init__, and the window is always placed accordingly.

Note that the DropDown window is always shown as floating window and that the
window is detached from the DropDown if floating state is toggled.
In that case the next key press spawns a new process.

Example
=======

.. code-block:: python

	# create the DropDown object in config.py
	# x, y, w and h are given in fractions of the screen
    logviewer = scratchpad.DropDown(
        "urxvt -hold -name qtile.log "
        "-e tail -f -n 30 ~/.local/share/qtile/qtile.log",
        x=0.05, y=0.4, width=0.9, height=0.6, opacity=0.88,
        on_focus_lost_hide=True)

Reference
=========

.. qtile_class:: libqtile.scratchpad.DropDown
   :no-commands:  