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

Python interpreters
-------------------

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


Core Dependencies
-----------------

Here are Qtile's core runtime dependencies and where available the package name
that provides them in Ubuntu. Note that Qtile can run with one of two backends
-- X11 and Wayland -- so only the dependencies of one of these is required.

================= =================== ==========================================
Dependency        Ubuntu Package      Needed for
================= =================== ==========================================
CFFI_             python3-cffi        Both backends, bars and popups
X server          xserver-xorg        X11 backend
xcffib_           python3-xcffib      X11 backend
wlroots_          libwlroots-dev      Wayland backend (see below)
pywlroots_        --                  Wayland backend
pywayland_        --                  Wayland backend
python-xkbcommon_ --                  Wayland backend
cairocffi_        python3-cairocffi   Drawing on bars and popups (see below)
libpangocairo     libpangocairo-1.0-0 Writing on bars and popups
dbus-next_        --                  Sending notifications with dbus (optional)
================= =================== ==========================================

.. _CFFI: https://cffi.readthedocs.io/en/latest/installation.html
.. _xcffib: https://github.com/tych0/xcffib#installation
.. _wlroots: https://gitlab.freedesktop.org/wlroots/wlroots
.. _pywlroots: https://github.com/flacjacket/pywlroots
.. _pywayland: https://pywayland.readthedocs.io/en/latest/install.html
.. _python-xkbcommon: https://github.com/sde1000/python-xkbcommon
.. _cairocffi: https://cairocffi.readthedocs.io/en/stable/overview.html
.. _dbus-next: https://python-dbus-next.readthedocs.io/en/latest/index.html


cairocffi
---------

Qtile uses cairocffi_ for drawing on status bars and popup windows. Under X11,
cairocffi requires XCB support via xcffib, which you should be sure to have
installed **before** installing cairocffi, otherwise the needed cairo-xcb
bindings will not be built. Once you've got the dependencies installed, you can
use the latest version on PyPI:

.. code-block:: bash

    pip install --no-cache-dir cairocffi


Qtile
-----

With the dependencies in place, you can now install qtile:

.. code-block:: bash

    git clone https://github.com/qtile/qtile.git
    cd qtile
    pip install .

Stable versions of Qtile can be installed from PyPI:

.. code-block:: bash

    pip install qtile

As long as the necessary libraries are in place, this can be done at any point,
however, it is recommended that you first install xcffib to ensure the
cairo-xcb bindings are built (X11 only) (see above).


Wayland
=======

Qtile can be run as a Wayland compositor rather than an X11 window manager. For
this, Qtile uses wlroots_, a compositor library which is undergoing fast
development. This means we can only support the latest release. Be aware that
some distributions package outdated versions of wlroots. More up-to-date
distributions such as Arch Linux may also package pywayland, pywlroots and
python-xkbcommon.

With the Wayland dependencies in place, Qtile can be run either from a TTY, or
within an existing X11 or Wayland session where it will run inside a nested
window:

.. code-block:: bash

    qtile start -b wayland

See the :ref:`Wayland <wayland>` page for more information on running Qtile as
a Wayland compositor.
