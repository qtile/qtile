=========
qtile top
=========

``qtile top`` is a ``top``-like tool to measure memory usage of Qtile's internals.

.. note::

  To use ``qtile top`` you need to have ``tracemalloc`` enabled. You can do this by
  setting the environmental variable ``PYTHONTRACEMALLOC=1`` before starting qtile.
  Alternatively, you can force start ``tracemalloc`` but you will lose early traces:

  .. code-block::

    >>> from libqtile.command.client import InteractiveCommandClient
    >>> i=InteractiveCommandClient()
    >>> i.eval("import tracemalloc;tracemalloc.start()")
