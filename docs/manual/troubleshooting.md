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
