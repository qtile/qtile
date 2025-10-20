========
Gestures
========

The ``gestures`` config file variable defines a set of global pointer actions, and
is a list of :class:`~libqtile.config.Swipe` and :class:`~libqtile.config.Pinch`
objects, which define what to do when a pointer gesture is detected.

:class:`~libqtile.config.Swipe` gestures trigger commands when a swipe matching the configured pattern
is detected. :class:`~libqtile.config.Pinch` gestures trigger commands when a pinching and/or rotating movement
is detected.

All gestures have a ``.fingers()`` method for finer control (e.g. you can specify a ``Swipe`` must have 4 fingers).
However, please note that you may find the server cannot always correctly identify the number of fingers, particularly
on a small touchpad. By default, finger count is therefore ignored.

Example
=======

::

    from libqtile.config import Pinch, Swipe
    gestures = [
        Swipe([], "D", lazy.window.toggle_minimize()),
        Swipe([mod], "DUD", lazy.reload_config()),
        Pinch([], lazy.screen.next_group()).clockwise(),
        Pinch([], lazy.screen.prev_group()).anticlockwise(),
        Pinch([mod], lazy.next_screen()).grow().clockwise(),    
    ]


Reference
=========

.. qtile_class:: libqtile.config.Swipe
   :no-commands:

.. qtile_class:: libqtile.config.Pinch
   :no-commands:
