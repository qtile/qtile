Configuration
=============

Qtile is configured in Python. A script (``~/.config/qtile/config.py`` by
default) is evaluated, and a small set of configuration variables are pulled
from its global namespace.

----

:doc:`/manual/config/groups`

A list of ``libqtile.manager.Group`` objects which defines the group names.

----

:doc:`/manual/config/keys`

A list of ``libqtile.manager.Key`` objects which defines the keybindings. At a
minimum, this will probably include bindings to switch between windows, groups
and layouts.

----

:doc:`/manual/config/layouts`

A list layout objects, configuring the layouts you want to use.

----

:doc:`/manual/config/mouse`

A list of ``libqtile.manager.Drag`` and ``libqtile.manager.Click`` objects
defining mouse operations.

----

:doc:`/manual/config/screens`

A list of ``libqtile.manager.Screen`` objects, which defines the physical
screens you want to use, and the bars and widgets associated with them. Most of
the visible "look and feel" configuration will happen in this section.

----

main

A function that executes after the window manager is initialized, but before
groups, screens and other components are set up. There are few reasons to use
this, other than testing and debugging.

----

Putting it all together
-----------------------

The qtile-examples repository includes a number of real-world configurations
that demonstrate how you can tune Qtile to your liking.

https://github.com/qtile/qtile-examples
