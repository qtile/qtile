====================
Installing on Ubuntu
====================

A Python 3 version of qtile is currently available as a deb_ for Debian sid,
and can be installed from the ``python3-qtile`` package.

There are no upstream Ubuntu packages for currently released versions of
qtile. However, on wily and above (and debian unstable), the dependencies
are available via:

.. code-block:: bash

    sudo apt-get install python3-xcffib python3-cairocffi

And with those, qtile can be built via a normal ``python setup.py install``.

.. _deb: https://packages.debian.org/sid/qtile

PPA on Launchpad
================

Packages for old versions are available for 11.10 (Oneiric Ocelot), 12.04
(Precise Pangolin), 12.10 (Quantal Quetzal), 13.04 (Raring Ringtail), 13.10
(Saucy Salamander), 14.04 (Trusty Tahr), and 14.10 (Utopic Unicorn).

.. code-block:: bash

    sudo apt-add-repository ppa:tycho-s/ppa
    sudo apt-get update
    sudo apt-get install qtile
