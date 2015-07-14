====================
Installing on Funtoo
====================

Latest versions of Qtile are available on Funtoo with python 2.7, 3.3 and 3.4 implementations. To install it, run:

.. code-block:: bash

    emerge -av qtile

Customize
=========

You can customize your installation with the following useflags:

- `dbus`_
- `widget-google-calendar`_
- `widget-imap`_
- `widget-keyboardkbdd`_
- `widget-launchbar`_
- `widget-mpd`_
- `widget-mpris`_
- `widget-wlan`_

The `dbus`_ useflag is enabled by default. Disable it only if you know what it is and know you don't use/need it.

All `widget-*`_ useflags are disabled by default because these widgets require additional dependencies while not anyone will use them. Enable only widgets you need to avoid extra dependencies thanks to these useflags.
