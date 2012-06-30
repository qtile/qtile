Built-in Hooks
==============

startup
-------

Called when Qtile has initialized

client_name_updated
-------------------

Called when the client name changes.

client_focus
------------

Called whenver focus changes.

Arguments:

* ``window.Window`` object of the new focus.

addgroup
--------

Called when group is added.

delgroup
--------

Called when group is deleted.

group_window_add
----------------

Called when a new window is added to a group.

client_managed
--------------

Called after Qtile starts managing a new client. That is, after a
window is assigned to a group, or when a window is made static.
This hook is not called for internal windows.

Arguments:

* ``window.Window`` object

client_new
----------

Called before Qtile starts managing a new client. Use this hook to
declare windows static, or add them to a group on startup. This
hook is not called for internal windows.

Arguments:

* ``window.Window`` object of the newly created window

**Example**::

    def func(c):
        if c.name == "xterm":
            c.togroup("a")
        elif c.name == "dzen":
            c.static(0)
    libqtile.hook.subscribe.client_new(func)

client_urgent_hint_changed
--------------------------

Called when the client urgent hint changes.

focus_change
------------

Called when focus is changed.

float_change
------------

Called when a change in float state is made

client_killed
-------------

Called after a client has been unmanaged.

Arguments:

* ``window.Window`` object of the killed window.

setgroup
--------

Called when group is changed.

layout_change
-------------

Called on layout change.

client_state_changed
--------------------

Called whenever client state changes.

window_name_change
------------------

Called whenever a windows name changes.

client_mouse_enter
------------------

Called when the mouse enters a client.

client_type_changed
-------------------

Called whenever window type changes.
