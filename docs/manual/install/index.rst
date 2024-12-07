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

Here are Qtile's core runtime dependencies and the package names that provide them 
in Ubuntu. Note that Qtile can run with one of two backends -- X11 and Wayland -- so 
only the dependencies of one of these is required.

+-------------------+-------------------------+-----------------------------------------+
| Dependency        | Ubuntu Package          |  Needed for                             |
+===================+=========================+=========================================+
|                     **Core Dependencies**                                             |
+-------------------+-------------------------+-----------------------------------------+
| CFFI_             | python3-cffi            | Bars and popups                         |
+-------------------+-------------------------+-----------------------------------------+
| cairocffi_        | python3-cairocffi       | Drawing on bars and popups              |
+-------------------+-------------------------+-----------------------------------------+
| libpangocairo     | libpangocairo-1.0-0     | Writing on bars and popups              |
+-------------------+-------------------------+-----------------------------------------+
| dbus-fast_        | --                      | Sending notifications with dbus         |
|                   |                         | (optional).                             |
+-------------------+-------------------------+-----------------------------------------+
|                       **X11**                                                         |
+-------------------+-------------------------+-----------------------------------------+
| X server          | xserver-xorg            |  X11 backends                           |
+-------------------+-------------------------+-----------------------------------------+
| xcffib_           | python3-xcffib          |  required for X11 backend               |
+-------------------+-------------------------+-----------------------------------------+
|                      **Wayland**                                                      |
+-------------------+-------------------------+-----------------------------------------+
| wlroots_          | libwlroots-dev          |  Wayland backend (see below)            |
+-------------------+-------------------------+-----------------------------------------+
| pywlroots_        | --                      |  python bindings for the wlroots library|
+-------------------+-------------------------+-----------------------------------------+
| pywayland_        | --                      |  python bindings for the wayland library|
+-------------------+-------------------------+-----------------------------------------+
| python-xkbcommon_ | --                      |  required for wayland backeds           |
+-------------------+-------------------------+-----------------------------------------+

.. _CFFI: https://cffi.readthedocs.io/en/latest/installation.html
.. _xcffib: https://github.com/tych0/xcffib#installation
.. _wlroots: https://gitlab.freedesktop.org/wlroots/wlroots
.. _pywlroots: https://github.com/flacjacket/pywlroots
.. _pywayland: https://pywayland.readthedocs.io/en/latest/install.html
.. _python-xkbcommon: https://github.com/sde1000/python-xkbcommon
.. _cairocffi: https://cairocffi.readthedocs.io/en/stable/overview.html
.. _dbus-fast: https://dbus-fast.readthedocs.io/en/latest/


Qtile
-----

With the dependencies in place, you can now install the stable version of qtile from PyPI:

.. code-block:: bash

   pip install qtile

Or with sets of dependencies:

.. code-block:: bash

   pip install qtile[wayland]  # for Wayland dependencies
   pip install qtile[widgets]  # for all widget dependencies
   pip install qtile[all]      # for all dependencies

Or install qtile-git with:

.. code-block:: bash

    git clone https://github.com/qtile/qtile.git
    cd qtile
    pip install .
    pip install --config-setting backend=wayland .  # adds wayland dependencies

.. _starting-qtile:

Starting Qtile
==============

There are several ways to start Qtile. The most common way is via an entry in
your X session manager's menu. The default Qtile behavior can be invoked by
creating a `qtile.desktop
<https://github.com/qtile/qtile/blob/master/resources/qtile.desktop>`_ file in
``/usr/share/xsessions``.

A second way to start Qtile is a custom X session. This way allows you to
invoke Qtile with custom arguments, and also allows you to do any setup you
want (e.g. special keyboard bindings like mapping caps lock to control, setting
your desktop background, etc.) before Qtile starts. If you're using an X
session manager, you still may need to create a ``custom.desktop`` file similar
to the ``qtile.desktop`` file above, but with ``Exec=/etc/X11/xsession``. Then,
create your own ``~/.xsession``. There are several examples of user defined
``xsession`` s in the `qtile-examples
<https://github.com/qtile/qtile-examples>`_ repository.

If there is no display manager such as SDDM, LightDM or other and there is need
to start Qtile directly from ``~/.xinitrc`` do that by adding 
``exec qtile start`` at the end.

In very special cases, ex. Qtile crashing during session, then suggestion would
be to start through a loop to save running applications:

.. code-block:: bash

    while true; do
        qtile
    done


Wayland
=======

Qtile can be run as a Wayland compositor rather than an X11 window manager. For
this, Qtile uses wlroots_, a compositor library which is undergoing fast
development. Be aware that some distributions package outdated versions of
wlroots. More up-to-date distributions such as Arch Linux may package
pywayland, pywlroots and python-xkbcommon. Also note that we may not have yet
caught up with the latest wlroots release ourselves.

.. note::
   We currently support wlroots>=0.17.0,<0.18.0, pywlroots>=0.17.0,<0.18.0 and pywayland >= 0.4.17.

With the Wayland dependencies in place, Qtile can be run either from a TTY, or
within an existing X11 or Wayland session where it will run inside a nested
window:

.. code-block:: bash

    qtile start -b wayland

See the :ref:`Wayland <wayland>` page for more information on running Qtile as
a Wayland compositor.

Similar to the xsession example above, a wayland session file can be used to start qtile
from a login manager. To use this, you should create a `qtile-wayland.desktop
<https://github.com/qtile/qtile/blob/master/resources/qtile-wayland.desktop>`_ file in
``/usr/share/wayland-sessions``.

udev rules
==========

Qtile has widgets that support managing various kinds of hardware (LCD
backlight, keyboard backlight, battery charge thresholds) via the kernel's
exposed sysfs endpoints. However, to make this work, Qtile needs permission to
write to these files. There is a udev rules file at
``/resources/99-qtile.rules`` in the tree, which users installing from source
will want to install at ``/etc/udev/rules.d/`` on their system. By default,
this rules file changes the group of the relevant files to the ``sudo`` group,
and changes the file mode to be g+w (i.e. writable by all members of the sudo
group). The theory here is that most systems qtile is installed on will also
have the primary user in the ``sudo`` group. However, you can change this to
whatever you like with the ``--group`` argument; see the sample udev rules.

Note that this file invokes Qtile's hidden ``udev`` from udevd, so udevd will
need ``qtile`` in its ``$PATH``. For distro packaging this shouldn't be a
problem, since /usr/bin is typically in udev's path. However, for users that
installed from source, you may need to modify the udev script to be one that
sources your virtualenv and then invokes qtile (or just invoke it via its
hardcoded path if you installed it with ``--break-system-packages``), e.g.:

.. code-block:: bash

    # create a wrapper script that loads the right stuff from our home directory; since
    # udev will run this script as root, it has no idea about how we've installed qtile
    mkdir -p $HOME/.local/bin
    tee $HOME/.local/bin/qtile-udev-wrapper <<- EOF
    #!/bin/sh

    export PYTHONPATH=$HOME/.local/lib/python$(python3 --version | awk -F '[ .]' '{print $2 "." $3}')/site-packages
    $HOME/.local/bin/qtile $@
    EOF

    # copy the in-tree udev rules file to the right place to make udev see it,
    # and change the rules to point at our wrapper script above.
    sed "s,qtile,$HOME/.local/bin/qtile-udev-wrapper,g" ./resources/99-qtile.rules | sudo tee /etc/udev/rules.d/99-qtile.rules
