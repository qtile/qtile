Frequently Asked Questions
==========================

When I first start xterm/urxvt/rxvt containing an instance of Vim, I see text and layout corruption. What gives?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Vim is not handling terminal resizes correctly. You can fix the problem by
starting your xterm with the "-wf" option, like so:

.. code-block:: bash

    xterm -wf -e vim

Alternatively, you can just cycle through your layouts a few times, which
usually seems to fix it.


How do I know which modifier specification maps to which key?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Append the following to your ``~/.config/qtile/config.py`` file:

.. code-block:: python

    @hook.subscribe.startup
    def runner():
        import subprocess
        subprocess.Popen(['xsetroot', '-cursor_name', 'left_ptr'])

This will change your pointer cursor to the standard "Left Pointer" cursor you chose in your ``~/.Xresources`` file on Qtile startup.
