====================
Installing on Funtoo
====================

Latest versions of Qtile are available on Funtoo with Python 2.7, 3.3, and 3.4
implementations. To install it, run:

.. code-block:: bash

    emerge -av x11-wm/qtile

You can also install the development version from GitHub:

.. code-blocks:: bash

    echo "x11-wm/qtile-9999 **" >> /etc/portage/package.accept_keywords
    emerge -av qtile

Customize
=========

You can customize your installation with the following useflags:

- dbus
- widget-google-calendar
- widget-imap
- widget-keyboardkbdd
- widget-launchbar
- widget-mpd
- widget-mpris
- widget-wlan

The dbus useflag is enabled by default. Disable it only if you know what it is
and know you don't use/need it.

All widget-* useflags are disabled by default because these widgets require
additional dependencies while not everyone will use them. Enable only widgets
you need to avoid extra dependencies thanks to these useflags.

Visit `Funtoo Qtile documentation`_ for more details on Qtile installation on
Funtoo.

.. _Funtoo Qtile documentation: http://www.funtoo.org/Package:Qtile
