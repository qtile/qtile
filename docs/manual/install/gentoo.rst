==========================
Installing on Gentoo Linux
==========================

The newest version of Qtile is not available in the official Gentoo
portage tree. But you can use an unofficial `portage overlay`_ to
install newer versions of Qtile.

Installing using portage
========================

Currently `x11-wm/qtile-0.8.0`_ is available. Installing is as easy
as:

.. code-block:: bash

    emerge qtile

You can read more about the portage tree in the `Gentoo Handbook`_.

Installing Qtile 0.9.1
======================

Qtile 0.9.1 can be installed using the unofficial `fillips
overlay`_. The excellent tool `layman`_ comes in handy when managing
overlays. Something around these lines is needed to install Qtile:

.. code-block:: bash

    layman -f -o http://github.com/buzz/fillips-overlay/raw/master/fillips.xml -a fillips
    emerge qtile

This will automatically install the dependencies xcffib-0.1.11 and
trollius-1.0.4 which are also provided by this overlay as they are not
available in the portage tree yet.

For an introduction how to work with overlays in Gentoo have a look at
the following guide:

http://wiki.gentoo.org/wiki/Project:Overlays/User_Guide

.. _x11-wm/qtile-0.8.0: http://packages.gentoo.org/package/x11-wm/qtile
.. _Gentoo Handbook: http://wiki.gentoo.org/wiki/Handbook:X86/Working/Portage
.. _portage overlay: http://wiki.gentoo.org/wiki/Overlay
.. _layman: http://wiki.gentoo.org/wiki/Layman
.. _fillips overlay: https://github.com/buzz/fillips-overlay
