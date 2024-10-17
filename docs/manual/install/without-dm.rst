====================
Running from systemd
====================

This case will cover automatic login to Qtile after booting the system without
using display manager. It logins in virtual console and init X by running
through session.

Automatic login to virtual console
----------------------------------

To get login into virtual console as an example edit `getty` service by running
`systemctl edit getty@tty1` and add instructions to
`/etc/systemd/system/getty@tty1.service.d/override.conf`::

    [Service]
    ExecStart=
    ExecStart=-/usr/bin/agetty --autologin username --noclear %I $TERM

`username` should be changed to current user name.

Check more for other `examples <https://wiki.archlinux.org/index.php/Getty#Automatic_login_to_virtual_console>`_.

Autostart X session
-------------------

After login X session should be started. That can be done by `.bash_profile` if
bash is used or `.zprofile` in case of zsh. Other shells can be adjusted by
given examples.

.. code-block:: bash

    if systemctl -q is-active graphical.target && [[ ! $DISPLAY && $XDG_VTNR -eq 1 ]]; then
      exec startx
    fi

And to start Qtile itself `.xinitrc` should be fixed:

::

    # some apps that should be started before Qtile, ex.
    #
    #   [[ -f ~/.Xresources ]] && xrdb -merge ~/.Xresources
    #   ~/.fehbg &
    #   nm-applet &
    #   blueman-applet &
    #   dunst &
    #
    # or
    #
    #   source ~/.xsession

    exec qtile start
