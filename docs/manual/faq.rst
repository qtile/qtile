==========================
Frequently Asked Questions
==========================

Why the name Qtile?
===================

Users often wonder, why the Q? Does it have something to do with Qt? No. Below
is an IRC excerpt where cortesi explains the great trial that ultimately
brought Qtile into existence, thanks to the benevolence of the Open Source
Gods. Praise be to the OSG!

::

    ramnes:  what does Qtile mean?
    ramnes:  what's the Q?
    @tych0:  ramnes: it doesn't :)
    @tych0:  cortesi was just looking for the first letter that wasn't registered
             in a domain name with "tile" as a suffix
    @tych0:  qtile it was :)
    cortesi: tych0, dx: we really should have something more compelling to
             explain the name. one day i was swimming at manly beach in sydney,
             where i lived at the time. suddenly, i saw an enormous great white
             right beside me. it went for my leg with massive, gaping jaws, but
             quick as a flash, i thumb-punched it in both eyes. when it reared
             back in agony, i saw that it had a jagged, gnarly scar on its
             stomach... a scar shaped like the letter "Q".
    cortesi: while it was distracted, i surfed a wave to shore. i knew that i
             had to dedicate my next open source project to the ocean gods, in
             thanks for my lucky escape. and thus, qtile got its name...

When I first start xterm/urxvt/rxvt containing an instance of Vim, I see text and layout corruption. What gives?
================================================================================================================

Vim is not handling terminal resizes correctly. You can fix the problem by
starting your xterm with the "-wf" option, like so:

.. code-block:: bash

    xterm -wf -e vim

Alternatively, you can just cycle through your layouts a few times, which
usually seems to fix it.

How do I know which modifier specification maps to which key?
=============================================================

To see a list of modifier names and their matching keys, use the ``xmodmap``
command. On my system, the output looks like this:

.. code-block:: bash

    $ xmodmap
    xmodmap:  up to 3 keys per modifier, (keycodes in parentheses):

    shift       Shift_L (0x32),  Shift_R (0x3e)
    lock        Caps_Lock (0x9)
    control     Control_L (0x25),  Control_R (0x69)
    mod1        Alt_L (0x40),  Alt_R (0x6c),  Meta_L (0xcd)
    mod2        Num_Lock (0x4d)
    mod3
    mod4        Super_L (0xce),  Hyper_L (0xcf)
    mod5        ISO_Level3_Shift (0x5c),  Mode_switch (0xcb)

My "pointer mouse cursor" isn't the one I expect it to be!
==========================================================

Qtile should set the default cursor to left_ptr, you must install xcb-util-cursor if you want support for themed cursors.

LibreOffice menus don't appear or don't stay visible
====================================================

A workaround for problem with the mouse in libreoffice is setting the environment variable »SAL_USE_VCLPLUGIN=gen«.
It is dependent on your system configuration as to where to do this. e.g. ArchLinux with libreoffice-fresh in /etc/profile.d/libreoffice-fresh.sh.

How can I get my groups to stick to screens?
============================================

This behaviour can be replicated by configuring your keybindings to not move
groups between screens. For example if you want groups ``"1"``, ``"2"`` and
``"3"`` on one screen and ``"q"``, ``"w"``, and ``"e"`` on the other, instead
of binding keys to ``lazy.group[name].toscreen()``, use this:

.. code-block:: python

    groups = [
        # Screen affinity here is used to make
        # sure the groups startup on the right screens
        Group(name="1", screen_affinity=0),
        Group(name="2", screen_affinity=0),
        Group(name="3", screen_affinity=0),
        Group(name="q", screen_affinity=1),
        Group(name="w", screen_affinity=1),
        Group(name="e", screen_affinity=1),
    ]

    def go_to_group(name: str):
        def _inner(qtile):
            if len(qtile.screens) == 1:
                qtile.groups_map[name].toscreen()
                return

            if name in '123':
                qtile.focus_screen(0)
                qtile.groups_map[name].toscreen()
            else:
                qtile.focus_screen(1)
                qtile.groups_map[name].toscreen()

        return _inner

    for i in groups:
        keys.append(Key([mod], i.name, lazy.function(go_to_group(i.name))))

To be able to move windows across these groups while switching groups, a similar function can be used:

.. code-block:: python

    def go_to_group_and_move_window(name: str):
        def _inner(qtile):
            if len(qtile.screens) == 1:
                qtile.current_window.togroup(name, switch_group=True)
                return

            if name in "123":
                qtile.current_window.togroup(name, switch_group=False)
                qtile.focus_screen(0)
                qtile.groups_map[name].toscreen()
            else:
                qtile.current_window.togroup(name, switch_group=False)
                qtile.focus_screen(1)
                qtile.groups_map[name].toscreen()

        return _inner

    for i in groups:
        keys.append(Key([mod, "shift"], i.name, lazy.function(go_to_group_and_move_window(i.name))))

If you use the ``GroupBox`` widget you can make it reflect this behaviour:

.. code-block:: python

    groupbox1 = widget.GroupBox(visible_groups=['1', '2', '3'])
    groupbox2 = widget.GroupBox(visible_groups=['q', 'w', 'e'])

And if you jump between having single and double screens then modifying the
visible groups on the fly may be useful:

.. code-block:: python

   @hook.subscribe.screens_reconfigured
   async def _():
       if len(qtile.screens) > 1:
           groupbox1.visible_groups = ['1', '2', '3']
       else:
           groupbox1.visible_groups = ['1', '2', '3', 'q', 'w', 'e']
       if hasattr(groupbox1, 'bar'):
           groupbox1.bar.draw()

Where can I find example configurations and other scripts?
==========================================================

Please visit our `qtile-examples`_ repo which contains examples of users' configurations,
scripts and other useful links.

.. _`qtile-examples`: https://github.com/qtile/qtile-examples

Where are the log files for Qtile?
==================================

The log files for qtile are at ``~/.local/share/qtile/qtile.log``.

How can I match the bar with picom?
===================================

You can use ``"QTILE_INTERNAL:32c = 1"`` in your picom.conf to match the bar.
This will match all internal Qtile windows, so if you want to avoid that or to
target bars individually, you can set a custom property and match that:

.. code-block:: python

   mybar = Bar(...)

   @hook.subscribe.startup
   def _():
       mybar.window.window.set_property("QTILE_BAR", 1, "CARDINAL", 32)

This would enable matching on ``mybar``'s window using ``"QTILE_BAR:32c = 1"``.
See `2526`_ and `1515`_ for more discussion.

.. _`2526`: https://github.com/qtile/qtile/issues/2526
.. _`1515`: https://github.com/qtile/qtile/issues/1515

Why do get a warning that fonts cannot be loaded?
=================================================

When installing Qtile on a new system, when running the test suite
or the Xephyr script (``./scripts/xephyr``),
you might see errors in the output like the following or similar:

* Xephyr script::

    xterm: cannot load font "-Misc-Fixed-medium-R-*-*-13-120-75-75-C-120-ISO10646-1"
    xterm: cannot load font "-misc-fixed-medium-r-semicondensed--13-120-75-75-c-60-iso10646-1"

* ``pytest``::

    ---------- Captured stderr call ----------
    Warning: Cannot convert string "8x13" to type FontStruct
    Warning: Unable to load any usable ISO8859 font
    Warning: Unable to load any usable ISO8859 font
    Error: Aborting: no font found

    -------- Captured stderr teardown --------
    Qtile exited with exitcode: -9

If it happens, it might be because you're missing fonts on your system.

On ArchLinux, you can fix this by installing ``xorg-fonts-misc``::

    sudo pacman -S xorg-fonts-misc

Try to search for "xorg fonts misc" with your distribution name on the internet
to find how to install them.

I've upgraded and Qtile's broken. What do I do?
===============================================

If you've recently upgraded, the first thing to do is check the :doc:`changelog </manual/changelog>`
and see if any breaking changes were made.

Next, check your log file (see above) to see if any error messages explain what the problem is.

If you're still stuck, come and ask for help on Discord, IRC or GitHub.
