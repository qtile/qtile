# Copyright (c) 2009-2010 Aldo Cortesi
# Copyright (c) 2010 Lee McCuller
# Copyright (c) 2010 matt
# Copyright (c) 2010, 2014 dequis
# Copyright (c) 2010, 2012, 2014 roger
# Copyright (c) 2011 Florian Mounier
# Copyright (c) 2011 Kenji_Takahashi
# Copyright (c) 2011 Paul Colomiets
# Copyright (c) 2011 Tzbob
# Copyright (c) 2012-2015 Tycho Andersen
# Copyright (c) 2012 Craig Barnes
# Copyright (c) 2013 Tao Sauvage
# Copyright (c) 2014 Sean Vig
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import asyncio
import contextlib

from libqtile import utils
from libqtile.log_utils import logger
from libqtile.resources.sleep import inhibitor

subscriptions = {}  # type: dict
SKIPLOG = set()  # type: set


def clear():
    subscriptions.clear()


class Subscribe:
    def __init__(self):
        hooks = set([])
        for i in dir(self):
            if not i.startswith("_"):
                hooks.add(i)
        self.hooks = hooks

    def _subscribe(self, event, func):
        lst = subscriptions.setdefault(event, [])
        if func not in lst:
            lst.append(func)
        return func

    def startup_once(self, func):
        """Called when Qtile has started on first start

        This hook is called exactly once per session (i.e. not on each
        ``lazy.restart()``).

        **Arguments**

        None

        Example:

        .. code:: python

          import os
          import subprocess

          from libqtile import hook


          @hook.subscribe.startup_once
          def autostart:
              script = os.path.expanduser("~/.config/qtile/autostart.sh")
              subprocess.run([script])

        """
        return self._subscribe("startup_once", func)

    def startup(self, func):
        """
        Called when qtile is started. Unlike ``startup_once``, this hook is
        fired on every start, including restarts.

        When restarting, this hook is fired after qtile has restarted
        but before qtile tries to restore the session to the same state
        that it was in before the restart.

        **Arguments**

        None

        Example:

        .. code:: python

          import subprocess

          from libqtile import hook
          from libqtile.utils import send_notification


          @hook.subscribe.startup
          def run_every_startup():
              send_notification("qtile", "Startup")

        """
        return self._subscribe("startup", func)

    def startup_complete(self, func):
        """
        Called when qtile is started after all resources initialized.

        This is the same as ``startup`` with the only difference being that
        this hook is fired after the saved state has been restored.

        **Arguments**

        None

        Example:

        .. code:: python

          import subprocess

          from libqtile import hook
          from libqtile.utils import send_notification


          @hook.subscribe.startup_complete
          def run_every_startup():
              send_notification("qtile", "Startup complete")

        """
        return self._subscribe("startup_complete", func)

    def shutdown(self, func):
        """
        Called before qtile is shutdown.

        Using a long-running command in this function will cause the shutdown to
        be delayed.

        This hook is only fired when qtile is shutting down, if you want a command
        to be run when the system sleeps then you should use the ``suspend`` hook
        instead.

        **Arguments**

        None

        Example:

        .. code:: python

          import os
          import subprocess

          from libqtile import hook


          @hook.subscribe.shutdown
          def autostart:
              script = os.path.expanduser("~/.config/qtile/shutdown.sh")
              subprocess.run([script])

        """
        return self._subscribe("shutdown", func)

    def restart(self, func):
        """
        Called before qtile is restarted.

        This hook fires before qtile restarts but after qtile has checked
        that it is able to restart (i.e. the config file is valid).

        **Arguments**

        None

        Example:

        .. code:: python

          from libqtile import hook
          from libqtile.utils import send_notification


          @hook.subscribe.restart
          def run_every_startup():
              send_notification("qtile", "Restarting...")

        """
        return self._subscribe("restart", func)

    def setgroup(self, func):
        """
        Called when group is put on screen.

        This hook is fired in 3 situations:
        1) When the screen changes to a new group
        2) When two groups are switched
        3) When a screen is focused

        **Arguments**

        None

        Example:

        .. code:: python

          from libqtile import hook
          from libqtile.utils import send_notification


          @hook.subscribe.setgroup
          def setgroup():
              send_notification("qtile", "Group set")

        """
        return self._subscribe("setgroup", func)

    def addgroup(self, func):
        """
        Called when a new group is added

        **Arguments**

            * name of new group

        Example:

        .. code:: python

          from libqtile import hook
          from libqtile.utils import send_notification


          @hook.subscribe.addgroup
          def group_added(group_name):
              send_notification("qtile", f"New group added: {group_name}")

        """
        return self._subscribe("addgroup", func)

    def delgroup(self, func):
        """
        Called when group is deleted

        **Arguments**

            * name of deleted group

        Example:

        .. code:: python

          from libqtile import hook
          from libqtile.utils import send_notification


          @hook.subscribe.delgroup
          def group_deleted(group_name):
              send_notification("qtile", f"Group deleted: {group_name}")

        """
        return self._subscribe("delgroup", func)

    def changegroup(self, func):
        """
        Called whenever a group change occurs.

        The following changes will result in this hook being fired:
        1) New group added (unlike ``addgroup``, no group name is passed with this hook)
        2) Group deleted (unlike ``delgroup``, no group name is passed with this hook)
        3) Groups order is changed
        4) Group is renamed

        **Arguments**

        None

        Example:

        .. code:: python

          from libqtile import hook
          from libqtile.utils import send_notification


          @hook.subscribe.changegroup
          def change_group():
              send_notification("qtile", "Change group event")

        """
        return self._subscribe("changegroup", func)

    def focus_change(self, func):
        """
        Called when focus is changed, including moving focus between groups or when
        focus is lost completely (i.e. when a window is closed.)

        **Arguments**

        None

        Example:

        .. code:: python

          from libqtile import hook
          from libqtile.utils import send_notification


          @hook.subscribe.focus_change
          def focus_changed():
              send_notification("qtile", "Focus changed.")

        """
        return self._subscribe("focus_change", func)

    def float_change(self, func):
        """
        Called when a change in float state is made (e.g. toggle floating,
        minimised and fullscreen states)

        **Arguments**

        None

        Example:

        .. code:: python

          from libqtile import hook
          from libqtile.utils import send_notification


          @hook.subscribe.float_change
          def float_change():
              send_notification("qtile", "Window float state changed.")

        """
        return self._subscribe("float_change", func)

    def group_window_add(self, func):
        """Called when a new window is added to a group

        **Arguments**

            * ``Group`` receiving the new window
            * ``Window`` added to the group

        Example:

        .. code:: python

          from libqtile import hook
          from libqtile.utils import send_notification


          @hook.subscribe.group_window_add
          def group_window_add(group, window):
              send_notification("qtile", f"Window {window.name} added to {group.name}")

        """
        return self._subscribe("group_window_add", func)

    def client_new(self, func):
        """
        Called before Qtile starts managing a new client

        Use this hook to declare windows static, or add them to a group on
        startup. This hook is not called for internal windows.

        **Arguments**

            * ``Window`` object

        Example:

        .. code:: python

            from libqtile import hook


            @hook.subscribe.client_new
            def new_client(client):
                if client.name == "xterm":
                    client.togroup("a")
                elif client.name == "dzen":
                    client.static(0)

        """
        return self._subscribe("client_new", func)

    def client_managed(self, func):
        """
        Called after Qtile starts managing a new client

        Called after a window is assigned to a group, or when a window is made
        static.  This hook is not called for internal windows.

        **Arguments**

            * ``Window`` object of the managed window

        Example:

        .. code:: python

            from libqtile import hook
            from libqtile.utils import send_notification

            @hook.subscribe.client_managed
            def client_managed(client):
                send_notification("qtile", f"{client.name} has been managed by qtile")

        """
        return self._subscribe("client_managed", func)

    def client_killed(self, func):
        """
        Called after a client has been unmanaged

        **Arguments**

            * ``Window`` object of the killed window.

        Example:

        .. code:: python

            from libqtile import hook
            from libqtile.utils import send_notification

            @hook.subscribe.client_killed
            def client_killed(client):
                send_notification("qtile", f"{client.name} has been killed")

        """
        return self._subscribe("client_killed", func)

    def client_focus(self, func):
        """
        Called whenever focus moves to a client window

        **Arguments**

            * ``Window`` object of the new focus.

        Example:

        .. code:: python

            from libqtile import hook
            from libqtile.utils import send_notification

            @hook.subscribe.client_focus
            def client_focus(client):
                send_notification("qtile", f"{client.name} has been focused")

        """
        return self._subscribe("client_focus", func)

    def client_mouse_enter(self, func):
        """
        Called when the mouse enters a client

        **Arguments**

            * ``Window`` of window entered

        Example:

        .. code:: python

            from libqtile import hook
            from libqtile.utils import send_notification

            @hook.subscribe.client_killed
            def client_mouse_enter(client):
                send_notification("qtile", f"Mouse has entered {client.name}")

        """
        return self._subscribe("client_mouse_enter", func)

    def client_name_updated(self, func):
        """
        Called when the client name changes

        **Arguments**

            * ``Window`` of client with updated name

        Example:

        .. code:: python

            from libqtile import hook
            from libqtile.utils import send_notification

            @hook.subscribe.client_name_updated
            def client_name_updated(client):
                send_notification(
                    "qtile",
                    f"Client's has been updated to {client.name}"
                )

        """
        return self._subscribe("client_name_updated", func)

    def client_urgent_hint_changed(self, func):
        """
        Called when the client urgent hint changes

        **Arguments**

            * ``Window`` of client with hint change

        Example:

        .. code:: python

            from libqtile import hook
            from libqtile.utils import send_notification

            @hook.subscribe.client_urgent_hint_changed
            def client_urgency_change(client):
                send_notification(
                    "qtile",
                    f"{client.name} has changed its urgency state"
                )

        """
        return self._subscribe("client_urgent_hint_changed", func)

    def layout_change(self, func):
        """
        Called on layout change event (including when a new group is
        displayed on the screen)

        **Arguments**

            * layout object for new layout
            * group object on which layout is changed

        Example:

        .. code:: python

            from libqtile import hook
            from libqtile.utils import send_notification

            @hook.subscribe.layout_change
            def layout_change(layout, group):
                send_notification(
                    "qtile",
                    f"{layout.name} is now on group {group.name}"
                )
        """
        return self._subscribe("layout_change", func)

    def net_wm_icon_change(self, func):
        """
        Called on ``_NET_WM_ICON`` change

        X11 only. Called when a window notifies that it has changed
        its icon.

        **Arguments**

            * ``Window`` of client with changed icon

        Example:

        .. code:: python

            from libqtile import hook
            from libqtile.utils import send_notification

            @hook.subscribe.net_wm_icon_change
            def icon_change(client):
                send_notification("qtile", f"{client.name} has changed its icon")

        """
        return self._subscribe("net_wm_icon_change", func)

    def selection_notify(self, func):
        """
        Called on selection notify

        X11 only. Fired when a selection is made in a window.

        **Arguments**

            * name of the selection
            * dictionary describing selection, containing ``owner`` and
              ``selection`` as keys

        The selection owner will typically be ``"PRIMARY"`` when contents is highlighted and
        ``"CLIPBOARD"`` when contents is actively copied to the clipboard, e.g. with Ctrl + C.

        Example:

        .. code:: python

            from libqtile import hook
            from libqtile.utils import send_notification

            @hook.subscribe.selection_notify
            def selection_notify(name, selection):
                send_notification(
                    "qtile",
                    f"Window {selection['owner']} has made a selection in the {name} selection."
                )

        """
        return self._subscribe("selection_notify", func)

    def selection_change(self, func):
        """
        Called on selection change

        X11 only. Fired when a selection property is changed (e.g. new selection created or
        existing selection is emptied)

        **Arguments**

            * name of the selection
            * dictionary describing selection, containing ``owner`` and
              ``selection`` as keys

        The selection owner will typically be ``"PRIMARY"`` when contents is highlighted and
        ``"CLIPBOARD"`` when contents is actively copied to the clipboard, e.g. with Ctrl + C.

        Example:

        .. code:: python

            from libqtile import hook
            from libqtile.utils import send_notification

            @hook.subscribe.selection_change
            def selection_change(name, selection):
                send_notification(
                    "qtile",
                    f"Window {selection['owner']} has changed the {name} selection."
                )

        """
        return self._subscribe("selection_change", func)

    def screen_change(self, func):
        """
        Called when the output configuration is changed (e.g. via randr in X11).

        .. note::

          If you have ``reconfigure_screens = True`` in your config then qtile
          will automatically reconfigure your screens when it detects a change to the
          screen configuration. This hook is fired *before* that reconfiguration takes
          place. The ``screens_reconfigured`` hook should be used where you want to trigger
          an event after the reconfiguration.

        **Arguments**

            * ``xproto.randr.ScreenChangeNotify`` event (X11) or None (Wayland).

        Example:

        .. code:: python

            from libqtile import hook
            from libqtile.utils import send_notification

            @hook.subscribe.screen_change
            def screen_change(event):
                send_notification("qtile", "Screen change detected.")

        """
        return self._subscribe("screen_change", func)

    def screens_reconfigured(self, func):
        """
        Called once ``qtile.reconfigure_screens`` has completed (e.g. if
        ``reconfigure_screens`` is set to ``True`` in your config).

        **Arguments**

        None

        Example:

        .. code:: python

            from libqtile import hook
            from libqtile.utils import send_notification

            @hook.subscribe.screen_change
            def screen_change(event):
                send_notification("qtile", "Screens have been reconfigured.")

        """
        return self._subscribe("screens_reconfigured", func)

    def current_screen_change(self, func):
        """
        Called when the current screen (i.e. the screen with focus) changes

        **Arguments**

        None

        Example:

        .. code:: python

            from libqtile import hook
            from libqtile.utils import send_notification

            @hook.subscribe.current_screen_change
            def screen_change(event):
                send_notification("qtile", "Current screen change detected.")

        """
        return self._subscribe("current_screen_change", func)

    def enter_chord(self, func):
        """
        Called when key chord begins

        Note: if you only want to use this chord to display the chord name then
        you should use the ``Chord`` widget.

        **Arguments**

            * name of chord(mode)

        Example:

        .. code:: python

            from libqtile import hook
            from libqtile.utils import send_notification

            @hook.subscribe.enter_chord
            def enter_chord(chord_name):
                send_notification("qtile", "Started {chord_name} key chord.")

        """
        return self._subscribe("enter_chord", func)

    def leave_chord(self, func):
        """
        Called when key chord ends

        **Arguments**

        None

        Example:

        .. code:: python

            from libqtile import hook
            from libqtile.utils import send_notification

            @hook.subscribe.leave_chord
            ded leave_chord():
                send_notification("qtile", "Key chord exited")

        """
        return self._subscribe("leave_chord", func)

    def resume(self, func):
        """
        Called when system wakes up from sleep, suspend or hibernate.

        Relies on systemd's inhibitor dbus interface, via the dbus-next package.

        Note: the hook is not fired when resuming from shutdown/reboot events.
        Use the "startup" hooks for those scenarios.

        **Arguments**

        None
        """
        inhibitor.want_resume()
        return self._subscribe("resume", func)

    def suspend(self, func):
        """
        Called when system is about to sleep, suspend or hibernate.

        Relies on systemd's inhibitor dbus interface, via the dbus-next package.

        When this hook is used, qtile will set an inhibitor that prevent the system
        from sleeping. The inhibitor is removed as soon as your function exits. You should therefore
        not use long-running code in this function.

        Please note, this inhibitor will also only delay, not block, the computer's ability to sleep.
        The default delay is 5 seconds. If your function has not completed within that time, the
        machine will still sleep (see important note below).

        You can increase this delay by setting ``InhibitDelayMaxSec`` in ``logind.conf.``
        see: https://www.freedesktop.org/software/systemd/man/logind.conf.html

        In addition, closing a laptop lid will ignore inhibitors by default. You can override this
        by setting ``LidSwitchIgnoreInhibited=no`` in ``/etc/systemd/logind.conf``.

        .. important::

            The logind service creates an inhibitor by passing a reference to a lock file which must
            be closed to release the lock. Additional references to the lock may be created if you
            spawn processes with the ``subprocess`` module and these processes are running when
            the machine tries to suspend. As a result, it is strongly recommended that you launch
            any processes with ``qtile.spawn(...)`` as this will not create additional copies of the
            lock.

        **Arguments**

        None

        Example:

        .. code:: python

          from libqtile import hook, qtile


          @hook.subscribe.suspend
          def lock_on_sleep():
              # Run screen locker
              qtile.spawn("/path/to/screen_locker")

        """
        inhibitor.want_sleep()
        return self._subscribe("suspend", func)


subscribe = Subscribe()


class Unsubscribe(Subscribe):
    """
    This class mirrors subscribe, except the _subscribe member has been
    overridden to removed calls from hooks.
    """

    def _subscribe(self, event, func):
        lst = subscriptions.setdefault(event, [])
        try:
            lst.remove(func)
        except ValueError:
            raise utils.QtileError(
                "Tried to unsubscribe a hook that was not currently subscribed"
            )


unsubscribe = Unsubscribe()


def _fire_async_event(co):
    from libqtile.utils import create_task

    loop = None
    with contextlib.suppress(RuntimeError):
        loop = asyncio.get_running_loop()

    if loop is None:
        asyncio.run(co)
    else:
        create_task(co)


def fire(event, *args, **kwargs):
    if event not in subscribe.hooks:
        raise utils.QtileError("Unknown event: %s" % event)
    if event not in SKIPLOG:
        logger.debug("Internal event: %s(%s, %s)", event, args, kwargs)
    for i in subscriptions.get(event, []):
        try:
            if asyncio.iscoroutinefunction(i):
                _fire_async_event(i(*args, **kwargs))
            elif asyncio.iscoroutine(i):
                _fire_async_event(i)
            else:
                i(*args, **kwargs)
        except:  # noqa: E722
            logger.exception("Error in hook %s", event)
