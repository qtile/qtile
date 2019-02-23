======
Groups
======

A group is a container for a bunch of windows, analogous to workspaces in other
window managers. Each client window managed by the window manager belongs to
exactly one group. The ``groups`` config file variable should be initialized to
a list of :class:`~liblavinder.dgroups.DGroup` objects.

:class:`~liblavinder.dgroups.DGroup` objects provide several options for group
configuration. Groups can be configured to show and hide themselves when
they're not empty, spawn applications for them when they start, automatically
acquire certain groups, and various other options.

Example
-------

::

    from liblavinder.config import Group, Match
    groups = [
        Group("a"),
        Group("b"),
        Group("c", matches=[Match(wm_class=["Firefox"])]),
    ]

    # allow mod3+1 through mod3+0 to bind to groups; if you bind your groups
    # by hand in your config, you don't need to do this.
    from liblavinder.dgroups import simple_key_binder
    dgroups_key_binder = simple_key_binder("mod3")


Reference
---------

.. lavinder_class:: liblavinder.config.Group
   :no-commands:

.. autofunction:: liblavinder.dgroups.simple_key_binder

Group Matching
==============

.. lavinder_class:: liblavinder.config.Match
   :no-commands:

.. lavinder_class:: liblavinder.config.Rule
   :no-commands:


ScratchPad and DropDown
=======================

:class:`~liblavinder.config.ScratchPad` is a special - by default invisible -
group which acts as a container for :class:`~liblavinder.config.DropDown`
configurations. A `DropDown` can be configured to spawn a defined process and
bind thats process' window to it. The associated window can then be shown and
hidden by the lazy command ``dropdown_toggle()``
(see :doc:`/manual/config/lazy`) from the ScratchPad group.
Thus - for example - your favorite terminal emulator turns into a quake-like
terminal by the control of lavinder.

If the DropDown window turns visible it is placed as a floating window on top
of the current group.
If the DropDown is hidden, it is simply switched back to the ScratchPad group.

Example
-------

::

  from liblavinder.config import Group, ScratchPad, DropDown, Key
  from liblavinder.command import lazy
  groups = [
      ScratchPad("scratchpad", [
          # define a drop down terminal.
          # it is placed in the upper third of screen by default.
          DropDown("term", "urxvt", opacity=0.8),

          # define another terminal exclusively for qshell at different position
          DropDown("qshell", "urxvt -hold -e qshell",
                   x=0.05, y=0.4, width=0.9, height=0.6, opacity=0.9,
                   on_focus_lost_hide=True) ]),
      Group("a"),
  ]

  keys = [
    # toggle visibiliy of above defined DropDown named "term"
    Key([], 'F11', lazy.group['scratchpad'].dropdown_toggle('term')),
    Key([], 'F12', lazy.group['scratchpad'].dropdown_toggle('qshell')),
  ]

There is only one DropDown visible in current group at a time.
If a further DropDown is set visible the currently shown DropDown turns
invisble immediately.

Note that if the window is set to not floating, it is detached from DropDown
and ScratchPad, and a new pocess is spawned next time the DropDown is set visible.

Reference
---------

.. lavinder_class:: liblavinder.config.ScratchPad
    :no-commands:

.. lavinder_class:: liblavinder.config.DropDown
     :no-commands:
