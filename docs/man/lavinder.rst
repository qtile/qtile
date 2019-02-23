PLACEHOLDER
-----------

SYNOPSIS
========

lavinder [-c config] [-s lavindersocket] [-l DEBUG] [-n]

DESCRIPTION
===========

``lavinder`` runs Qtile on the current $DISPLAY. Qtile is a tiling window manager
written in python. Complete configuration information is available online at
http://docs.lavinder.org.

OPTIONS
=======
    -c config, --config config

        Use the specified config file.

    -s lavindersocket, --socket lavindersocket

        Use lavindersocket as the IPC server.

    -l DEBUG, --log-level DEBUG

        Set the default log level, one of DEBUG, INFO, WARNING, ERROR,
        CRITICAL.

FILES
=====

Qtile searches for configuration files in the following locations:

    #. The location specified by the ``-c`` option.
    #. ``$XDG_CONFIG_HOME/lavinder/config.py``
    #. ``~/.config/lavinder/config.py``
    #. The default configuration, distributed as the python module
       ``liblavinder.resources.default_config``.

BUGS
====

Bugs can be reported to the issue tracker at http://github.com/lavinder/lavinder.
