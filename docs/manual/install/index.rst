============
Installation
============

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
    NixOS <nixos>
    Void <void>
    Without DM <without-dm>

.. _installing-from-source:


Installing From Source
======================

Python interpreters
-------------------

We aim to always support the last three versions of CPython, the reference
Python interpreter. We usually support the latest stable version of PyPy_ as
well. You can check the versions and interpreters we currently run our test
suite against in our `CI configuration file`_.

There are not many differences between versions aside from Python features you
may or may not be able to use in your config. PyPy should be faster at runtime
than any corresponding CPython version under most circumstances, especially for
bits of Python code that are run many times. CPython should start up faster than
PyPy and has better compatibility for external libraries.

.. _`CI configuration file`: https://github.com/qtile/qtile/blob/master/.github/workflows/ci.yml
.. _PyPy: https://www.pypy.org/


Core Dependencies
-----------------

Here are Qtile's core runtime dependencies and the package names that provide them 
in Ubuntu. Note that Qtile can run with one of two backends -- X11 and Wayland -- so 
only the dependencies of one of these is required.

+--------------------+-------------------------+-----------------------------------------+
| Dependency         | Ubuntu Package          |  Needed for                             |
+====================+=========================+=========================================+
|                      **Core Dependencies**                                             |
+--------------------+-------------------------+-----------------------------------------+
| CFFI_              | python3-cffi            | Bars and popups                         |
+--------------------+-------------------------+-----------------------------------------+
| cairocffi_         | python3-cairocffi       | Drawing on bars and popups              |
+--------------------+-------------------------+-----------------------------------------+
| libpangocairo      | libpangocairo-1.0-0     | Writing on bars and popups              |
+--------------------+-------------------------+-----------------------------------------+
| dbus-fast_         | --                      | Sending notifications with dbus         |
|                    |                         | (optional).                             |
+--------------------+-------------------------+-----------------------------------------+
|                        **X11**                                                         |
+--------------------+-------------------------+-----------------------------------------+
| X server           | xserver-xorg            |  X11 backends                           |
+--------------------+-------------------------+-----------------------------------------+
| xcffib_            | python3-xcffib          |  required for X11 backend               |
+--------------------+-------------------------+-----------------------------------------+
|                       **Wayland**                                                      |
+--------------------+-------------------------+-----------------------------------------+
| wlroots_           | libwlroots-dev          |  Wayland backend (see below)            |
+--------------------+-------------------------+-----------------------------------------+
+--------------------+-------------------------+-----------------------------------------+
| wayland-scanner_   | --                      |  generate C headers (Wayland backend)   |
+--------------------+-------------------------+-----------------------------------------+
+--------------------+-------------------------+-----------------------------------------+
| wayland-protocols_ | wayland-protocols       |  Additional standard Wayland protocols  |
+--------------------+-------------------------+-----------------------------------------+

.. _CFFI: https://cffi.readthedocs.io/en/latest/installation.html
.. _xcffib: https://github.com/tych0/xcffib#installation
.. _wlroots: https://gitlab.freedesktop.org/wlroots/wlroots
.. _cairocffi: https://cairocffi.readthedocs.io/en/stable/overview.html
.. _wayland-scanner: https://wayland-book.com/libwayland/wayland-scanner.html
.. _wayland-protocols: https://gitlab.freedesktop.org/wayland/wayland-protocols
.. _dbus-fast: https://dbus-fast.readthedocs.io/en/latest/


Qtile
-----

With the dependencies in place, you can now install the stable version of qtile from PyPI:

.. code-block:: bash

   uv tool install qtile

Or with sets of dependencies:

.. code-block:: bash

   uv tool install qtile[widgets]  # for all widget dependencies
   uv tool install qtile[all]      # for all dependencies

Or install qtile-git with:

.. code-block:: bash

    git clone https://github.com/qtile/qtile.git
    cd qtile
    uv tool install .                               # for minimal dependencies
    uv tool install .[dev,widgets,optional-core]    # for all dependencies

Installing other dependencies
-----------------------------

If you use ``uv`` to install qtile, any python modules that you want to use with it
must be installed in the same environment. You have a few options for doing this:

At installation time:

.. code-block:: bash

    # Install package from pypi
    uv tool install --with package-name qtile  # can use qtile[widgets] etc. as above

    # Install from github repo
    uv tool install --with git+https://github.com/elParaguayo/qtile-extras/ .

    # Install from custom requirements file
    uv tool install --with-requirements /path/to/requirements.txt .

Installing packages after installation is a bit more complicated and does not seem to
be officially supported when using ``uv tool``. However, the following code should work:

.. code-block:: bash

    cd $(uv tool dir)/qtile
    uv pip install package-name

.. _starting-qtile:

Starting Qtile
==============

The recommended way to start Qtile is as a systemd user service launched from
your display manager (SDDM, GDM, LightDM, greetd, ...). Starting Qtile this way
activates ``graphical-session.target``, so services such as xdg-desktop-portal
(screen sharing, file pickers, ...) work correctly, and it restarts Qtile if it
crashes. The same setup works whether you run Qtile on X11 or as a Wayland
compositor: Qtile detects the backend from the session it is launched in, so a
single session file serves both.

Qtile ships the required files in `resources/
<https://github.com/qtile/qtile/tree/master/resources>`_:

* `qtile.desktop
  <https://github.com/qtile/qtile/blob/master/resources/qtile.desktop>`_ is the
  session entry your display manager lists. Install it to
  ``/usr/share/xsessions`` to offer an X11 session and/or
  ``/usr/share/wayland-sessions`` to offer a Wayland session.
* `qtile.service
  <https://github.com/qtile/qtile/blob/master/resources/qtile.service>`_ and
  `qtile-session.target
  <https://github.com/qtile/qtile/blob/master/resources/qtile-session.target>`_
  are the systemd user units that run Qtile and pull in
  ``graphical-session.target``. Install both to ``~/.config/systemd/user/``.

See `resources/README
<https://github.com/qtile/qtile/blob/master/resources/README>`_ for the details
of installing these files, handing the session environment to user services, and
pinning an xdg-desktop-portal backend.

To start Qtile without a display manager -- for example autologin on a TTY --
see :doc:`without-dm`.

See the :ref:`Wayland <wayland>` page for more information on running Qtile as
a Wayland compositor.

udev rules
==========

Qtile has widgets that support managing various kinds of hardware (LCD
backlight, keyboard backlight, battery charge thresholds) via the kernel's
exposed sysfs endpoints. However, to make this work, Qtile needs permission to
write to these files. There is a udev rules file at
``/resources/99-qtile.rules`` in the tree, which users installing from source
will want to install at ``/etc/udev/rules.d/`` on their system. You can
install it manually with:

.. code-block:: bash

    # copy the in-tree udev rules file to the right place to make udev see it
    cat ./resources/99-qtile.rules | sudo tee /etc/udev/rules.d/99-qtile.rules
