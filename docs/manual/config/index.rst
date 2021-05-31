=============
Configuration
=============

Qtile is configured in Python. A script (``~/.config/qtile/config.py`` by
default) is evaluated, and a small set of configuration variables are pulled
from its global namespace.

Configuration lookup order
==========================

Qtile looks in the following places for a configuration file, in order:

* The location specified by the ``-c`` argument.
* ``$XDG_CONFIG_HOME/qtile/config.py``, if it is set
* ``~/.config/qtile/config.py``
* It reads the module ``libqtile.resources.default_config``, included by
  default with every Qtile installation.

Qtile will try to create the configuration file as a copy of the default
config, if it doesn't exist yet.

Default Configuration
=====================

The `default configuration
<https://github.com/qtile/qtile/blob/master/libqtile/resources/default_config.py>`_
is invoked when qtile cannot find a configuration file. In addition, if qtile
is restarted via qshell, qtile will load the default configuration if the
config file it finds has some kind of error in it. The documentation below
describes the configuration lookup process, as well as what the key bindings
are in the default config.

The default config is not intended to be suitable for all users; it's mostly
just there so qtile does /something/ when fired up, and so that it doesn't
crash and cause you to lose all your work if you reload a bad config.

Key Bindings
------------

The mod key for the default config is ``mod4``, which is typically bound to
the "Super" keys, which are things like the windows key and the mac command
key. The basic operation is:

* ``mod + k`` or ``mod + j``: switch windows on the current stack
* ``mod + <space>``: put focus on the other pane of the stack (when in stack
  layout)
* ``mod + <tab>``: switch layouts
* ``mod + w``: close window
* ``mod + <ctrl> + r``: restart qtile with new config
* ``mod + <group name>``: switch to that group
* ``mod + <shift> + <group name>``: send a window to that group
* ``mod + <enter>``: start terminal guessed by ``libqtile.utils.guess_terminal``
* ``mod + r``: start a little prompt in the bar so users can run arbitrary
  commands

The default config defines one screen and 8 groups, one for each letter in
``asdfuiop``. It has a basic bottom bar that includes a group box, the current
window name, a little text reminder that you're using the default config,
a system tray, and a clock.

The default configuration has several more advanced key combinations, but the
above should be enough for basic usage of qtile.

See :ref:`Keybindings in images <keybinding-img>` for visual
keybindings in keyboard layout.

Mouse Bindings
--------------

By default, holding your ``mod`` key and clicking (and holding) a window will
allow you to drag it around as a floating window.


Configuration variables
=======================

A Qtile configuration consists of a file with a bunch of variables in it, which
qtile imports and then runs as a Python file to derive its final configuration.
The documentation below describes the most common configuration variables; more
advanced configuration can be found in the `qtile-examples
<https://github.com/qtile/qtile-examples>`_ repository, which includes a number
of real-world configurations that demonstrate how you can tune Qtile to your
liking. (Feel free to issue a pull request to add your own configuration to the
mix!)

.. toctree::
    :maxdepth: 1

    lazy
    groups
    keys
    layouts
    mouse
    screens
    hooks

In addition to the above variables, there are several other boolean
configuration variables that control specific aspects of Qtile's behavior:

.. list-table::
    :widths: 10 10 80
    :header-rows: 1

    * - variable
      - default
      - description
    * - auto_fullscreen
      - True
      - If a window requests to be fullscreen, it is automatically
        fullscreened. Set this to false if you only want windows to be
        fullscreen if you ask them to be.
    * - bring_front_click
      - False
      - When clicked, should the window be brought to the front or not. If this
        is set to "floating_only", only floating windows will get affected (This
        sets the X Stack Mode to Above.)
    * - cursor_warp
      - False
      - If true, the cursor follows the focus as directed by the keyboard,
        warping to the center of the focused window. When switching focus between
        screens, If there are no windows in the screen, the cursor will warp to
        the center of the screen.
    * - dgroups_key_binder
      - None
      - A function which generates group binding hotkeys. It takes a single
        argument, the DGroups object, and can use that to set up dynamic key
        bindings.

        A sample implementation is available in `libqtile/dgroups.py
        <https://github.com/qtile/qtile/blob/master/libqtile/dgroups.py>`_
        called simple_key_binder(), which will bind groups to mod+shift+0-10 by
        default.
    * - dgroups_app_rules
      - []
      - A list of Rule objects which can send windows to various groups based
        on matching criteria.
    * - extension_defaults
      - same as `widget_defaults`
      - Default settings for extensions.
    * - floating_layout
      - layout.Floating(float_rules=[...])
      - The default floating layout to use. This allows you to set
        custom floating rules among other things if you wish.

        See the configuration file for the default `float_rules`.
    * - focus_on_window_activation
      - smart
      - Behavior of the _NET_ACTIVATE_WINDOW message sent by applications

        - urgent: urgent flag is set for the window

        - focus: automatically focus the window

        - smart: automatically focus if the window is in the current group

        - never: never automatically focus any window that requests it
    * - follow_mouse_focus
      - True
      - Controls whether or not focus follows the mouse around as it moves
        across windows in a layout.
    * - widget_defaults
      - dict(font='sans',
             fontsize=12,
             padding=3)
      - Default settings for bar widgets.
    * - reconfigure_screens
      - True
      - Controls whether or not to automatically reconfigure screens when there
        are changes in randr output configuration.
    * - wmname
      - "LG3D"
      - Gasp! We're lying here. In fact, nobody really uses or cares
        about this string besides java UI toolkits; you can see several
        discussions on the mailing lists, GitHub issues, and other WM
        documentation that suggest setting this string if your java app
        doesn't work correctly. We may as well just lie and say that
        we're a working one by default. We choose LG3D to maximize irony:
        it is a 3D non-reparenting WM written in java that happens to be
        on java's whitelist.
    * - auto_minimize
      - True
      - If things like steam games want to auto-minimize themselves when losing
        focus, should we respect this or not?


Testing your configuration
==========================

The best way to test changes to your configuration is with the provided Xephyr
script. This will run Qtile with your ``config.py`` inside a nested X server
and prevent your running instance of Qtile from crashing if something goes
wrong.

See :ref:`Hacking Qtile <hacking>` for more information on using
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

If there is no display manager such as SDDM, LightDM or other and there is need
to start Qtile directly from ``~/.xinitrc`` do that by adding ``exec qtile`` at
the end.

In very special cases, ex. Qtile crashing during session, then suggestion would
be to start through a loop to save running applications::

    while true; do
        qtile
    done

Finally, if you're a gnome user, you can start integrate Qtile into Gnome's
session manager and use gnome as usual.

.. toctree::
    :maxdepth: 1

    without-dm
    gnome
