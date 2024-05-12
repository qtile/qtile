.. _qtile-shell:

===========
qtile shell
===========

The Qtile command shell is a command-line shell interface that provides access
to the full complement of Qtile command functions. The shell features command
name completion, and full command documentation can be accessed from the shell
itself. The shell uses GNU Readline when it's available, so the interface can
be configured to, for example, obey VI keybindings with an appropriate
``.inputrc`` file. See the GNU Readline documentation for more information.


Navigating the Object Graph
===========================

The shell presents a filesystem-like interface to the command graph - the
builtin "cd" and "ls" commands act like their familiar shell counterparts:

.. code-block:: bash

    > ls
    layout/  widget/  screen/  bar/     window/  group/

    > cd screen
    layout/  window/  bar/  widget/

    > cd ..
    /

    > ls
    layout/  widget/  screen/  bar/     window/  group/

If you try to access an object that has no "default" value then you will see an
error message:

.. code-block:: bash

    > ls
    layout/  widget/  screen/  bar/     window/  group/

    > cd bar
    Item required for bar

    > ls bar
    bar[bottom]/

    > cd bar/bottom
    bar['bottom']> ls
    screen/  widget/

Please refer to :ref:`object_graph_selectors` for a summary of which objects need a
specified selector and the type of selector required. Using ``ls`` will show
which selectors are available for an object. Please see below for an explanation
about how Qtile displays shell paths.

Alternatively, the ``items()`` command can be run on the parent object to show which
selectors are available. The first value shows whether a selector is optional
(``False`` means that a selector is required) and the second value is a list of
selectors:

.. code-block:: bash

    > ls
    layout/  widget/  screen/  bar/     window/  group/

    > items(bar)
    (False, ['bottom'])

Displaying the shell path
=========================

Note that the shell provides a "short-hand" for specifying node keys (as
opposed to children). The following is a valid shell path:

.. code-block:: bash

    > cd group/4/window/31457314

The command prompt will, however, always display the Python node path that
should be used in scripts and key bindings:

.. code-block:: bash

    group['4'].window[31457314]>

Live Documentation
==================

The shell ``help`` command provides the canonical documentation for the Qtile
API:

.. code-block:: bash

    > cd layout/1

    layout[1]> help
    help command   -- Help for a specific command.

    Builtins
    ========
    cd    exit  help  ls    q     quit

    Commands for this object
    ========================
    add           commands      current       delete        doc
    down          get_info      items         next          previous
    rotate        shuffle_down  shuffle_up    toggle_split  up

    layout[1]> help previous
    previous()
    Focus previous stack.
