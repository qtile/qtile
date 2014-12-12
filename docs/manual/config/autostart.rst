Autostart
=========

You might want to run some commands or spawn some applications when qtile
starts. There are lot of provided :doc:`Hooks </manual/config/hooks>`. In this
case, you might especially be interested in ``startup`` and ``startup_once``.
``startup_once`` is emtited only once when you start qtile. It is not emitted
on restarts. On the other side ``startup`` is emitted on the first start and
even on restarts.

Hooks can be subscribed in your config and you can respond to them anyhow you
want

.. code-block:: python

    @hook.subscribe.startup_once
    def autostart():
        # Do whatever you want


More advanced thing you might want to do is create autostart file with shell
commands. For instance ``~/.config/qtile/autostart.sh``. Don't forget to set
executable flag on it.


.. code-block:: bash

    #!/bin/sh
    feh --bg-scale ~/images/wallpaper.jpg &
    pidgin &
    dropbox start &


This kind of file can be run on qtile startup for example this way

.. code-block:: python

    import os
    import subprocess


    @hook.subscribe.startup_once
    def autostart():
        home = os.path.expanduser("~")
        subprocess.call([home + "/.config/qtile/autostart.sh"])
