.. _scripting-interfaces:

==========
Interfaces
==========

Introduction
============

This page provides an overview of the various interfaces available to interact with Qtile's
command graph.

* ``lazy`` calls
* when running ``qtile shell``
* when running ``qtile cmd-obj``
* when using ``CommandClient`` or ``InteractiveCommandClient`` in python 

The way that these commands are called varies depending on which option you select. However, all
interfaces follow the same, basic approach: navigate to the desired object and then execute a command
on that object. The following examples illustrate this principle by showing how the same command can
be accessed by the various interfaces:

.. code:: bash

    Lazy call:
    lazy.widget["volume"].increase_volume()

    qtile shell:
    > cd widget/volume
    widget[volume] > increase_volume()

    qtile cmd-obj:
    qtile cmd-obj -o widget volume -f increase_volume

    CommandClient:
    >>> from libqtile.command.client import CommandClient
    >>> c = CommandClient()
    >>> c.navigate("widget", "volume").call("increase_volume")

    InteractiveCommandClient:
    >>> from libqtile.command.client import InteractiveCommandClient
    >>> c = InteractiveCommandClient()
    >>> c.widget["volume"].increase_volume()  


The Interfaces
==============

From the examples above, you can see that there are five main interfaces which
can be used to interact with Qtile's command graph. Which one you choose will depend
on how you intend to use it as each interface is suited to different scenarios.

* The ``lazy`` interface is used in config scripts to bind commands to keys and
  mouse callbacks.
* The ``qtile shell`` is a tool for exploring the graph my presenting it as a
  file structure. It is not designed to be used for scripting.
* For users creating shell scripts, the ``qtile cmd-obj`` interface would be
  the recommended choice.
* For users wanting to control Qtile from a python script, there are two available
  interfaces ``libqtile.command.client.CommandClient`` and
  ``libqtile.command.client.InteractiveCommandClient``. Users are advised to use the
  ``InteractiveCommandClient`` as this simplifies the syntax for navigating the graph
  and calling commands.


.. _interface-lazy:

The Lazy interface
~~~~~~~~~~~~~~~~~~

The :data:`lazy.lazy` object is a special helper object to specify a command
for later execution. Lazy objects are typically users' first exposure to Qtile's
command graph but they may not realise it. However, understanding this will
help users when they try using some of the other interfaces listed on this page.

The basic syntax for a lazy command is:

.. code:: python

    lazy.node[selector].command(arguments)

No node is required when accessing commands on the root node. In addition,
multiple nodes can be sequenced if required to navigate to a specific object. For example,
bind a key that would focus the next window on the active group on screen 2, you would
create a lazy object as follows:

.. code:: python

    lazy.screen[1].group.next_window()

.. note::

  As noted above, ``lazy`` calls do not call the
  relevant command but only create a reference to it. While this makes it
  ideal for binding commands to key presses and ``mouse_callbacks`` for
  widgets, it also means that ``lazy`` calls cannot be included
  in user-defined functions.

qtile shell
~~~~~~~~~~~

The qtile shell maps the command graph to a virtual filesystem that can be navigated in a similar
way. While it is unlikely to be used for scripting, the ``qtile shell`` interface provides an
excellent means for users to navigate and familiarise themselves with the command graph.

For more information, please refer to :doc:`/manual/commands/shell/qtile-shell`

qtile cmd-obj
~~~~~~~~~~~~~

``qtile cmd-obj`` is a command line interface for executing commands on the command graph. It can
be used as a standalone command (e.g. executed directly from the terminal) or incorporated into shell
scripts.

For more information, please refer to :doc:`/manual/commands/shell/qtile-cmd`

CommandClient
~~~~~~~~~~~~~

The ``CommandClient`` interface is a low-level python interface for accessing and navigating the
command graph. The low-level nature means that navigation steps must be called explicityly,
rather than being inferred from the body of the calling command.

For example:

.. code:: python

    from libqtile.command.client import CommandClient

    c = CommandClient()

    # Call info command on clock widget
    info = c.navigate("widget", "clock").call("info")

    # Call info command on the screen displaying the clock widget
    info = c.navigate("widget", "clock").navigate("screen", None).call("info")

Note from the last example that each navigation step must be called separately. The arguments
passed to ``navigate()`` are ``node`` and ``selector``. ``selector`` is ``None`` when you wish to access
the default object on that node (e.g. the current screen).

More technical explanation about the python command clients can be found at :ref:`command-interface`.

InteractiveCommandClient
~~~~~~~~~~~~~~~~~~~~~~~~

The ``InteractiveCommandClient`` is likely to be the more popular interface for users wishing
to access the command graph via external python scripts. One of the key differences between the
``InteractiveCommandClient`` and the above ``CommandClient`` is that the ``InteractiveCommandClient``
removes the need to call ``navigate`` and ``call`` explicitly. Instead, the syntax mimics that of
the ``lazy`` interface.

For example, to call the same commands in the above example:

.. code:: python

    from libqtile.command.client import InteractiveCommandClient

    c = InteractiveCommandClient()

    # Call info command on clock widget
    info = c.widget["clock"].info()

    # Call info command on the screen displaying the clock widget
    info = c.widget["clock"].screen.info()
