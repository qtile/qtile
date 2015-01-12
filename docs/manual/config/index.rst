=============
Configuration
=============

Qtile is configured in Python. A script (``~/.config/qtile/config.py`` by
default) is evaluated, and a small set of configuration variables are pulled
from its global namespace.

.. toctree::
    :maxdepth: 2

    default
    gnome

Configuration lookup order
==========================

Qtile looks in the following places for a configuration file, in order:

* The location specified by the ``-f`` argument.
* ``$XDG_CONFIG_HOME/qtile/config.py``, if it is set
* ``~/.config/qtile/config.py``
* It reads the module ``libqtile.resources.default_config``, included by
  default with every Qtile installation.

Configuration variables
=======================

.. toctree::
    :maxdepth: 1

    groups
    keys
    layouts
    mouse
    screens
    hooks

groups
------

A list of ``libqtile.config.Group`` objects which defines the group names.
A group is a container for a bunch of windows, analogous to workspaces in
other window managers. Each client window managed by the window manager
belongs to exactly one group.

keys
----

A list of ``libqtile.config.Key`` objects which defines the keybindings.
At a minimum, this will probably include bindings to switch between
windows, groups and layouts.

layouts
-------

A list of layout objects, configuring the layouts you want to use.

mouse
-----

A list of ``libqtile.config.Drag`` and ``libqtile.config.Click`` objects
defining mouse operations.

screens
-------

A list of ``libqtile.config.Screen`` objects, which defines the physical
screens you want to use, and the bars and widgets associated with them.
Most of the visible "look and feel" configuration will happen in this
section.

main()
------

A function that executes after the window manager is initialized, but
before groups, screens and other components are set up.

Putting it all together
=======================

The `qtile-examples <https://github.com/qtile/qtile-examples>`_ repository
includes a number of real-world configurations that demonstrate how you can
tune Qtile to your liking. (Feel free to issue a pull request to add your own
configuration to the mix!)

Testing your configuration
==========================

The best way to test changes to your configuration is with the provided Xephyr
script. This will run Qtile with your ``config.py`` inside a nested X server
and prevent your running instance of Qtile from crashing if something goes
wrong.

See :doc:`Hacking Qtile </manual/hacking>` for more information on using
Xephyr.

Starting Qtile
==============

There are several ways to start Qtile. The most common way is via an entry in
your X session manager's menu. The default Qtile behavior can be invoked by
creating a `qtile.desktop
<https://github.com/qtile/qtile/blob/master/resources/qtile.desktop>`_ file in
``/usr/share/xsessions``.

A second way to start Qtile is a custom X session. This way allows you to
invoke Qtile with custom arguments, and also allows you to do any setup you
want (e.g. special keyboard bindings like mapping caps lock to control, setting
your desktop background, etc.) before Qtile starts. If you're using an X
session manager, you still may need to create a ``custom.desktop`` file similar
to the ``qtile.desktop`` file above, but with ``Exec=/etc/X11/xsession``. Then,
create your own ``~/.xsession``. There are several examples of user defined
``xsession`` s in the `qtile-examples
<https://github.com/qtile/qtile-examples>`_ repository.
