Commands API
============

Qtile's command API is based on a graph of objects, where each object has a set
of associated commands. The graph and object commands are used in a number of
different places:

* Commands can be :doc:`bound to keys </manual/config/keys>` in the Qtile
  configuration file.
* Commands can be :doc:`called through qsh </manual/commands/qsh>`, the Qtile
  shell.
* Commands can be :doc:`called from a script </manual/commands/scripting>` to
  interact with Qtile from Python.

If the explanation below seems a bit complex, please take a moment to explore
the API using the ``qsh`` command shell. Command lists and detailed
documentation can be accessed from its built-in help command.


Object Graph
============

The objects in Qtile's object graph come in seven flavours, matching the seven
basic components of the window manager: ``layouts``, ``windows``, ``groups``,
``bars``, ``widgets``, ``screens``, and a special ``root`` node.  Objects are
addressed by a path specification that starts at the root, and follows the
edges of the graph. This is what the graph looks like:

.. image:: /_static/objgraph.png

Each arrow can be read as "holds a reference to". So, we can see that a
``widget`` object _holds a reference to_ objects of type ``bar``, ``screen``
and ``group``. Lets start with some simple examples of how the addressing
works. Which particular objects we hold reference to depends on the context -
for instance, widgets hold a reference to the screen that they appear on, and
the bar they are attached to.

Lets look at an example, starting at the root node. The following script runs
the ``status`` command on the root node, which, in this case, is represented by
the Client object:

::

    from libqtile.command import Client
    c = Client()
    print c.status()

From the graph, we can see that the root node holds a reference to
``group`` nodes. We can access the "info" command on the current group like
so:

::

    c.group.info()

To access a specific group, regardless of whether or not it is current, we use
the Python containment syntax. This command sends group "b" to screen 1:

::

    c.group["b"].to_screen(1)

The current ``group``, ``layout``, ``screen`` and ``window`` can be
accessed by simply leaving the key specifier out. The key specifier is
mandatory for ``widget`` and ``bar`` nodes.

We can now drill down deeper in the graph. To access the screen
currently displaying group "b", we can do this:

::

    c.group["b"].screen.info()

Be aware, however, that group "b" might not currently be displayed. In that
case, it has no associated screen, the path resolves to a non-existent
node, and we get an exeption:

::

    libqtile.command.CommandError: No object screen in path 'group['b'].screen'

The graph is not a tree, since it can contain cycles. This path (redundantly)
specifies the group belonging to the screen that belongs to group "b":

::

    c.group["b"].screen.group()

Keys
====

The key specifier for the various object types are as follows:

+--------+-------------------+-----------+--------------------------+
| Object | Key               | Optional? | Example                  |
+========+===================+===========+==========================+
| bar    | "top", "bottom"   | No        | - c.screen.bar["bottom"] |
+--------+-------------------+-----------+--------------------------+
| group  | Name string       | Yes       | - c.group["one"]         |
|        |                   |           | - c.group                |
+--------+-------------------+-----------+--------------------------+
| layout | Integer offset    | Yes       | - c.layout[2]            |
|        |                   |           | - c.layout               |
+--------+-------------------+-----------+--------------------------+
| screen | Integer offset    | Yes       | - c.screen[1]            |
|        |                   |           | - c.screen               |
+--------+-------------------+-----------+--------------------------+
| widget | Widget name       | No        | - c.widget["textbox"]    |
+--------+-------------------+-----------+--------------------------+
| window | Integer window ID | Yes       | - c.window[123456]       |
|        |                   |           | - c.window               |
+--------+-------------------+-----------+--------------------------+
