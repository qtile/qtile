Configuration
=============

Qtile is configured in Python. A script (``~/.config/qtile/config.py`` by
default) is evaluated, and a small set of configuration variables are pulled
from its global namespace.

Configuration variables
-----------------------

:doc:`groups </manual/config/groups>`
    A list of ``libqtile.config.Group`` objects which defines the group names.
    A group is a container for a bunch of windows, analogous to workspaces in
    other window managers. Each client window managed by the window manager
    belongs to exactly one group.

:doc:`keys </manual/config/keys>`
    A list of ``libqtile.config.Key`` objects which defines the keybindings.
    At a minimum, this will probably include bindings to switch between
    windows, groups and layouts.

:doc:`layouts </manual/config/layouts>`
    A list of layout objects, configuring the layouts you want to use.

:doc:`mouse </manual/config/mouse>`
    A list of ``libqtile.config.Drag`` and ``libqtile.config.Click`` objects
    defining mouse operations.

:doc:`screens </manual/config/screens>`
    A list of ``libqtile.config.Screen`` objects, which defines the physical
    screens you want to use, and the bars and widgets associated with them.
    Most of the visible "look and feel" configuration will happen in this
    section.

main()
    A function that executes after the window manager is initialized, but
    before groups, screens and other components are set up.

Putting it all together
-----------------------

The `qtile-examples <https://github.com/qtile/qtile-examples>`_ repository
includes a number of real-world configurations that demonstrate how you can
tune Qtile to your liking. (Feel free to issue a pull request to add your own
configuration to the mix!)

Testing your configuration
--------------------------

The best way to test changes to your configuration is with the provided Xephyr
script. This will run Qtile with your ``config.py`` inside a nested X server
and prevent your running instance of Qtile from crashing if something goes
wrong.

See :doc:`Hacking Qtile </manual/hacking>` for more information on using
Xephyr.
