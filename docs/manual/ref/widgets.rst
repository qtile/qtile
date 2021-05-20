.. _ref-widgets:

================
Built-in Widgets
================

.. qtile_module:: libqtile.widget
    :baseclass: libqtile.widget.base._Widget
    :no-commands:

Widget decorations
==================

Widgets can also be configured with ``Decoration`` objects to add additional
eye-candy.

The classes need to be imported into the user's config and can then be added to
widgets as follows:

::

    from libqtile.widget.decorations import RectDecoration



    decoration_config = {
        "decorations": [
            BorderDecoration(
                padding=2,
                padding_y=5,
                filled=True,
                dec_colour="#005555"
            )
        ],
        "padding": 6, 
    }


    screens = [
        Screen(
            bottom=bar.Bar(
                [
                    widget.Prompt(),
                    widget.Sep(),
                    widget.WindowName(),
                    widget.Sep(),
                    widget.Clock(format='%H:%M:%S %d.%m.%Y', **decoration_config),
                    widget.QuickExit(**decoration_config)
                ],
            24,
            ),
        )
    ]

The following decorations are available:

.. qtile_module:: libqtile.widget.decorations
    :baseclass: libqtile.widget.decorations._Decoration
    :no-commands: