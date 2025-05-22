# Copyright (c) 2017, Dirk Hartmann
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

from __future__ import annotations

from typing import TYPE_CHECKING

from libqtile import config, group, hook
from libqtile.backend.base import FloatStates
from libqtile.command.base import expose_command
from libqtile.config import Match, _Match

if TYPE_CHECKING:
    from libqtile.backend.base import Window


class WindowVisibilityToggler:
    """
    WindowVisibilityToggler is a wrapper for a window, used in ScratchPad group
    to toggle visibility of a window by toggling the group it belongs to.
    The window is either sent to the named ScratchPad, which is by default
    invisble, or the current group on the current screen.
    With this functionality the window can be shown and hidden by a single
    keystroke (bound to command of ScratchPad group).
    By default, the window is also hidden if it loses focus.
    """

    def __init__(self, scratchpad_name, window: Window, on_focus_lost_hide, warp_pointer):
        """
        Initiliaze the  WindowVisibilityToggler.

        Parameters:
        ===========
        scratchpad_name: string
            The name (not label) of the ScratchPad group used to hide the window
        window: window
            The window to toggle
        on_focus_lost_hide: bool
            if True the associated window is hidden if it loses focus
        warp_pointer: bool
            if True the mouse pointer is warped to center of associated window
            if shown. Only used if on_focus_lost_hide is True
        """
        self.scratchpad_name = scratchpad_name
        self.window = window
        self.on_focus_lost_hide = on_focus_lost_hide
        self.warp_pointer = warp_pointer
        # determine current status based on visibility
        self.shown = False
        self.show()

    def info(self):
        return dict(
            window=self.window.info(),
            scratchpad_name=self.scratchpad_name,
            visible=self.visible,
            on_focus_lost_hide=self.on_focus_lost_hide,
            warp_pointer=self.warp_pointer,
        )

    @property
    def visible(self):
        """
        Determine if associated window is currently visible.
        That is the window is on a group different from the scratchpad
        and that group is the current visible group.
        """
        if self.window.group is None:
            return False
        return (
            self.window.group.name != self.scratchpad_name
            and self.window.group is self.window.qtile.current_group
        )

    def toggle(self):
        """
        Toggle the visibility of associated window. Either show() or hide().
        """
        if self.window.has_focus:
            self.hide()
        elif self.shown and self.visible:
            win = self.window
            win.bring_to_front()
            win.focus(warp=True)
            self.shown = True
        else:
            self.show()

    def show(self):
        """
        Show the associated window on top of current screen.
        The window is moved to the current group as floating window.

        If 'warp_pointer' is True the mouse pointer is warped to center of the
        window if 'on_focus_lost_hide' is True.
        Otherwise, if pointer is moved manually to window by the user
        the window might be hidden again before actually reaching it.
        """
        if (not self.visible) or (not self.shown):
            win = self.window
            # always set the floating state before changing group
            # to avoid disturbance of tiling layout
            win._float_state = FloatStates.TOP
            # add to group and bring it to front.
            win.togroup()
            win.bring_to_front()
            # toggle internal flag of visibility
            self.shown = True

            # add hooks to determine if focus get lost
            if self.on_focus_lost_hide:
                if self.warp_pointer:
                    win.focus(warp=True)
                hook.subscribe.client_focus(self.on_focus_change)
                hook.subscribe.setgroup(self.on_focus_change)

    def hide(self):
        """
        Hide the associated window. That is, send it to the scratchpad group.
        """
        if self.visible or self.shown:
            # unsubscribe the hook methods, since the window is not shown
            if self.on_focus_lost_hide:
                hook.unsubscribe.client_focus(self.on_focus_change)
                hook.unsubscribe.setgroup(self.on_focus_change)
            self.window.togroup(self.scratchpad_name)
            self.shown = False

    def unsubscribe(self):
        """unsubscribe all hooks"""
        if self.on_focus_lost_hide and (self.visible or self.shown):
            hook.unsubscribe.client_focus(self.on_focus_change)
            hook.unsubscribe.setgroup(self.on_focus_change)

    def on_focus_change(self, *args, **kwargs):
        """
        hook method which is called on window focus change and group change.
        Depending on 'on_focus_lost_xxx' arguments, the associated window may
        get hidden (by call to hide) or even killed.
        """
        if self.shown:
            current_group = self.window.qtile.current_group
            if (
                self.window.group is not current_group
                or self.window is not current_group.current_window
            ):
                if self.on_focus_lost_hide:
                    self.hide()


class DropDownToggler(WindowVisibilityToggler):
    """
    Specialized WindowVisibilityToggler which places the associatd window
    each time it is shown at desired location.
    For example this can be used to create a quake-like terminal.
    """

    def __init__(self, window, scratchpad_name, ddconfig):
        self.name = ddconfig.name
        self.x = ddconfig.x
        self.y = ddconfig.y
        self.width = ddconfig.width
        self.height = ddconfig.height
        self.border_width = window.qtile.config.floating_layout.border_width

        # add "SKIP_TASKBAR" to _NET_WM_STATE atom (for X11)
        if window.qtile.core.name == "x11":
            net_wm_state = list(window.window.get_property("_NET_WM_STATE", "ATOM", unpack=int))
            skip_taskbar = window.qtile.core.conn.atoms["_NET_WM_STATE_SKIP_TASKBAR"]
            if net_wm_state:
                if skip_taskbar not in net_wm_state:
                    net_wm_state.append(skip_taskbar)
            else:
                net_wm_state = [skip_taskbar]
            window.window.set_property("_NET_WM_STATE", net_wm_state)

        # Let's add the window to the scratchpad group.
        window.togroup(scratchpad_name)
        window.opacity = ddconfig.opacity
        WindowVisibilityToggler.__init__(
            self, scratchpad_name, window, ddconfig.on_focus_lost_hide, ddconfig.warp_pointer
        )

    def info(self):
        info = WindowVisibilityToggler.info(self)
        info.update(
            dict(name=self.name, x=self.x, y=self.y, width=self.width, height=self.height)
        )
        return info

    def show(self):
        """
        Like WindowVisibilityToggler.show, but before showing the window,
        its floating x, y, width and height is set.
        """
        if (not self.visible) or (not self.shown):
            # SET GEOMETRY
            win = self.window
            screen = win.qtile.current_screen
            # calculate windows floating position and width/height
            # these may differ for screens, and thus always recalculated.
            x = int(screen.dx + self.x * screen.dwidth)
            y = int(screen.dy + self.y * screen.dheight)
            win.float_x = x
            win.float_y = y
            width = int(screen.dwidth * self.width) - 2 * self.border_width
            height = int(screen.dheight * self.height) - 2 * self.border_width
            win.place(x, y, width, height, self.border_width, win.bordercolor, respect_hints=True)
            # Toggle the dropdown
            WindowVisibilityToggler.show(self)


class ScratchPad(group._Group):
    """
    Specialized group which is by default invisible and can be configured, to
    spawn windows and toggle its visibility (in the current group) by command.

    The ScratchPad group acts as a container for windows which are currently
    not visible but associated to a DropDownToggler and can toggle their
    group by command (of ScratchPad group).
    The ScratchPad, by default, has no label and thus is not shown in
    GroupBox widget.
    """

    def __init__(
        self,
        name="scratchpad",
        dropdowns: list[config.DropDown] | None = None,
        label="",
        single=False,
    ):
        group._Group.__init__(self, name, label=label)
        self._dropdownconfig = {dd.name: dd for dd in dropdowns} if dropdowns is not None else {}
        self.dropdowns: dict[str, DropDownToggler] = {}
        self._spawned: dict[str, _Match] = {}
        self._to_hide: list[str] = []
        self._single = single

    def _check_unsubscribe(self):
        if not self.dropdowns:
            hook.unsubscribe.client_killed(self.on_client_killed)
            hook.unsubscribe.float_change(self.on_float_change)

    def _spawn(self, ddconfig):
        """
        Spawn a process by defined command.
        Method is only called if no window is associated. This is either on the
        first call to show or if the window was killed.
        The process id of spawned process is saved and compared to new windows.
        In case of a match the window gets associated to this DropDown object.
        """
        name = ddconfig.name
        if name not in self._spawned:
            if not self._spawned:
                hook.subscribe.client_new(self.on_client_new)
            pid = self.qtile.spawn(ddconfig.command)
            self._spawned[name] = ddconfig.match or Match(net_wm_pid=pid)

    def on_client_new(self, client, *args, **kwargs):
        """
        hook method which is called on new windows.
        This method is subscribed if the given command is spawned
        and unsubscribed immediately if the associated window is detected.
        """
        name = None
        for n, match in self._spawned.items():
            if match.compare(client):
                name = n
                break

        if name is not None:
            self._spawned.pop(name)
            if not self._spawned:
                hook.unsubscribe.client_new(self.on_client_new)
            self.dropdowns[name] = DropDownToggler(client, self.name, self._dropdownconfig[name])
            if self._single:
                for n, d in self.dropdowns.items():
                    if n != name:
                        d.hide()
            if name in self._to_hide:
                self.dropdowns[name].hide()
                self._to_hide.remove(name)
            if len(self.dropdowns) == 1:
                hook.subscribe.client_killed(self.on_client_killed)
                hook.subscribe.float_change(self.on_float_change)

    def on_client_killed(self, client, *args, **kwargs):
        """
        hook method which is called if a client is killed.
        If the associated window is killed, reset internal state.
        """
        name = None
        for name, dd in self.dropdowns.items():
            if dd.window is client:
                del self.dropdowns[name]
                break
        self._check_unsubscribe()

    def on_float_change(self, *args, **kwargs):
        """
        hook method which is called if window float state is changed.
        If the current associated window is not floated (any more) the window
        and process is detached from DropDown, thus the next call to Show
        will spawn a new process.
        """
        name = None
        for name, dd in self.dropdowns.items():
            if not dd.window.floating:
                if dd.window.group is not self:
                    dd.unsubscribe()
                    del self.dropdowns[name]
                    break
        self._check_unsubscribe()

    @expose_command()
    def dropdown_toggle(self, name):
        """
        Toggle visibility of named DropDown.
        """
        if self._single:
            for n, d in self.dropdowns.items():
                if n != name:
                    d.hide()
        if name in self.dropdowns:
            self.dropdowns[name].toggle()
        else:
            if name in self._dropdownconfig:
                self._spawn(self._dropdownconfig[name])

    @expose_command()
    def hide_all(self):
        """
        Hide all scratchpads.
        """
        for d in self.dropdowns.values():
            d.hide()

    @expose_command()
    def dropdown_reconfigure(self, name, **kwargs):
        """
        reconfigure the named DropDown configuration.
        Note that changed attributes only have an effect on spawning the window.
        """
        if name not in self._dropdownconfig:
            return
        dd = self._dropdownconfig[name]
        for attr, value in kwargs.items():
            if hasattr(dd, attr):
                setattr(dd, attr, value)

    @expose_command()
    def dropdown_info(self, name=None):
        """
        Get information on configured or currently active DropDowns.
        If name is None, a list of all dropdown names is returned.
        """
        if name is None:
            return {"dropdowns": [ddname for ddname in self._dropdownconfig]}
        elif name in self.dropdowns:
            return self.dropdowns[name].info()
        elif name in self._dropdownconfig:
            return self._dropdownconfig[name].info()
        else:
            raise ValueError(f'No DropDown named "{name}".')

    def get_state(self):
        """
        Get the state of existing dropdown windows. Used for restoring state across
        Qtile restarts (`restart` == True) or config reloads (`restart` == False).
        """
        state = []
        for name, dd in self.dropdowns.items():
            client_wid = dd.window.wid
            state.append((name, client_wid, dd.visible))
        return state

    def restore_state(self, state, restart: bool) -> list[int]:
        """
        Restore the state of existing dropdown windows. Used for restoring state across
        Qtile restarts (`restart` == True) or config reloads (`restart` == False).
        """
        orphans = []
        for name, wid, visible in state:
            if name in self._dropdownconfig:
                if restart:
                    self._spawned[name] = Match(wid=wid)
                    if not visible:
                        self._to_hide.append(name)
                else:
                    # We are reloading the config; manage the clients now
                    self.dropdowns[name] = DropDownToggler(
                        self.qtile.windows_map[wid],
                        self.name,
                        self._dropdownconfig[name],
                    )
                    if not visible:
                        self.dropdowns[name].hide()
            else:
                orphans.append(wid)

        if self._spawned:
            # Handle re-managed clients after restarting
            assert restart
            hook.subscribe.client_new(self.on_client_new)

        if not restart and self.dropdowns:
            # We're only reloading so don't have these hooked via self.on_client_new
            hook.subscribe.client_killed(self.on_client_killed)
            hook.subscribe.float_change(self.on_float_change)

        return orphans
