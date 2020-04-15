====================
Running Inside Gnome
====================

Add the following snippet to your Qtile configuration. As per `this
page <https://wiki.gnome.org/Projects/SessionManagement/GnomeSession#A3._Register>`_,
it registers Qtile with gnome-session. Without it, a "Something has gone
wrong!" message shows up a short while after logging in. dbus-send must
be on your $PATH.

.. code-block:: python

    import subprocess
    import os
    from libqtile import hook

    @hook.subscribe.startup
    def dbus_register():
        id = os.environ.get('DESKTOP_AUTOSTART_ID')
        if not id:
            return
        subprocess.Popen(['dbus-send',
                          '--session',
                          '--print-reply',
                          '--dest=org.gnome.SessionManager',
                          '/org/gnome/SessionManager',
                          'org.gnome.SessionManager.RegisterClient',
                          'string:qtile',
                          'string:' + id])

This adds a new entry "Qtile GNOME" to GDM's login screen.

::

    $ cat /usr/share/xsessions/qtile_gnome.desktop
    [Desktop Entry]
    Name=Qtile GNOME
    Comment=Tiling window manager
    TryExec=/usr/bin/gnome-session
    Exec=gnome-session --session=qtile
    Type=XSession

The custom session for gnome-session.

For Gnome >= 3.23.2 (Ubuntu >= 17.04, Fedora >= 26, etc.)
:: 

    $ cat /usr/share/gnome-session/sessions/qtile.session
    [GNOME Session]
    Name=Qtile session
    RequiredComponents=qtile;org.gnome.SettingsDaemon.A11ySettings;org.gnome.SettingsDaemon.Clipboard;org.gnome.SettingsDaemon.Color;org.gnome.SettingsDaemon.Datetime;org.gnome.SettingsDaemon.Housekeeping;org.gnome.SettingsDaemon.Keyboard;org.gnome.SettingsDaemon.MediaKeys;org.gnome.SettingsDaemon.Mouse;org.gnome.SettingsDaemon.Power;org.gnome.SettingsDaemon.PrintNotifications;org.gnome.SettingsDaemon.Rfkill;org.gnome.SettingsDaemon.ScreensaverProxy;org.gnome.SettingsDaemon.Sharing;org.gnome.SettingsDaemon.Smartcard;org.gnome.SettingsDaemon.Sound;org.gnome.SettingsDaemon.Wacom;org.gnome.SettingsDaemon.XSettings;

Or for older Gnome versions

::

    $ cat /usr/share/gnome-session/sessions/qtile.session
    [GNOME Session]
    Name=Qtile session
    RequiredComponents=qtile;gnome-settings-daemon;

So that Qtile starts automatically on login.

::

    $ cat /usr/share/applications/qtile.desktop
    [Desktop Entry]
    Type=Application
    Encoding=UTF-8
    Name=Qtile
    Exec=qtile
    NoDisplay=true
    X-GNOME-WMName=Qtile
    X-GNOME-Autostart-Phase=WindowManager
    X-GNOME-Provides=windowmanager
    X-GNOME-Autostart-Notify=false

The above does not start gnome-panel. Getting gnome-panel to work
requires some extra Qtile configuration, mainly making the top and
bottom panels static on panel startup and leaving a gap at the top (and
bottom) for the panel window.

You might want to add keybindings to log out of the GNOME session.

.. code-block:: python

    Key([mod, 'control'], 'l', lazy.spawn('gnome-screensaver-command -l')),
    Key([mod, 'control'], 'q', lazy.spawn('gnome-session-quit --logout --no-prompt')),
    Key([mod, 'shift', 'control'], 'q', lazy.spawn('gnome-session-quit --power-off')),

The above apps need to be in your path (though they are typically
installed in ``/usr/bin``, so they probably are if they're installed
at all).
