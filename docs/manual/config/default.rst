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

Configuration Lookup
--------------------

Qtile looks in the following places for a configuration file, in order:

* The location specified by the ``-f`` argument.
* ``$XDG_CONFIG_HOME/qtile/config.py``, if it is set
* ``~/.config/qtile/config.py``
* It reads the module ``libqtile.resources.default_config``, included by
  default with every qtile installation.

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
window name, a little text reminder that you're using the default, a system
tray, and a clock. you're using the default config.

The default configuration has several more advanced key combinations, but the
above should be enough for basic usage of qtile.
