# Qtile root object

The root node represents the main Qtile manager instance. Many of the commands
on this node are therefore related to the running of the application itself.

The root can access every other node in the command graph. Certain objects
can be accessed without a selector resulting in the current object being
selected (e.g. current group, screen, layout, window).

.. qtile_graph::
    :root: root

::: libqtile.core.manager.Qtile
    options:
      heading_level: 2
