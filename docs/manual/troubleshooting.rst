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
   raise Exception as e:
       logger.exception(e)

``logger.warning`` is convenient because its messages will always be visibile
in the log. ``logger.exception`` is helpful because it will print the full
traceback of an error to the log. By sticking these amongst your changes you
can look more closely at the effects of any changes you made to Qtile's
internals.

.. _capturing-an-xtrace:

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
