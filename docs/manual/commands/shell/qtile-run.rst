=============
qtile run-cmd
=============

Run a command applying rules to the new windows, ie, you can start a window in
a specific group, make it floating, intrusive, etc.

The Windows must have NET_WM_PID.

.. code-block:: bash

    # run xterm floating on group "test-group"
    qtile run-cmd -g test-group -f xterm
