=============
Configuration
=============

Qtile is configured in Python. A script (*~/.config/qtile/config.py* by
default) is evaluated, and a small set of configuration variables are pulled
from its global namespace. 

.. # Variables


Groups
======

The ``groups`` config file variable should be initialized to a list of
``libqtile.manager.Group`` objects, which defines the group names.

``libqtile.manager.Group``
--------------------------

A group is a container for a bunch of windows, analogous to workspaces
in other window managers. Each client window managed by the window
manager belongs to exactly one group.

.. TODO: There was a table here showing the possible commands.

Example
-------

.. code-block:: python

  from libqtile.manager import Group
  groups = [
      Group("a"),
      Group("b"),
      Group("c"),
  ]


Keys
====

A list of ``libqtile.manager.Key`` objects which defines the key bindings. At a
minimum, this will probably include bindings to switch between windows, groups
and layouts. The ``keys`` configuration variable defines Qtile's key bindings. 

``libqtile.manager.Key``
------------------------

.. code-block:: python

  class Key:
      def __init__(self, modifiers, key, *commands):
          ...

modifiers
  A list of modifier specifications. Modifier
  specifications are one of: "shift", "lock", "control", "mod1",
  "mod2", "mod3", "mod4", "mod5".

key
  A key specification, e.g. "a", "Tab", "Return", "space".

\*commands
  A list of lazy command objects generated with the
  command.lazy helper. If multiple Call objects are specified, they
  are run in sequence.


The ``command.lazy`` object
---------------------------

``command.lazy`` is a special helper object to specify a command for later
execution. This object acts like the root of the object graph, which means that
we can specify a key binding command with the same syntax used to call the
command through a script or through ``qsh``.

.. TODO: link to qsh in the above paragraph.


Example
-------

.. code-block:: python

  from libqtile.manager import Key
  keys = [
      Key(
          ["mod1"], "k",
          command.lazy.layout.down()
      ),
      Key(
          ["mod1"], "j",
          lazy.layout.up()
      )
  ]


On my system ``mod1`` is the Alt key - you can see which modifiers map to which
keys on your system by running the ``xmodmap`` command. This example binds
``Alt-k`` to the "down" command on the current layout. This command is standard
on all the included layouts, and switches to the next window (where "next" is
defined differently in different layouts). The matching "up" command switches
to the previous window.


Layouts
=======

A layout is an algorithm for laying out windows in a group on your screen.
Since Qtile is a tiling window manager, this usually means that we try to use
space as efficiently as possible, and give the user ample commands that can be
bound to keys to interact with layouts. 

The ``layouts`` variable defines the list of layouts you will use with Qtile.
The first layout in the list is the default. If you define more than one
layout, you will probably also want to define key bindings to let you switch to
the next and previous layouts.


Built-in layouts
----------------

.. TODO: $!confobj("libqtile.layout.Max")!$

.. TODO: $!confobj("libqtile.layout.Stack")!$

.. TODO: $!confobj("libqtile.layout.Tile")!$


Example
-------

.. code-block:: python

  from libqtile import layout
  layouts = [
      layout.Max(),
      layout.Stack(stacks=2)
  ]


``main``
========

A function that executes after the window manager is initialized, but before
groups, screens and other components are set up. There are few reasons to use
this, other than testing and debugging.


Mouse
=====

The ``mouse`` config file variable defines a set of global mouse actions, and
is a list of ``libqtile.manager.Click`` and ``libqtile.manager.Drag`` objects.

.. TODO: $!confobj("libqtile.manager.Click")!$

.. TODO: $!confobj("libqtile.manager.Drag")!$


Example
-------

.. code-block:: python

  from libqtile.manager import Click, Drag
  mouse = [
      Drag([mod], "Button1", lazy.window.set_position_floating(),
          start=lazy.window.get_position()),
      Drag([mod], "Button3", lazy.window.set_size_floating(),
          start=lazy.window.get_size()),
      Click([mod], "Button2", lazy.window.bring_to_front())
  ]


Screens
=======

The ``screens`` configuration variable, a list of ``libqtile.manager.Screen``
objects, is where the physical screens, their associated ``bars``, and the
``widgets`` contained within the bars are defined. Most of the visible
"look and feel" configuration will happen in this section.


Screens
-------

.. TODO: $!confobj("libqtile.manager.Screen")!$


Bars
----

.. TODO: $!confobj("libqtile.bar.Bar")!$

.. TODO: $!confobj("libqtile.bar.Gap")!$


Widgets
-------

.. TODO: $!confobj("libqtile.widget.Clock", "clock.png")!$

.. TODO: $!confobj("libqtile.widget.GroupBox", "groupbox.png")!$

.. TODO: $!confobj("libqtile.widget.AGroupBox")!$

.. TODO: $!confobj("libqtile.widget.Prompt")!$

.. TODO: $!confobj("libqtile.widget.Sep")!$

.. TODO: $!confobj("libqtile.widget.Spacer")!$

.. TODO: $!confobj("libqtile.widget.Systray", "systray.png")!$

.. TODO: $!confobj("libqtile.widget.TextBox")!$

.. TODO: $!confobj("libqtile.widget.WindowName")!$


Graphs
------ 

.. TODO: <img src="@!urlTo('graph.png')!@"/>

.. TODO: $!confobj("libqtile.widget.CPUGraph")!$

.. TODO: $!confobj("libqtile.widget.MemoryGraph")!$

.. TODO: $!confobj("libqtile.widget.SwapGraph")!$


Example
-------

Tying together screens, bars and widgets, we get something like this:

.. code-block:: python

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


Hooks
=====

Qtile has an extensive set of hooks that users can bind functions to. 

.. warning::

  Be careful when writing hooks - they run in the context of the Qtile
  process, and have complete access to all of Qtile's internal object APIs. 
  This means they can be arbitrarily powerful, but they can also crash Qtile
  or corrupt its data structures.


Normally, hooks are subscribed to in the Qtile configuration file. Hooks are
exposed on the ``hook.subscribe`` object. The following code will print the
client name to ``stderr`` (which will show up in your *.xsession-errors* file)
whenever focus changes.

.. code-block:: python

  from libqtile import hook
    
  def mymethod(c):
      print >> sys.stderr, c.name
    
  hook.subscribe.client_focus(mymethod)

.. TODO: $!hookobj("libqtile.hook.Subscribe")!$
.. TODO: List of hooks
..  TODO: Example showing a hook being used. Should show which module its being
    imported from.
..  TODO: Create something similar to xmonad.start. If this is implemented, then
    explain the difference between using this and something like .xinitrc and 
    qtile startup hook.
.. TODO: Insert hooks API documentation


Complete example
================

.. TODO: Examples should probably reside inside the docs directory.

.. literalinclude:: ../examples/config/cortesi-config.py