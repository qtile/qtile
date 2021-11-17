.. _scripting:

=========
Scripting
=========

Client-Server Scripting Model
=============================

Qtile has a client-server control model - the main Qtile instance listens on a
named pipe, over which marshalled command calls and response data is passed.
This allows Qtile to be controlled fully from external scripts. Remote
interaction occurs through an instance of the
``libqtile.command.interface.IPCCommandInterface`` class. This class
establishes a connection to the currently running instance of Qtile.  A
``libqtile.command.client.InteractiveCommandClient`` can use this connection to dispatch
commands to the running instance.  Commands then appear as methods with the
appropriate signature on the ``InteractiveCommandClient`` object.  The object hierarchy is
described in the :ref:`commands-api` section of this manual. Full
command documentation is available through the :ref:`Qtile Shell
<qtile-shell>`.


Example
=======

Below is a very minimal example script that inspects the current Qtile
instance, and returns the integer offset of the current screen.

.. code-block:: python

    from libqtile.command.client import InteractiveCommandClient
    c = InteractiveCommandClient()
    print(c.screen.info()["index"])
