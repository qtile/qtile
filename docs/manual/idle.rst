Idle events
===========

Qtile supports idle events natively on both the X11 and Wayland backends. Custom actions can
be triggered after a specified period of inactivity. In addition, users can define rules to
prevent idle timers from activating (e.g. when a video player is fullscreened.).

The Wayland backend includes support for the ``ext_idle_notifier_v1`` and ``zwp_idle_inhibit_manager_v1``
protocols. This means clients like ``swayidle`` are supported by qtile.

.. note::

    If an inhibitor prevents a timer from firing, the timer will not be fired if the inhibitor is removed
    and the system is still in an idle state. Similarly, a resume action will not be fired when exiting the
    idle state if there was an active inhibitor when the timeout period was completed. 

Idle timers
~~~~~~~~~~~

Timers are defined in the ``idle_timers`` section of the config file. This should be a list
of ``IdleTimer`` objects.

.. code:: python

     from libqtile.config import IdleTimer
     from libqtile.lazy import lazy

     idle_timers = [
        IdleTimer(300, action=lazy.spawn("/path/to/screen_dimmer.sh"), resume=lazy.spawn("/path/to/restore_screen.sh")),
        IdleTimer(900, action=lazy.spawn("/path/to/screen_off.sh"))
     ]

.. qtile_class:: libqtile.config.IdleTimer

Idle inhibitors
~~~~~~~~~~~~~~~

An active idle inhibitor will prevent a timer action being triggered. Users can define rules for
inhibitors in the ``idle_inhibitors`` section of the config file. This is a list of ``IdleInhibitor``
objects. Each inhibitor defines a ``Match`` to check whether the rule should apply to a window. There is
also a setting to determine what state the window must be in to activate the inhibitor.

.. code:: python

     from libqtile.config import IdleInhibitor, Match
     from libqtile.lazy import lazy

     idle_inhibitors = [
        IdleInhibitor(match=Match(wm_class="vlc"), when="fullscreen"),
     ]

.. qtile_class:: libqtile.config.IdleInhibitor
