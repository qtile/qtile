.. _commands-api:

============
Commands API
============

Qtile's command API is based on a graph of objects, where each object has a set
of associated commands. The graph and object commands are used in a number of
different places:

* Commands can be :ref:`bound to keys <config-keys>` in the Qtile
  configuration file.
* Commands can be :ref:`called through qtile shell <qtile-shell>`, the
  Qtile shell.
* The shell can also be hooked into a Jupyter kernel :ref:`called iqshell
  <iqshell>`.
* Commands can be :ref:`called from a script <scripting>` to
  interact with Qtile from Python.

If the explanation below seems a bit complex, please take a moment to explore
the API using the ``qtile shell`` command shell. Command lists and detailed
documentation can be accessed from its built-in help command.


Introduction: Object Graph
==========================

The objects in Qtile's object graph come in seven flavours, matching the seven
basic components of the window manager: ``layouts``, ``windows``, ``groups``,
``bars``, ``widgets``, ``screens``, and a special ``root`` node.  Objects are
addressed by a path specification that starts at the root, and follows the
edges of the graph. This is what the graph looks like:

.. graphviz:: /_static/diagrams/object-graph-orig.dot

Each arrow can be read as "holds a reference to". So, we can see that a
``widget`` object *holds a reference to* objects of type ``bar``, ``screen``
and ``group``. Lets start with some simple examples of how the addressing
works. Which particular objects we hold reference to depends on the context -
for instance, widgets hold a reference to the screen that they appear on, and
the bar they are attached to.

Lets look at an example, starting at the root node. The following script runs
the ``status`` command on the root node, which, in this case, is represented by
the ``InteractiveCommandClient`` object:

.. code-block:: python

    from libqtile.command.client import InteractiveCommandClient
    c = InteractiveCommandClient()
    print(c.status())

The ``InteractiveCommandClient`` is a class that allows us to traverse the
command graph using attributes to select child nodes or commands.  In this
example, we have resolved the ``status()`` command on the root object.  The
interactive command client will automatically find and connect to a running
Qtile instance, and which it will use to dispatch the call and print out the
return.

An alternative is to use the ``CommandClient``, which allows for a more precise
resolution of command graph objects, but is not as easy to interact with from a
REPL:

.. code-block:: python

    from libqtile.command.client import CommandClient
    c = CommandClient()
    print(c.call("status")())

Like the interactive client, the command client will automatically connect to a
running Qtile instance.  Here, we first resolve the ``status()`` command with
the ``.call("status")``, which simply located the function, then we can invoke
the call with no arguments.

For the rest of this example, we will use the interactive command client.  From
the graph, we can see that the root node holds a reference to ``group`` nodes.
We can access the "info" command on the current group like so:

.. code-block:: python

    c.group.info()

To access a specific group, regardless of whether or not it is current, we use
the Python mapping lookup syntax. This command sends group "b" to screen 1 (by
the :meth:`libqtile.config.Group.to_screen` method):

.. code-block:: python

    c.group["b"].to_screen(1)

In different contexts, it is possible to access a default object, where in
other contexts a key is required.  From the root of the graph, the current
``group``, ``layout``, ``screen`` and ``window`` can be accessed by simply
leaving the key specifier out. The key specifier is mandatory for ``widget``
and ``bar`` nodes.

With this context, we can now drill down deeper in the graph, following the
edges in the graphic above. To access the screen currently displaying group
"b", we can do this:

.. code-block:: python

    c.group["b"].screen.info()

Be aware, however, that group "b" might not currently be displayed. In that
case, it has no associated screen, the path resolves to a non-existent
node, and we get an exception:

.. code-block:: python

    libqtile.command.CommandError: No object screen in path 'group['b'].screen'


The graph is not a tree, since it can contain cycles. This path (redundantly)
specifies the group belonging to the screen that belongs to group "b":

.. code-block:: python

    c.group["b"].screen.group

This amount of connectivity makes it easy to reach out from a given object when
callbacks and events fire on that object to related objects.

.. _object_graph_keys:

Keys
====

The key specifier for the various object types are as follows:

.. list-table::
    :widths: 15 30 15 40
    :header-rows: 1

    * - Object
      - Key
      - Optional?
      - Example
    * - bar
      - "top", "bottom"
      - No
      - | c.screen.bar["bottom"]
    * - group
      - Name string
      - Yes
      - | c.group["one"]
        | c.group
    * - layout
      - Integer index
      - Yes
      - | c.layout[2]
        | c.layout
    * - screen
      - Integer index
      - Yes
      - | c.screen[1]
        | c.screen
    * - widget
      - Widget name
      - No
      - | c.widget["textbox"]
    * - window
      - Integer window ID
      - Yes
      - | c.window[123456]
        | c.window


Digging Deeper: Command Objects
===============================

If you just want to script your Qtile window manager the above information, in
addition to the documentation on the :ref:`various scripting
commands <scripting-commands>` should be enough to get started.  To develop
the Qtile manager itself, we can dig into how Qtile represents these objects,
which will lead to the way the commands are dispatched.

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
