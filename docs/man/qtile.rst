PLACEHOLDER
-----------

SYNOPSIS
========

qtile [-c config] [-s qtilesocket] [-l DEBUG] [-n]

DESCRIPTION
===========

``qtile`` runs Qtile on the current $DISPLAY. Qtile is a tiling window manager
written in python. Complete configuration information is available online at
http://docs.qtile.org.

OPTIONS
=======
    -c config, --config config

        Use the specified config file.

    -s qtilesocket, --socket qtilesocket

        Use qtilesocket as the IPC server.

    -l DEBUG, --log-level DEBUG

        Set the default log level, one of DEBUG, INFO, WARNING, ERROR,
        CRITICAL.

FILES
=====

Qtile searches for configuration files in the following locations:

    #. The location specified by the ``-c`` option.
    #. ``$XDG_CONFIG_HOME/qtile/config.py``
    #. ``~/.config/qtile/config.py``
    #. The default configuration, distributed as the python module
       ``libqtile.resources.default_config``.

BUGS
====

Bugs can be reported to the issue tracker at http://github.com/qtile/qtile.
