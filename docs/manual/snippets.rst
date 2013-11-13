Snippets for the system
=======================

There are some suggested snippets for the system to make things be done easier.

Session menu with dmenu
-----------------------

This snippet creates nice dmenu at bottom with suggested actions for session.
It works with dmenu application, so it should be installed. Code was taken from 
https://bbs.archlinux.org/viewtopic.php?id=95984

Create runnable file ``/usr/local/bin/dmenu-session``. Change colors or prompt
to your needs.

.. code-block:: bash

    #!/bin/bash
    #
    # a simple dmenu session script 
    # from https://bbs.archlinux.org/viewtopic.php?id=95984
    #
    ###

    DMENU='dmenu -i -b -p >>> -nb #000 -nf #fff -sb #15181a -sf #fff'
    choice=$(echo -e "lock\nlogout\nshutdown\nreboot\nsuspend\nhibernate" | $DMENU)

    case "$choice" in
      lock) gnome-screensaver-command --lock ;;
      logout) gksu kill $(pgrep X) & ;;
      shutdown) gksu shutdown -h now & ;;
      reboot) gksu shutdown -r now & ;;
      suspend) gksu pm-suspend && gnome-screensaver-command --lock ;;
      hibernate) gksu pm-hibernate && gnome-screensaver-command --lock ;;
    esac

Change mod to 777 what it become executable

.. code-block:: bash

    chmod +x dmenu-session

Bind key to your newly created script in Qtile config.

.. code-block:: python

    <...>
    Key([mod, 'control'], 'q', lazy.spawn('dmenu-session')),
    <...>

What's it. Now after Qtile reload you should get nice menu at bottom.
