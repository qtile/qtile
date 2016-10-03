=======================
Installing on Slackware
=======================

Qtile is available on the `SlackBuilds.org <https://slackbuilds.org/repository/14.2/desktop/qtile/>`_ as:

======================= =======================
Package Name            Description
======================= =======================
qtile                   stable branch (release)
======================= =======================

Using slpkg (third party package manager)
=========================================

The easy way to install Qtile is with `slpkg <https://github.com/dslackw/slpkg>`_. For example:

.. code-block:: bash

    slpkg -s sbo qtile

Manual installation
===================

Download dependencies first and install them.
The order in which you need to install is:

- pycparser
- cffi
- six
- futures
- python-xcffib
- trollius
- cairocffi
- qtile


Please see the HOWTO for more information on `SlackBuild Usage HOWTO <https://slackbuilds.org/howto/>`_.
