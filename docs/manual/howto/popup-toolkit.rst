.. _extended-popups:

============================
How to use the Popup Toolkit
============================

This guide explains how to create popups that can be used to add functionality
to widgets or create standalone launchers.

What's in the toolkit?
======================

The Toolkit has two types of object, a layout and a control. The layout is the
container that helps organise the presentation of the popup. The controls are the
objects that display the content.

A simple comparison would be to think of the ``Bar`` as the layout and widgets as the
controls. However, a key difference of this toolkit is that the controls can be placed
anywhere in a 2D space whereas widgets can only be ordered in one dimension.

Layouts
=======

The toolkit provides three layouts: ``PopupGridLayout``, ``PopupRelativeLayout`` and
``PopupAbsoluteLayout``.

Descriptions and configuration options of these layouts can be found on
:ref:`the reference page <ref-popup-layouts>`.

Controls
========

Currently, the following controls are provided:

- ``PopupText``: a simple text display object
- ``PopupImage``: a control to display an image
- ``PopupSlider``: a control to draw a line which marks a particular value (e.g. volume level)

Configuration options for these controls can be found on
:ref:`the reference page <ref-popup-controls>`.

Callbacks
=========

To add functionality to your popup, you need to bind callbacks to the individual controls. 
This is achieved in the same way as widgets i.e. a dictionary of ``mouse_callbacks`` is passed
as a configuration option for the control.

Building a popup
================

.. code:: python

    from libqtile import qtile
    from libqtile.lazy import lazy
    from libqtile.popup.toolkit import PopupGridLayout, PopupImage 

    controls = [
        PopupImage(
            filename='/path/to/power_icon.png',
            col=0,
            hover=True,
            mouse_callbacks = {
                'Button1': lazy.spawn('shutdown-command')
            }),
        PopupImage(
            filename='/path/to/lock_icon.png',
            col=1,
            hover=True,
            mouse_callbacks = {
                'Button1': lazy.spawn('lock-command')
            }),
        PopupImage(
            filename='/path/to/sleep_icon.png',
            col=2,
            hover=True,
            mouse_callbacks = {
                'Button1': lazy.spawn('sleep-command')
            }),
    ]

    layout = PopupGridLayout(
        width=400,
        height=75,
        rows=1,
        cols=3,
        controls=controls
    )

    # Place layout in center of screen and warp cursor.
    layout.show(centered=True, warp_cursor=True)

