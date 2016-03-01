===
qsh
===

The Qtile command shell is a command-line shell interface that provides access
to the full complement of Qtile command functions. The shell features command
name completion, and full command documentation can be accessed from the shell
itself. The shell uses GNU Readline when it's available, so the interface can
be configured to, for example, obey VI keybindings with an appropriate
``.inputrc`` file. See the GNU Readline documentation for more information.


Navigating the Object Graph
===========================

The shell presents a filesystem-like interface to the object graph - the
builtin "cd" and "ls" commands act like their familiar shell counterparts:

.. code-block:: bash

    > ls
    layout/  widget/  screen/  bar/     window/  group/

    > cd bar

    bar> ls
    bottom/

    bar> cd bottom

    bar['bottom']> ls
    screen/

    bar['bottom']> cd ../..

    > ls
    layout/  widget/  screen/  bar/     window/  group/

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
    down          get info      items         next          previous
    rotate        shuffle_down  shuffle_up    toggle_split  up

    layout[1]> help previous
    previous()
    Focus previous stack.

Reference
=========

Qsh
---

.. autoclass:: libqtile.sh.QSh

   .. automethod:: libqtile.sh.QSh.do_cd

   .. automethod:: libqtile.sh.QSh.do_exit

   .. automethod:: libqtile.sh.QSh.do_ls

   .. automethod:: libqtile.sh.QSh.do_pwd

   .. automethod:: libqtile.sh.QSh.do_help
