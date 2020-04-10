================
Hacking on Qtile
================

Requirements
============

Any reasonably recent version of these should work, so you can probably just
install them from your package manager.

* `pytest <http://pytest.org/latest/>`_
* `Xephyr <http://www.freedesktop.org/wiki/Software/Xephyr>`_
* ``xrandr``, ``xcalc``, ``xeyes`` and ``xclock`` (``x11-apps`` on Ubuntu)

On Ubuntu, if testing on Python 3, this can be done with:

.. code-block:: bash

    sudo apt-get install python3-pytest xserver-xephyr x11-apps

On ArchLinux, the X11 requirements are installed with:

.. code-block:: bash

    sudo pacman -S xorg-xrandr xorg-xcalc xorg-xeyes xorg-xclock
    
To build the documentation, you will also need to install `graphviz <https://www.graphviz.org/download/>`_.
On ArchLinux, you can install it with ``sudo pacman -S graphviz``.


Building cffi module
====================

Qtile ships with a small in-tree pangocairo binding built using cffi,
``pangocffi.py``, and also binds to xcursor with cffi.  The bindings are not
built at run time and will have to be generated manually when the code is
downloaded or when any changes are made to the cffi library.  This can be done
by calling:

.. code-block:: bash

    ./scripts/ffibuild

Setting up the environment
==========================

In the root of the project, run ``./dev.sh``.
It will create a virtualenv called ``venv``.

Activate this virtualenv with ``. venv/bin/activate``.
Deactivate it with the ``deactivate`` command.

Building the documentation
==========================

Activate your virtualenv, and install the ``graphviz`` Python package:

    pip install graphviz
    
Go into the ``docs/`` directory and run ``make html``.

Check the result by opening ``_build/html/index.html`` in your browser.

Development and testing
=======================

In practice, the development cycle looks something like this:

1. make minor code change
#. run appropriate test: ``pytest tests/test_module.py`` or ``pytest -k PATTERN``
#. GOTO 1, until hackage is complete
#. run entire test suite: ``pytest``
#. commit

Of course, your patches should also pass the unit tests as well (i.e.
``make check``). These will be run by travis-ci on every pull request so you
can see whether or not your contribution passes.

Coding style
============

While not all of our code follows `PEP8 <http://www.python.org/dev/peps/pep-0008/>`_,
we do try to adhere to it where possible. All new code should be PEP8 compliant.

The ``make lint`` command will run a linter with our configuration over libqtile
to ensure your patch complies with reasonable formatting constraints. We also
request that git commit messages follow the
`standard format <http://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html>`_.

Deprecation policy
==================

When a widget API is changed, you should deprecate the change using
``libqtile.widget.base.deprecated`` to warn users, in addition to adding it to
the appropriate place in the changelog. We will typically remove deprecated
APIs one tag after they are deprecated.

Using Xephyr
============

Qtile has a very extensive test suite, using the Xephyr nested X server. When
tests are run, a nested X server with a nested instance of Qtile is fired up,
and then tests interact with the Qtile instance through the client API. The
fact that we can do this is a great demonstration of just how completely
scriptable Qtile is. In fact, Qtile is designed expressly to be scriptable
enough to allow unit testing in a nested environment.

The Qtile repo includes a tiny helper script to let you quickly pull up a
nested instance of Qtile in Xephyr, using your current configuration.
Run it from the top-level of the repository, like this::

  ./scripts/xephyr

Change the screen size by setting the ``SCREEN_SIZE`` environment variable.
Default: 800x600. Example::

  SCREEN_SIZE=1920x1080 ./scripts/xephyr

Change the log level by setting the ``LOG_LEVEL`` environment variable.
Default: INFO. Example::

  LOG_LEVEL=DEBUG ./scripts/xephyr

The script will also pass any additional options to Qtile. For example, you
can use a specific configuration file like this::

  ./scripts/xephyr -c ~/.config/qtile/other_config.py

Once the Xephyr window is running and focused, you can enable capturing the
keyboard shortcuts by hitting Control+Shift. Hitting them again will disable the
capture and let you use your personal keyboard shortcuts again.

You can close the Xephyr window by enabling the capture of keyboard shortcuts
and hit Mod4+Control+Q. Mod4 (or Mod) is usually the Super key (or Windows key).
You can also close the Xephyr window by running ``qtile-cmd -o cmd -f shutdown``
in a terminal (from inside the Xephyr window of course).

You don't need to run the Xephyr script in order to run the tests
as the test runner will launch its own Xephyr instances.

Second X Session
================

Some users prefer to test Qtile in a second, completely separate X session:
Just switch to a new tty and run ``startx`` normally to use the ``~/.xinitrc``
X startup script.

It's likely though that you want to use a different, customized startup script
for testing purposes, for example ``~/.config/qtile/xinitrc``. You can do so by
launching X with:

.. code-block:: bash

  startx ~/.config/qtile/xinitrc

``startx`` deals with multiple X sessions automatically. If you want to use
``xinit`` instead, you need to first copy ``/etc/X11/xinit/xserverrc`` to
``~/.xserverrc``; when launching it, you have to specify a new session number:

.. code-block:: bash

  xinit ~/.config/qtile/xinitrc -- :1

Examples of custom X startup scripts are available in `qtile-examples
<https://github.com/qtile/qtile-examples>`_.

Capturing an ``xtrace``
=======================

Occasionally, a bug will be low level enough to require an ``xtrace`` of
Qtile's conversations with the X server. To capture one of these, create an
``xinitrc`` or similar file with:

.. code-block:: bash

  exec xtrace qtile >> ~/qtile.log

This will put the xtrace output in Qtile's logfile as well. You can then
demonstrate the bug, and paste the contents of this file into the bug report.

Note that xtrace may be named ``x11trace`` on some platforms, for example, on Fedora.

Resources
=========

Here are a number of resources that may come in handy:

* `Inter-Client Conventions Manual <http://tronche.com/gui/x/icccm/>`_
* `Extended Window Manager Hints <http://standards.freedesktop.org/wm-spec/wm-spec-latest.html>`_
* `A reasonable basic Xlib Manual <http://tronche.com/gui/x/xlib/>`_


Troubleshoot
============

Cairo errors
------------

When running the Xephyr script (``./scripts/xephyr``), you might see tracebacks
with attribute errors like the following or similar::

    AttributeError: cffi library 'libcairo.so.2' has no function, constant or global variable named 'cairo_xcb_surface_create'

If it happens, it might be because the ``cairocffi`` and ``xcffib`` dependencies
were installed in the wrong order.

To fix this:

1. uninstall them from your environment: with ``pip uninstall cairocffi xcffib``
   if using a virtualenv, or with your system package-manager if you installed
   the development version of Qtile system-wide.
#. re-install them sequentially (again, with pip or with your package-manager)::

    pip install xcffib
    pip install --no-cache-dir cairocffi

See `this issue comment`_ for more information.

.. _`this issue comment`: https://github.com/qtile/qtile/issues/994#issuecomment-497984551

If you are using your system package-manager and the issue still happens,
the packaging of ``cairocffi`` might be broken for your distribution.
Try to contact the persons responsible for ``cairocffi``'s packaging
on your distribution, or to install it from the sources with ``xcffib``
available.

DBus/GObject errors
-------------------

When running the Xephyr script (``./scripts/xephyr``), you might see a line in
the output like the following or similar::

    libqtile manager.py:setup_python_dbus():L310  importing dbus/gobject failed, dbus will not work.

If it happens, it might be because you are missing some dependencies on your
system and/or in your Qtile virtualenv.

To fix this:

1. follow the installation instructions of ``PyGObject``
   at https://pygobject.readthedocs.io/en/latest/getting_started.html.
   There are methods for several Linux distributions: pick yours.
#. there are instructions for system-wide installation and virtualenv
   installation: pick the relevant one, depending on how you installed the
   development version of QTile (usually in a virtualenv).
#. Optionally re-install QTile's dependencies::

    pip install -r requirements.txt
    pip install -r requirements-dev.txt


Fonts errors
------------

When running the test suite or the Xephyr script (``./scripts/xephyr``),
you might see errors in the output like the following or similar:

* Xephyr script::

    xterm: cannot load font "-Misc-Fixed-medium-R-*-*-13-120-75-75-C-120-ISO10646-1"
    xterm: cannot load font "-misc-fixed-medium-r-semicondensed--13-120-75-75-c-60-iso10646-1"

* ``pytest``::

    ---------- Captured stderr call ----------
    Warning: Cannot convert string "8x13" to type FontStruct
    Warning: Unable to load any usable ISO8859 font
    Warning: Unable to load any usable ISO8859 font
    Error: Aborting: no font found

    -------- Captured stderr teardown --------
    Qtile exited with exitcode: -9

If it happens, it might be because you're missing fonts on your system.

On ArchLinux, you can fix this by installing ``xorg-fonts-misc``::

    sudo pacman -S xorg-fonts-misc

Try to search for "xorg fonts misc" with your distribution name on the internet
to find how to install them.
