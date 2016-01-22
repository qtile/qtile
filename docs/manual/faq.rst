==========================
Frequently Asked Questions
==========================

Why the name Qtile?
===================

Users often wonder, why the Q? Does it have something to do with Qt? No. Below
is an IRC excerpt where cortesi explains the great trial that ultimately
brought Qtile into existance, thanks to the benevolence of the Open Source
Gods. Praise be to the OSG!

::

    ramnes:  what does Qtile mean?
    ramnes:  what's the Q?
    @tych0:  ramnes: it doesn't :)
    @tych0:  cortesi was just looking for the first letter that wasn't registerd
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
