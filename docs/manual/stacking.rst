Window stacking
===============

A number of window commands (``move_up/down()``, ``bring_to_front()`` etc.) relate to
the stacking order of windows.

The aim of this page is to provide more details as to how stacking is implemented in Qtile.

.. important::

    Currently, stacking is only implemented in the X11 background. Support will be added to the
    Wayland backend in future and this page will be updated accordingly.

Layer priority groups
~~~~~~~~~~~~~~~~~~~~~

We have tried to adhere to the `EWMH specification`_. Windows are therefore stacked, from the bottom,
according to the following priority rules:

- windows of type _NET_WM_TYPE_DESKTOP
- windows having state _NET_WM_STATE_BELOW
- windows not belonging in any other layer
- windows of type _NET_WM_TYPE_DOCK (unless they have state
  _NET_WM_TYPE_BELOW) and windows having state _NET_WM_STATE_ABOVE
- focused windows having state _NET_WM_STATE_FULLSCREEN

Qtile had then added an additional layer so that ``Scratchpad`` windows are placed above everything else.

.. _EWMH specification: https://specifications.freedesktop.org/wm-spec/1.3/ar01s07.html#STACKINGORDER

Tiled windows will open in the default, "windows not belonging in any other layer", layer. If
``floats_kept_above`` is set to ``True`` in the config then new floating windows will have the
``_NET_WM_STATE_ABOVE`` property set which will ensure they remain above tiled windows.

Moving windows
~~~~~~~~~~~~~~

Imagine you have four tiled windows stacked (from the top) as follows:

.. code::

    "One"
    "Two"
    "Three"
    "Four"

If you call ``move_up()`` on window "Four", the result will be:

.. code::

    "One"
    "Two"
    "Four"
    "Three"

If you now call ``move_to_top()`` on window "Three", the result will be:

.. code::

    "Three"
    "One"
    "Two"
    "Four"

.. note::

    ``bring_to_front()`` has a special behaviour in Qtile. This will bring any window to the very top
    of the stack, disregarding the priority rules set out above. When that window loses focus, it will
    be restacked in the appropriate location.

    This can cause undesirable results if the config contains ``bring_front_click=True`` and the user has
    an app like a dock which is activated by mousing over the window. In this situation, tiled windows will
    be displayed above the dock making it difficult to activate. To fix this, set ``bring_front_click`` to
    ``False`` to disable the behaviour completely, or ``"floating_only"`` to only have this behaviour apply
    to floating windows.
