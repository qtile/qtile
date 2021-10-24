.. _hacking:

================
Hacking on Qtile
================

Requirements
============

Here are Qtile's additional dependencies that may be required for tests:

================= =================== ==================================================
Dependency        Ubuntu Package      Needed for
================= =================== ==================================================
pytest_           python3-pytest      Running tests
PyGObject         python3-gi          Running tests (test windows)
Xephyr_           xserver-xephyr      Testing with X11 backend (optional, see below)
mypy              python3-mypy        Testing ``qtile check`` (optional)
imagemagick>=6.8  imagemagick         ``test/test_images*`` (optional)
gtk-layer-shell   libgtk-layer-shell0 Testing notification windows in Wayland (optional)
dbus-launch       dbus-x11            Testing dbus-using widgets (optional)
notifiy-send      libnotify-bin       Testing ``Notify`` widget (optional)
xvfb              xvfb                Testing with X11 headless (optional)
================= =================== ==================================================

.. _pytest: https://docs.pytest.org
.. _Xephyr: https://freedesktop.org/wiki/Software/Xephyr


Backends
--------

The test suite can be run using the X11 or Wayland backend, or both.  By
default, only the X11 backend is used for tests. To test a single backend or
both backends, specify as arguments to pytest:

.. code-block:: bash

    pytest --backend wayland  # Test just Wayland backend
    pytest --backend x11 --backend wayland  # Test both

Testing with the X11 backend requires Xephyr_ (and xvfb for headless mode) in addition to the core
dependencies.


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

To build the documentation, you will also need to install `graphviz
<https://www.graphviz.org/download/>`_.

Go into the ``docs/`` directory and run ``pip install -r requirements.txt``.

Build the documentation with ``make html``.

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
``make check``). These will be run by ci on every pull request so you
can see whether or not your contribution passes.

Coding style
============

While not all of our code follows `PEP8 <https://www.python.org/dev/peps/pep-0008/>`_,
we do try to adhere to it where possible. All new code should be PEP8 compliant.

The ``make lint`` command will run a linter with our configuration over libqtile
to ensure your patch complies with reasonable formatting constraints. We also
request that git commit messages follow the
`standard format <https://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html>`_.

Logging
=======

Logs are important to us because they are our best way to see what Qtile is
doing when something abnormal happens. However, our goal is not to have as many
logs as possible, as this hinders readability. What we want are relevant logs.

To decide which log level to use, refer to the following scenarios:

* ERROR: a problem affects the behavior of Qtile in a way that is noticeable to
  the end user, and we can't work around it.
* WARNING: a problem causes Qtile to operate in a suboptimal manner.
* INFO: the state of Qtile has changed.
* DEBUG: information is worth giving to help the developer better understand
  which branch the process is in.

Be careful not to overuse DEBUG and clutter the logs. No information should be
duplicated between two messages.

Also, keep in mind that any other level than DEBUG is aimed at users who don't
necessarily have advanced programming knowledge; adapt your message
accordingly. If it can't make sense to your grandma, it's probably meant to be
a DEBUG message.

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
You can also close the Xephyr window by running ``qtile cmd-obj -o cmd -f shutdown``
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

Debugging in PyCharm
====================

Make sure to have all the requirements installed and your development environment setup.

PyCharm should automatically detect the ``venv`` virtualenv when opening the project.
If you are using another viirtualenv, just instruct PyCharm to use it
in ``Settings -> Project: qtile -> Project interpreter``.

In the project tree, on the left, right-click on the ``libqtile`` folder,
and click on ``Mark Directory as -> Sources Root``.

Next, add a Configuration using a Python template with these fields:

- Script path: ``bin/qtile``, or the absolute path to it
- Parameters: ``-c libqtile/resources/default_config.py``,
  or nothing if you want to use your own config file in ``~/.config/qtile/config.py``
- Environment variables: ``PYTHONUNBUFFERED=1;DISPLAY=:1``
- Working directory: the root of the project
- Add contents root to PYTHONPATH: yes
- Add source root to PYTHONPATH: yes

Then, in a terminal, run:

    Xephyr +extension RANDR -screen 1920x1040 :1 -ac &

Note that we used the same display, ``:1``, in both the terminal command
and the PyCharm configuration environment variables.
Feel free to change the screen size to fit your own screen.

Finally, place your breakpoints in the code and click on ``Debug``!

Once you finished debugging, you can close the Xephyr window with ``kill PID``
(use the ``jobs`` builtin to get its PID).

Debugging in VSCode
===================

Make sure to have all the requirements installed and your development
environment setup.

Open the root of the repo in VSCode.  If you have created it, VSCode should
detect the ``venv`` virtualenv, if not, select it.

Create a launch.json file with the following lines.

.. code-block:: json

  {
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Qtile",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/bin/qtile",
            "cwd": "${workspaceFolder}",
            "args": ["-c", "libqtile/resources/default_config.py"],
            "console": "integratedTerminal",
            "env": {"PYTHONUNBUFFERED":"1", "DISPLAY":":1"}
        }
    ]
  }

Then, in a terminal, run:

    Xephyr +extension RANDR -screen 1920x1040 :1 -ac &

Note that we used the same display, ``:1``, in both the terminal command
and the VSCode configuration environment variables.  Then ``debug`` usually
in VSCode. Feel free to change the screen size to fit your own screen.

Resources
=========

Here are a number of resources that may come in handy:

* `Inter-Client Conventions Manual <https://tronche.com/gui/x/icccm/>`_
* `Extended Window Manager Hints <https://specifications.freedesktop.org/wm-spec/wm-spec-latest.html>`_
* `A reasonable basic Xlib Manual <https://tronche.com/gui/x/xlib/>`_


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
