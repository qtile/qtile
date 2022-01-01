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
It is dependet on your system configuration where to do this. e.g. ArchLinux with libreoffice-fresh in /etc/profile.d/libreoffice-fresh.sh.

How can I get my groups to stick to screens?
============================================

This behaviour can be replicated by configuring your keybindings to not move
groups between screens. For example if you want groups ``"1"``, ``"2"`` and
``"3"`` on one screen and ``"q"``, ``"w"``, and ``"e"`` on the other, instead
of binding keys to ``lazy.group[name].toscreen()``, use this:

.. code-block:: python

    def go_to_group(name: str) -> Callable:
        def _inner(qtile: Qtile) -> None:
            if len(qtile.screens) == 1:
                qtile.groups_map[name].cmd_toscreen()
                return

            if name in '123':
                qtile.focus_screen(0)
                qtile.groups_map[name].cmd_toscreen()
            else:
                qtile.focus_screen(1)
                qtile.groups_map[name].cmd_toscreen()

        return _inner

    for i in groups:
        keys.append(Key([mod], i.name, lazy.function(go_to_group(i.name))))

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
