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

Installing From Source
======================

First, you need to install all of Qtile's dependencies (although some are
optional/not needed depending on your Python version, as noted below).

Note that Python 3 versions 3.5 and newer are currently supported and tested,
including corresponding PyPy3 versions.

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
    pip install .

Stable versions of Qtile can be installed from PyPI:

.. code-block:: bash

    pip install qtile

As long as the necessary libraries are in place, this can be done at any point,
however, it is recommended that you first install xcffib to ensure the
cairo-xcb bindings are built (see above).

The above steps are sufficient to run Qtile directly, but there are some extra
works if you want to run it within a virtualenv. Here are the steps on a Fedora
system for user ``foo``, it should work on other Linux systems too.

#. Clone the repo as ``~/local/qtile/``.

   .. code-block:: bash

       mkdir -p ~/local/
       cd ~/local/
       git clone git://github.com/qtile/qtile.git

#. Create a virtualenv ``~/local/qtile/venv/``, and install the dependencies
   there (see above).

#. Create a glue shell to take advantage of the virtualenv.

   .. code-block:: bash

       cat > /home/foo/local/qtile/qtile-venv-entry <<EOF
       #!/bin/bash

       source ~/local/qtile/venv/bin/activate
       python ~/local/qtile/bin/qtile $*
       EOF

#. Create an xsession file.
   Note that it can only be used to log in as user ``foo`` due to file system
   permission restriction.

   .. code-block:: bash

       cat > /usr/share/xsessions/qtile-venv.desktop <<EOF
       [Desktop Entry]
       Name=Qtile(venv)
       Comment=Qtile Session Within Venv
       Exec=/home/foo/local/qtile/qtile-venv-entry
       Type=Application
       Keywords=wm;tiling
       EOF

#. Log out or reboot your system, then select "Qtile(venv)" as your window manager
   by clicking the gear icon (⚙) when logging in again.
