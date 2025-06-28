qtile cmd-obj
=============

This is a simple tool to expose qtile.command functionality to shell.
This can be used standalone or in other shell scripts.

How it works
------------

``qtile cmd-obj`` works by selecting a command object and calling a specified function of that object.

As per :ref:`commands-api`, Qtile's command graph has seven nodes: ``layout``, ``window``, ``group``,
``bar``, ``widget``, ``screen``, and a special ``root`` node. These are the objects that can be accessed
via ``qtile cmd-obj``.

Running the command against a selected object without a function (``-f``) will run the ``help``
command and list the commands available to the object. Commands shown with an asterisk ("*") require
arguments to be passed via the ``-a`` flag.

Selecting an object
~~~~~~~~~~~~~~~~~~~

With the exception of ``cmd``, all objects need an identifier so the correct object can be selected. Refer to
:ref:`object_graph_selectors` for more information.

.. note::

    You will see from the graph on :ref:`commands-api` that certain objects can be accessed from other objects.
    For example, ``qtile cmd-obj -o group term layout`` will list the commands for the current layout on the
    ``term`` group.

Information on functions
~~~~~~~~~~~~~~~~~~~~~~~~

Running a function with the ``-i`` flag will provide additional detail about that function (i.e. what it does and what
arguments it expects).


Passing arguments to functions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Arguments can be passed to a function by using the ``-a`` flag. For example, to change the label for the group named "1"
to "A", you would run ``qtile cmd-obj -o group 1 -f set_label -a A``.

.. warning::

    It is not currently possible to pass non-string arguments to functions via ``qtile cmd-obj``. Doing so will
    result in an error.


Examples:
---------

Output of ``qtile cmd-obj -h``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: text

    usage: qtile cmd-obj [-h] [--object OBJ_SPEC [OBJ_SPEC ...]]
                     [--function FUNCTION] [--args ARGS [ARGS ...]] [--info]

    Simple tool to expose qtile.command functionality to shell.

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
     qtile cmd-obj
     qtile cmd-obj -o root  # same as above, root node is default
     qtile cmd-obj -o root -f prev_layout -i
     qtile cmd-obj -o root -f prev_layout -a 3 # prev_layout on group 3
     qtile cmd-obj -o group 3 -f focus_back
     qtile cmd-obj -o widget textbox -f update -a "New text"
     qtile cmd-obj -f restart # restart qtile

Output of ``qtile cmd-obj -o group 3``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: text

    -o group 3 -f commands            Returns a list of possible commands for this object
    -o group 3 -f doc               * Returns the documentation for a specified command name
    -o group 3 -f eval              * Evaluates code in the same context as this function
    -o group 3 -f focus_back          Focus the window that had focus before the current one got it.
    -o group 3 -f focus_by_name     * Focus the first window with the given name. Do nothing if the name is
    -o group 3 -f function          * Call a function with current object as argument
    -o group 3 -f info                Returns a dictionary of info for this group
    -o group 3 -f info_by_name      * Get the info for the first window with the given name without giving it
    -o group 3 -f items             * Returns a list of contained items for the specified name
    -o group 3 -f next_window         Focus the next window in group.
    -o group 3 -f prev_window         Focus the previous window in group.
    -o group 3 -f set_label         * Set the display name of current group to be used in GroupBox widget.
    -o group 3 -f setlayout
    -o group 3 -f switch_groups     * Switch position of current group with name
    -o group 3 -f toscreen          * Pull a group to a specified screen.
    -o group 3 -f unminimize_all      Unminimise all windows in this group

Output of ``qtile cmd-obj -o root``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: text

    -o root -f add_rule              * Add a dgroup rule, returns rule_id needed to remove it
    -o root -f addgroup              * Add a group with the given name
    -o root -f commands                Returns a list of possible commands for this object
    -o root -f critical                Set log level to CRITICAL
    -o root -f debug                   Set log level to DEBUG
    -o root -f delgroup              * Delete a group with the given name
    -o root -f display_kb            * Display table of key bindings
    -o root -f doc                   * Returns the documentation for a specified command name
    -o root -f error                   Set log level to ERROR
    -o root -f eval                  * Evaluates code in the same context as this function
    -o root -f findwindow            * Launch prompt widget to find a window of the given name
    -o root -f focus_by_click        * Bring a window to the front
    -o root -f function              * Call a function with current object as argument
    -o root -f get_info                Prints info for all groups
    -o root -f get_state               Get pickled state for restarting qtile
    -o root -f get_test_data           Returns any content arbitrarily set in the self.test_data attribute.
    -o root -f groups                  Return a dictionary containing information for all groups
    -o root -f hide_show_bar         * Toggle visibility of a given bar
    -o root -f info                    Set log level to INFO
    -o root -f internal_windows        Return info for each internal window (bars, for example)
    -o root -f items                 * Returns a list of contained items for the specified name
    -o root -f list_widgets            List of all addressible widget names
    -o root -f next_layout           * Switch to the next layout.
    -o root -f next_screen             Move to next screen
    -o root -f next_urgent             Focus next window with urgent hint
    -o root -f pause                   Drops into pdb
    -o root -f prev_layout           * Switch to the previous layout.
    -o root -f prev_screen             Move to the previous screen
    -o root -f qtile_info              Returns a dictionary of info on the Qtile instance
    -o root -f qtilecmd              * Execute a Qtile command using the client syntax
    -o root -f remove_rule           * Remove a dgroup rule by rule_id
    -o root -f restart                 Restart qtile
    -o root -f run_extension         * Run extensions
    -o root -f run_external          * Run external Python script
    -o root -f screens                 Return a list of dictionaries providing information on all screens
    -o root -f shutdown                Quit Qtile
    -o root -f simulate_keypress     * Simulates a keypress on the focused window.
    -o root -f spawn                 * Run cmd in a shell.
    -o root -f spawncmd              * Spawn a command using a prompt widget, with tab-completion.
    -o root -f status                  Return "OK" if Qtile is running
    -o root -f switch_groups         * Switch position of groupa to groupb
    -o root -f switchgroup           * Launch prompt widget to switch to a given group to the current screen
    -o root -f sync                    Sync the X display. Should only be used for development
    -o root -f to_layout_index       * Switch to the layout with the given index in self.layouts.
    -o root -f to_screen             * Warp focus to screen n, where n is a 0-based screen number
    -o root -f togroup               * Launch prompt widget to move current window to a given group
    -o root -f tracemalloc_dump        Dump tracemalloc snapshot
    -o root -f tracemalloc_toggle      Toggle tracemalloc status
    -o root -f warning                 Set log level to WARNING
    -o root -f windows                 Return info for each client window
