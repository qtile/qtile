
The Command Graph
=================

The objects in Qtile's command graph come in eight flavours, matching the eight
basic components of the window manager: ``layouts``, ``windows``, ``groups``,
``bars``, ``widgets``, ``screens``, ``core``, and a special ``root`` node.
Objects are addressed by a path specification that starts at the root and
follows the available paths in the graph. This is what the graph looks like:

.. qtile_graph::
    :root: all
    :api_page_root: api/

Each arrow can be read as "holds a reference to". So, we can see that a
``widget`` object *holds a reference to* objects of type ``bar`` and ``screen``. 
Let's start with some simple examples of how the addressing
works. Which particular objects we hold reference to depends on the context -
for instance, widgets hold a reference to the screen that they appear on, and
the bar they are attached to.

Let's look at an example, starting at the root node. The following script runs
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
    print(c.call("status"))

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
the :meth:`libqtile.config.Group.toscreen` method):

.. code-block:: python

    c.group["b"].toscreen(1)

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
