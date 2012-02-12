Screens
=======

The ``screens`` configuration variable is where the physical screens, their
associated ``bars``, and the ``widgets`` contained within the bars are defined.

screens
~~~~~~~

$!confobj("libqtile.manager.Screen")!$

bars
~~~~

$!confobj("libqtile.bar.Bar")!$

$!confobj("libqtile.bar.Gap")!$

widgets
~~~~~~~

$!confobj("libqtile.widget.Clock", "clock.png")!$

.. image:: /_static/clock.png

$!confobj("libqtile.widget.GroupBox", "groupbox.png")!$

.. image:: /_static/groupbox.png

$!confobj("libqtile.widget.AGroupBox")!$

$!confobj("libqtile.widget.Prompt")!$

$!confobj("libqtile.widget.Sep")!$

$!confobj("libqtile.widget.Spacer")!$

$!confobj("libqtile.widget.Systray", "systray.png")!$

.. image:: /_static/systray.png

$!confobj("libqtile.widget.TextBox")!$

$!confobj("libqtile.widget.WindowName")!$

Graphs
~~~~~~

.. image:: /_static/graph.png

$!confobj("libqtile.widget.CPUGraph")!$

$!confobj("libqtile.widget.MemoryGraph")!$

$!confobj("libqtile.widget.SwapGraph")!$


Example
~~~~~~~

Tying together screens, bars and widgets, we get something like this:

::

    from libqtile.manager import Screen
    from libqtile import bar, widget
    screens = [
        Screen(
            bottom = bar.Bar(
                        [
                            widget.GroupBox(),
                            widget.WindowName()
                        ],
                        30,
                    ),
        ),
        Screen(
            bottom = bar.Bar(
                        [
                            widget.GroupBox(),
                            widget.WindowName()
                        ],
                        30,
                    ),
        )
    ]
