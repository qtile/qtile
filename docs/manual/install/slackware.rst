=======================
Installing on Slackware
=======================

Qtile is available on the `SlackBuilds.org <https://slackbuilds.org/repository/14.2/desktop/lavinder/>`_ as:

======================= =======================
Package Name            Description
======================= =======================
lavinder                   stable branch (release)
======================= =======================

Using slpkg (third party package manager)
=========================================

The easy way to install Qtile is with `slpkg <https://github.com/dslackw/slpkg>`_. For example:

.. code-block:: bash

    slpkg -s sbo lavinder

Manual installation
===================

Download dependencies first and install them.
The order in which you need to install is:

- pycparser
- cffi
- futures
- python-xcffib
- trollius
- cairocffi
- lavinder


Please see the HOWTO for more information on `SlackBuild Usage HOWTO <https://slackbuilds.org/howto/>`_.
