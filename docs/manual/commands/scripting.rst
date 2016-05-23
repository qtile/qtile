=========
Scripting
=========

Client-Server Scripting Model
=============================

Qtile has a client-server control model - the main Qtile instance listens on a
named pipe, over which marshalled command calls and response data is passed.
This allows Qtile to be controlled fully from external scripts. Remote
interaction occurs through an instance of the :class:`libqtile.command.Client`
class. This class establishes a connection to the currently running instance of
Qtile, and sources the user's configuration file to figure out which commands
should be exposed. Commands then appear as methods with the appropriate
signature on the ``Client`` object.  The object hierarchy is described in the
:doc:`/manual/commands/index` section of this manual. Full command
documentation is available through the :doc:`Qtile Shell
</manual/commands/qshell>`.


Example
=======

Below is a very minimal example script that inspects the current qtile
instance, and returns the integer offset of the current screen.

.. code-block:: python

    from libqtile.command import Client
    c = Client()
    print c.screen.info()["index"]

Reference
=========

.. qtile_class:: libqtile.command.Client
