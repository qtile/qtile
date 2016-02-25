====
iqsh
====

In addition to the standard ``qsh`` shell interface, we provide a kernel
capable of running through Jupyter that hooks into the qsh client.  The command
structure and syntax is the same as qsh, so it is recommended you read that for
more information about that.

Dependencies
============

In order to run iqsh, you must have ``ipykernel`` and ``jupyter_console``.  You
can install the dependencies when you are installing qtile by running:

.. code-block:: bash

    $ pip install qtile[ipython]

Otherwise, you can just install these two packages separately.

Installing and Running the Kernel
=================================

Once you have the required dependencies, you can run the kernel right away by running:

.. code-block:: bash

    $ python -m libqtile.interactive.iqsh_kernel

However, this will merely spawn a kernel instance, you will have to run a
separate frontend that connects to this kernel.

A more convenient way to run the kernel is by registering the kernel with
Jupyter.  To register the kernel itself, run:

.. code-block:: bash

    $ python -m libqtile.interactive.iqsh_install

If you run this as a non-root user, or pass the ``--user`` flag, this will
install to the user Jupyter kernel directory.  You can now invoke the kernel
directly when starting a Jupyter frontend, for example:

.. code-block:: bash

    $ jupyter console --kernel qsh

The ``iqsh`` script will launch a Jupyter terminal console with the qsh kernel.

iqsh vs qsh
===========

One of the main drawbacks of running through a Jupyter kernel is the frontend
has no way to query the current node of the kernel, and as such, there is no
way to set a custom prompt.  In order to query your current node, you can call
``pwd``.

This, however, enables many of the benefits of running in a Jupyter frontend,
including being able to save, run, and re-run code cells in frontends such as
the Jupyter notebook.

The Jupyter kernel also enables more advanced help, text completion, and
introspection capabilities (however, these are currently not implemented at a
level much beyond what is available in the standard qsh).
