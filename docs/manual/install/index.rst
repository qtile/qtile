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
    Ubuntu/Debian <ubuntu>
    Slackware <slackware>
    FreeBSD <freebsd>

.. _installing-from-source:

Installing From Source
======================


First, you need to install all of Qtile's dependencies (although some are
optional/not needed depending on your Python version, as noted below).

We aim to always support the last three versions of CPython, the reference
Python interpreter. We usually support the latest stable version of PyPy_ as
well. You can check the versions and interpreters we currently run our test
suite against in our `tox configuration file`_.

There are not many differences between versions aside from Python features you
may or may not be able to use in your config. PyPy should be faster at runtime
than any corresponding CPython version under most circumstances, especially for
bits of Python code that are run many times. CPython should start up faster than
PyPy and has better compatibility for external libraries.

.. _`tox configuration file`: https://github.com/qtile/qtile/blob/master/tox.ini
.. _PyPy: https://www.pypy.org/


xcffib
------

Qtile uses xcffib_ as an XCB binding, which has its own instructions for
building from source. However, if you'd like to skip building it, you can
install its dependencies, you will need libxcb and libffi with the associated
headers (``libxcb-render0-dev`` and ``libffi-dev`` on Ubuntu), and install it
via PyPI:

.. code-block:: bash

    pip install xcffib

.. _xcffib: https://github.com/tych0/xcffib#installation

cairocffi
---------

Qtile uses cairocffi_ with XCB support via xcffib. You'll need ``libcairo2``,
the underlying library used by the binding.  You should **be sure before you
install cairocffi that xcffib has been installed**, otherwise the needed
cairo-xcb bindings will not be built.  Once you've got the dependencies
installed, you can use the latest version on PyPI:

.. code-block:: bash

    pip install --no-cache-dir cairocffi

.. _cairocffi: https://pythonhosted.org/cairocffi/overview.html

pangocairo
----------

You'll also need ``libpangocairo``, which on Ubuntu can be installed via ``sudo
apt-get install libpangocairo-1.0-0``. Qtile uses this to provide text
rendering (and binds directly to it via cffi with a small in-tree binding).

dbus-next
---------

Qtile uses ``dbus-next`` to interact with dbus. Qtile will run without this
packagee but certain functionality will be lost (e.g. notifications).

You can install dbus-next from PyPi:

.. code-block:: bash

    pip install dbus-next

Qtile
-----

With the dependencies in place, you can now install qtile:

.. code-block:: bash

    git clone git://github.com/qtile/qtile.git
    cd qtile
    pip install .

Stable versions of Qtile can be installed from PyPI:

.. code-block:: bash

    pip install qtile

As long as the necessary libraries are in place, this can be done at any point,
however, it is recommended that you first install xcffib to ensure the
cairo-xcb bindings are built (see above).
