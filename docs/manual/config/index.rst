=============
Configuration
=============

Qtile is configured in Python. A script (``~/.config/qtile/config.py`` by
default) is evaluated, and a small set of configuration variables are pulled
from its global namespace.

Configuration lookup order
==========================

Qtile looks in the following places for a configuration file, in order:

* The location specified by the ``-f`` argument.
* ``$XDG_CONFIG_HOME/qtile/config.py``, if it is set
* ``~/.config/qtile/config.py``
* It reads the module ``libqtile.resources.default_config``, included by
  default with every Qtile installation.

Default Configuration
=====================

The `default configuration
<https://github.com/qtile/qtile/blob/develop/libqtile/resources/default_config.py>`_
is invoked when qtile cannot find a configuration file. In addition, if qtile
is restarted via qsh, qtile will load the default configuration if the config
file it finds has some kind of error in it. The documentation below describes
the configuration lookup process, as well as what the key bindings are in the
default config.

The default config is not intended to be sutiable for all users; it's mostly
just there so qtile does /something/ when fired up, and so that it doesn't
crash and cause you to lose all your work if you reload a bad config.

Key Bindings
------------

The mod key for the default config is ``mod4``, which is typically bound to
the "Super" keys, which are things like the windows key and the mac control
key. The basic operation is:

* ``mod + k`` or ``mod + j``: switch windows on the current stack
* ``mod + <space>``: put focus on the other pane of the stack (when in stack
  layout)
* ``mod + <tab>``: switch layouts
* ``mod + w``: close window
* ``mod + <ctrl> + r``: restart qtile with new config
* ``mod + <group name>``: switch to that group
* ``mod + <shift> + <group name>``: send a window to that group
* ``mod + <enter>``: start xterm
* ``mod + r``: start a little prompt in the bar so users can run arbitrary
  commands

The default config defines one screen and 8 groups, one for each letter in
``qweruiop``. It has a basic bottom bar that includes a group box, the current
window name, a little text reminder that you're using the default config,
a system tray, and a clock.

The default configuration has several more advanced key combinations, but the
above should be enough for basic usage of qtile.

Mouse Bindings
--------------

By default, holding your ``mod`` key and clicking (and holding) a window will
allow you to drag it around as a floating window.


Configuration variables
=======================

A Qtile configuration consists of a file with a bunch of variables in it, which
qtile imports and then runs as a python file to derive its final configuration.
The documentation below describes the most common configuration variables; more
advanced configuration can be found in the `qtile-examples
<https://github.com/qtile/qtile-examples>`_ repository, which includes a number
of real-world configurations that demonstrate how you can tune Qtile to your
liking. (Feel free to issue a pull request to add your own configuration to the
mix!)

.. toctree::
    :maxdepth: 1

    groups
    keys
    layouts
    mouse
    screens
    hooks

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

Finally, if you're a gnome user, you can start integrate Qtile into Gnome's
session manager and use gnome as usual:

.. toctree::
    :maxdepth: 1

    gnome
