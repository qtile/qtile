dlavinder-cmd
==========

A Rofi/dmenu interface to lavinder-cmd. Accepts all arguments of lavinder-cmd.

Examples:
---------

Output of ``dlavinder-cmd -o cmd``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. image:: dlavinder-cmd.png

Output of ``dlavinder-cmd -h``
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: text

    dlavinder-cmd

        A Rofi/dmenu interface to lavinder-cmd. Excepts all arguments of lavinder-cmd
        (see below).

    usage: dlavinder-cmd [-h] [--object OBJ_SPEC [OBJ_SPEC ...]]
                      [--function FUNCTION] [--args ARGS [ARGS ...]] [--info]

    Simple tool to expose lavinder.command functionality to shell.

    optional arguments:
      -h, --help            show this help message and exit
      --object OBJ_SPEC [OBJ_SPEC ...], -o OBJ_SPEC [OBJ_SPEC ...]
                            Specify path to object (space separated). If no
                            --function flag display available commands.
      --function FUNCTION, -f FUNCTION
                            Select function to execute.
      --args ARGS [ARGS ...], -a ARGS [ARGS ...]
                            Set arguments supplied to function.
      --info, -i            With both --object and --function args prints
                            documentation for function.

    Examples:
     dlavinder-cmd
     dlavinder-cmd -o cmd
     dlavinder-cmd -o cmd -f prev_layout -i
     dlavinder-cmd -o cmd -f prev_layout -a 3 # prev_layout on group 3
     dlavinder-cmd -o group 3 -f focus_back

    If both rofi and dmenu are present rofi will be selected as default, to change this us --force-dmenu as the first argument.
