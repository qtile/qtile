===============
Troubleshooting
===============

So something has gone wrong... what do you do?
==============================================

When Qtile is running, it logs error messages (and other messages) to its log
file. This is found at ``~/.local/share/qtile/qtile.log``. This is the first
place to check to see what is going on. If you are getting unexpected errors
from normal usage or your configuration (and you're not doing something wacky)
and believe you have found a bug, then please :ref:`report a bug <reporting>`.

If you are :ref:`hacking on Qtile <hacking>` and you want to debug your
changes, this log is your best friend. You can send messages to the log from
within libqtile by using the ``logger``:

.. code-block:: python

   from libqtile.log_utils import logger

   logger.warning("Your message here")
   logger.warning(variable_you_want_to_print)

   try:
       # some changes here that might error
   except Exception:
       logger.exception("Uh oh!")

``logger.warning`` is convenient because its messages will always be visibile
in the log. ``logger.exception`` is helpful because it will print the full
traceback of an error to the log. By sticking these amongst your changes you
can look more closely at the effects of any changes you made to Qtile's
internals.

.. _capturing-an-xtrace:

X11: Capturing an ``xtrace``
============================

Occasionally, a bug will be low level enough to require an ``xtrace`` of
Qtile's conversations with the X server. To capture one of these, create an
``xinitrc`` or similar file with:

.. code-block:: bash

  exec xtrace qtile >> ~/qtile.log

This will put the xtrace output in Qtile's logfile as well. You can then
demonstrate the bug, and paste the contents of this file into the bug report.

Note that xtrace may be named ``x11trace`` on some platforms, for example, on Fedora.

.. _debugging-wayland:

Debugging in Wayland
=====================

To get incredibly verbose output of communications between clients and the
server, you can set ``WAYLAND_DEBUG=1`` in the environment before starting the
process. This applies to the server itself, so be aware that running ``qtile``
with this set will generate lots of output for Qtile **and** all clients that
it launches. If you're including this output with a bug report please try to
cut out just the relevant portions.

If you're hacking on Qtile and would like this debug log output for it rather
than any clients, it can be helpful to run the helper script at
``scripts/wephyr`` in the source from an existing session. You can then run
clients from another terminal using the ``WAYLAND_DISPLAY`` value printed by
Qtile, so that the debug logs printed by Qtile are only the server's.

If you suspect a client may be responsible for a bug, it can be helpful to look
at the issue trackers for other compositors, such as `sway
<https://github.com/swaywm/sway/issues>`_. Similarly if you're hacking on
Qtile's internals and think you've found an unexpected quirk it may be helpful
to search the issue tracker for `wlroots
<https://gitlab.freedesktop.org/wlroots/wlroots/-/issues>`_.

Common Issues
=============

.. _cairo-errors:

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
