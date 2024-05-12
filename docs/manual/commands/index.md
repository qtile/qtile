.. _commands-api:

============
Architecture
============

This page explains how Qtile's API works and how it can be accessed. Users who just
want to find a list of commands can jump to :doc:`the API commands page <api/index>`.

Qtile's command API is based on a graph of objects, where each object has a set
of associated commands, combined with a number of interfaces that are used
to navigate the graph and execute associated commands.

This page gives an overview of the command graph and the various interfaces
accessible by users. The documentation also contains details of all the commands
that are exposed by objects on the graph.

.. note::

  While users are able to access the internal python objects (e.g. via a ``qtile``
  instance), this is not part of the "official" API. These objects and method are
  not currently included in the documentation but can be viewed by looking at the
  source code on github. Changes to commonly-used internal objects will be kept to
  a minimum.

The graph and object commands are used in a number of
different places:

* Commands can be :ref:`bound to keys <config-keys>` in the Qtile
  configuration file using the ``lazy`` interface.
* Commands can be called from a script using one of the various :ref:`available interfaces
  <scripting-interfaces>` to interact with Qtile from Python or shell scripts.

A couple of additional options are available if you are looking for more
interactive access:

* Commands can be :ref:`called through qtile shell <qtile-shell>`, the
  Qtile shell.
* The shell can also be hooked into a Jupyter kernel :ref:`called iqshell
  <iqshell>` (NB this interface is currently broken).

If the explanations in the pages below seems a bit complex, please take a moment to explore
the API using the ``qtile shell`` command shell. The shell provides a way to
navigate the graph, allowing you to see how nodes are connected. Available nodes
can be displayed with the ``ls`` command while command lists and detailed documentation
can be accessed from the built-in ``help`` command. Commands can also be executed
from this shell.

.. toctree::
    :maxdepth: 1

    command_graph
    navigation
    advanced
