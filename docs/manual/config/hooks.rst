=====
Hooks
=====

Qtile provides a mechanism for subscribing to certain events in ``libqtile.hook``.
To subscribe to a hook in your configuration, simply decorate a function with
the hook you wish to subscribe to.

See :doc:`/manual/ref/hooks` for a listing of available hooks.

Examples
========

Automatic floating dialogs
--------------------------

Let's say we wanted to automatically float all dialog windows (this code is not
actually necessary; Qtile floats all dialogs by default). We would subscribe to
the ``client_new`` hook to tell us when a new window has opened and, if the
type is "dialog", as can set the window to float. In our configuration file it
would look something like this:

.. code-block:: python

    from libqtile import hook

    @hook.subscribe.client_new
    def floating_dialogs(window):
        dialog = window.window.get_wm_type() == 'dialog'
        transient = window.window.get_wm_transient_for()
        if dialog or transient:
            window.floating = True

A list of available hooks can be found in the
:doc:`Built-in Hooks </manual/ref/hooks>` reference.

Autostart
---------

If you want to run commands or spawn some applications when Qtile starts, you'll
want to look at the ``startup`` and ``startup_once`` hooks. ``startup`` is
emitted every time Qtile starts (including restarts), whereas ``startup_once``
is only emitted on the very first startup.

Let's create a file ``~/.config/qtile/autostart.sh`` that will set our desktop
wallpaper and start a few programs when Qtile first runs.

.. code-block:: bash

    #!/bin/sh
    feh --bg-scale ~/images/wallpaper.jpg &
    pidgin &
    dropbox start &

We can then subscribe to ``startup_once`` to run this script:

.. code-block:: python

    import os
    import subprocess

    @hook.subscribe.startup_once
    def autostart():
        home = os.path.expanduser('~/.config/qtile/autostart.sh')
        subprocess.call([home])
