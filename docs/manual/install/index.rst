================
Installing Qtile
================

Distro Guides
=============

Below are the preferred installation methods for specific distros. If you are
running something else, please see `Installing From Source`_.

.. toctree::
    :maxdepth: 1

    Arch <arch>
    Fedora <fedora>
    Funtoo <funtoo>
    Ubuntu <ubuntu>

Installing From Source
======================

First, you need to install all of Qtile's dependencies (although some are
optional/not needed depending on your python version, as noted below).

xcffib
------

Qtile uses xcffib_ as an XCB binding, which has its own instructions for
building from source. However, if you'd like to skip building it, you can
install its dependencies (``sudo apt-get install libxcb-render0-dev`` on
Ubuntu), and install it via pypi:

.. code-block:: bash

    pip install xcffib

.. _xcffib: https://github.com/tych0/xcffib#installation

cairocffi
---------

Qtile uses cairocffi_ with XCB support via xcffib. You'll need ``libcairo2``,
the underlying library used by the binding. Once you've got that installed, you
can use the latest version on pypi:

.. code-block:: bash

    pip install cairocffi

.. _cairocffi: https://pythonhosted.org/cairocffi/overview.html

pangocairo
----------

You'll also need ``libpangocairo``, which on Ubuntu can be installed via ``sudo
apt-get install libpangocairo-1.0-0``. Qtile uses this to provide text
rendering (and binds directly to it via cffi with a small in-tree binding).

asyncio/trollius
----------------

Qtile uses the asyncio module as introduced in `PEP 3156`_ for its event loop.
Based on your Python version, there are different ways to install this:

- Python >=3.4: The `asyncio module`_ comes as part of the standard library, so
  there is nothing more to install.
- Python 3.3: This has all the infastructure needed to implement PEP 3156, but
  the asyncio module must be installed from the `Tulip project`_.  This is done
  by calling:

  .. code-block:: bash

      pip install asyncio

  Alternatively, you can install trollius (see next point).
- Python 2 and <=3.2 (and 3.3 without asyncio): You will need to install
  trollius_, which backports the asyncio module functionality to work without
  the infastructure introduced in PEP 3156.  You can install this from PyPi:

  .. code-block:: bash

      pip install trollius

.. _PEP 3156: http://python.org/dev/peps/pep-3156/
.. _asyncio module: https://docs.python.org/3/library/asyncio.html
.. _Tulip project: https://code.google.com/p/tulip/
.. _trollius: http://trollius.readthedocs.org/

importlib
---------

- Python <=2.6 you will need to install importlib from PyPi:

  .. code-block:: bash

      pip install importlib

dbus/gobject
------------

Until someone comes along and writes an asyncio-based dbus library, qtile will
depend on ``python-dbus`` to interact with dbus. This means that if you want
to use things like notification daemon or mpris widgets, you'll need to
install python-gobject and python-dbus. Qtile will run fine without these,
although it will emit a warning that some things won't work.

Qtile
-----

With the dependencies in place, you can now install qtile:

.. code-block:: bash

    git clone git://github.com/qtile/qtile.git
    cd qtile
    sudo python setup.py install
