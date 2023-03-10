=========================
Command graph development
=========================

This page provides further detail on how Qtile's command graph works.
If you just want to script your Qtile window manager the :doc:`earlier information <index>`, in
addition to the documentation on the :doc:`available commands <api/index>` should be enough to get started.

To develop the Qtile manager itself, we can dig into how Qtile represents these objects,
which will lead to the way the commands are dispatched.

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

Digging Deeper: Command Objects
===============================

All of the configured objects setup by Qtile are ``CommandObject`` subclasses.
These objects are so named because we can issue commands against them using the
command scripting API.  Looking through the code, the commands that are exposed
are commands that are decorated with the ``@expose_command()`` decorator.
When writing custom layouts, widgets, or any other object, you can add your own
custom functions and, once you add the decorator, they will be callable using the
standard command infrastructure. An available command can be extracted by calling
``.command()`` with the name of the command.

In addition to having a set of associated commands, each command object also
has a collection of items associated with it.  This is what forms the graph
that is shown above.  For a given object type, the ``items()`` method returns
all of the names of the associated objects of that type and whether or not
there is a defaultable value.  For example, from the root, ``.items("group")``
returns the name of all of the groups and that there is a default value, the
currently focused group.

To navigate from one command object to the next, the ``.select()`` method is
used.  This method resolves a requested object from the command graph by
iteratively selecting objects.  A selector like ``[("group", "b"), ("screen",
None)]`` would be to first resolve group "b", then the screen associated to the
group.

The Command Graph
=================

In order to help in specifying command objects, there is the abstract command
graph structure.  The command graph structure allows us to address any valid
command object and issue any command against it without needing to have any
Qtile instance running or have anything to resolve the objects to.  This is
particularly useful when constructing lazy calls, where the Qtile instance does
not exist to specify the path that will be resolved when the command is
executed.  The only limitation of traversing the command graph is that it must
follow the allowed edges specified in the first section above.

Every object in the command graph is represented by a ``CommandGraphNode``.
Any call can be resolved from a given node.  In addition, each node knows about
all of the children objects that can be reached from it and have the ability to
``.navigate()`` to the other nodes in the command graph.  Each of the object
types are represented as ``CommandGraphObject`` types and the root node of the
graph, the ``CommandGraphRoot`` represents the Qtile instance.  When a call is
performed on an object, it returns a ``CommandGraphCall``.  Each call will know
its own name as well as be able to resolve the path through the command graph
to be able to find itself.

Note that the command graph itself can standalone, there is no other
functionality within Qtile that it relies on.  While we could have started here
and built up, it is helpful to understand the objects that the graph is meant
to represent, as the graph is just a representation of a traversal of the real
objects in a running Qtile window manager.  In order to tie the running Qtile
instance to the abstract command graph, we move on to the command interface.

.. _command-interface:

Executing graph commands: Command Interface
===========================================

The ``CommandInterface`` is what lets us take an abstract call on the command
graph and resolve it against a running command object.  Put another way, this
is what takes the graph traversal ``.group["b"].screen.info()`` and executes
the ``info()`` command against the addressed ``screen`` object.  Additional
functionality can be used to check that a given traversal resolves to actual
objcets and that the requested command actually exists.  Note that by
construction of the command graph, the traversals here must be feasible, even
if they cannot be resolved for a given configuration state.  For example, it is
possible to check the screen assoctiated to a group, even though the group may
not be on a screen, but it is not possible to check the widget associated to a
group.

The simplest form of the command interface is the ``QtileCommandInterface``,
which can take an in-process ``Qtile`` instance as the root ``CommandObject``
and execute requested commands.  This is typically how we run the unit tests
for Qtile.

The other primary example of this is the ``IPCCommandInterface`` which is able
to then route all calls through an IPC client connected to a running Qtile
instance.  In this case, the command graph call can be constructed on the
client side without having to dispatch to Qtile and once the call is
constructed and deemed valid, the call can be executed.

In both of these cases, executing a command on a command interface will return
the result of executing the command on a running Qtile instance.  To support
lazy execution, the ``LazyCommandInterface`` instead returns a ``LazyCall``
which is able to be resolved later by the running Qtile instance when it is
configured to fire.

Tying it together: Command Client
=================================

So far, we have our running Command Objects and the Command Interface to
dispatch commands against these objects as well as the Command Graph structure
itself which encodes how to traverse the connections between the objects.  The
final component which ties everything together is the Command Client, which
allows us to navigate through the graph to resolve objects, find their
associated commands, and execute the commands against the held command
interface.

The idea of the command client is that it is created with a reference into the
command graph and a command interface.  All navigation can be done against the
command graph, and traversal is done by creating a new command client starting
from the new node.  When a command is executed against a node, that command is
dispatched to the held command interface.  The key decision here is how to
perform the traversal.  The command client exists in two different flavors: the
standard ``CommandClient`` which is useful for handling more programatic
traversal of the graph, calling methods to traverse the graph, and the
``InteractiveCommandClient`` which behaves more like a standard Python object,
traversing by accessing properties and performing key lookups.

Returning to our examples above, we now have the full context to see what is
going on when we call:

.. code-block:: python

    from libqtile.command.client import CommandClient
    c = CommandClient()
    print(c.call("status")())
    from libqtile.command.client import InteractiveCommandClient
    c = InteractiveCommandClient()
    print(c.status())

In both cases, the command clients are constructed with the default command
interface, which sets up an IPC connection to the running Qtile instance, and
starts the client at the graph root.  When we call ``c.call("status")`` or
``c.status``, we navigate the command client to the ``status`` command on the
root graph object.  When these are invoked, the commands graph calls are
dispatched via the IPC command interface and the results then sent back and
printed on the local command line.

The power that can be realized by separating out the traversal and resolution
of objects in the command graph from actually invoking or looking up any
objects within the graph can be seen in the ``lazy`` module.  By creating a
lazy evaluated command client, we can expose the graph traversal and object
resolution functionality via the same ``InteractiveCommandClient`` that is used
to perform live command execution in the Qtile prompt.
