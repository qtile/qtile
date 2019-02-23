lavinder-cmd
=========

This is a simple tool to expose lavinder.command functionality to shell.
This can be used standalone or in other shell scripts.

Examples:
---------

Output of ``lavinder-cmd -h``
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: text

    usage: lavinder-cmd [-h] [--object OBJ_SPEC [OBJ_SPEC ...]]
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
     lavinder-cmd
     lavinder-cmd -o cmd
     lavinder-cmd -o cmd -f prev_layout -i
     lavinder-cmd -o cmd -f prev_layout -a 3 # prev_layout on group 3
     lavinder-cmd -o group 3 -f focus_back

Output of ``lavinder-cmd -o group 3``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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

Output of ``lavinder-cmd -o cmd``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: text

    -o cmd -f add_rule              * Add a dgroup rule, returns rule_id needed to remove it
    -o cmd -f addgroup              * Add a group with the given name
    -o cmd -f commands                Returns a list of possible commands for this object
    -o cmd -f critical                Set log level to CRITICAL
    -o cmd -f debug                   Set log level to DEBUG
    -o cmd -f delgroup              * Delete a group with the given name
    -o cmd -f display_kb            * Display table of key bindings
    -o cmd -f doc                   * Returns the documentation for a specified command name
    -o cmd -f error                   Set log level to ERROR
    -o cmd -f eval                  * Evaluates code in the same context as this function
    -o cmd -f findwindow            * Launch prompt widget to find a window of the given name
    -o cmd -f focus_by_click        * Bring a window to the front
    -o cmd -f function              * Call a function with current object as argument
    -o cmd -f get_info                Prints info for all groups
    -o cmd -f get_state               Get pickled state for restarting lavinder
    -o cmd -f get_test_data           Returns any content arbitrarily set in the self.test_data attribute.
    -o cmd -f groups                  Return a dictionary containing information for all groups
    -o cmd -f hide_show_bar         * Toggle visibility of a given bar
    -o cmd -f info                    Set log level to INFO
    -o cmd -f internal_windows        Return info for each internal window (bars, for example)
    -o cmd -f items                 * Returns a list of contained items for the specified name
    -o cmd -f list_widgets            List of all addressible widget names
    -o cmd -f next_layout           * Switch to the next layout.
    -o cmd -f next_screen             Move to next screen
    -o cmd -f next_urgent             Focus next window with urgent hint
    -o cmd -f pause                   Drops into pdb
    -o cmd -f prev_layout           * Switch to the previous layout.
    -o cmd -f prev_screen             Move to the previous screen
    -o cmd -f lavinder_info              Returns a dictionary of info on the Qtile instance
    -o cmd -f lavindercmd              * Execute a Qtile command using the client syntax
    -o cmd -f remove_rule           * Remove a dgroup rule by rule_id
    -o cmd -f restart                 Restart lavinder
    -o cmd -f run_extension         * Run extensions
    -o cmd -f run_extention         * Deprecated alias for cmd_run_extension()
    -o cmd -f run_external          * Run external Python script
    -o cmd -f screens                 Return a list of dictionaries providing information on all screens
    -o cmd -f shutdown                Quit Qtile
    -o cmd -f simulate_keypress     * Simulates a keypress on the focused window.
    -o cmd -f spawn                 * Run cmd in a shell.
    -o cmd -f spawncmd              * Spawn a command using a prompt widget, with tab-completion.
    -o cmd -f status                  Return "OK" if Qtile is running
    -o cmd -f switch_groups         * Switch position of groupa to groupb
    -o cmd -f switchgroup           * Launch prompt widget to switch to a given group to the current screen
    -o cmd -f sync                    Sync the X display. Should only be used for development
    -o cmd -f to_layout_index       * Switch to the layout with the given index in self.layouts.
    -o cmd -f to_screen             * Warp focus to screen n, where n is a 0-based screen number
    -o cmd -f togroup               * Launch prompt widget to move current window to a given group
    -o cmd -f tracemalloc_dump        Dump tracemalloc snapshot
    -o cmd -f tracemalloc_toggle      Toggle tracemalloc status
    -o cmd -f warning                 Set log level to WARNING
    -o cmd -f windows                 Return info for each client window
