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

from . import group
from . import hook, window

class WindowVisibilityToggler(object):
    """
    WindowVisibilityToggler is a wrapper for a window, used in ScratchPad group
    to toggle visibility of a window by toggling the group it belongs to.
    The window is either sent to the named ScratchPad, which is by default
    invisble, or the current group on the current screen.
    With this functionality the window can be shown and hidden by a single
    keystroke (bound to command of ScratchPad group).
    By default, the window is also hidden if it looses focus.
    """

    def __init__(self, scratchpad_name, window, on_focus_lost_hide, warp_pointer):
        """
        Initiliaze the  WindowVisibilityToggler.

        Parameters:
        ===========
        scratchpad_name : string
            The name (not label) of the ScratchPad group used to hide the window
        window : window
            The window to toggle
        on_focus_lost_hide : bool
            if True the associated window is hidden if it looses focus
        warp_pointer : bool
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
        return dict(window=self.window.info(),
                    scratchpad_name=self.scratchpad_name,
                    visible=self.visible,
                    on_focus_lost_hide=self.on_focus_lost_hide,
                    warp_pointer=self.warp_pointer)

    @property
    def visible(self):
        """
        Determine if associated window is currently visible.
        That is the window is on a group different from the scratchpad
        and that group is the current visible group.
        """
        if self.window.group is None:
            return False
        return (self.window.group.name != self.scratchpad_name and
                self.window.group is self.window.qtile.currentGroup)

    def toggle(self):
        """
        Toggle the visibility of associated window. Either show() or hide().
        """
        if (not self.visible or not self.shown):
            self.show()
        else:
            self.hide()

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
            win._float_state = window.TOP
            # add to group and bring it to front.
            win.togroup()
            win.cmd_bring_to_front()
            # toggle internal flag of visibility
            self.shown = True

            # add hooks to determine if focus get lost
            if self.on_focus_lost_hide:
                if self.warp_pointer:
                    win.window.warp_pointer(win.width // 2, win.height // 2)
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
        try:
            hook.unsubscribe.client_focus(self.on_focus_change)
        except:
            pass
        try:
            hook.unsubscribe.setgroup(self.on_focus_change)
        except:
            pass

    def on_focus_change(self, *args, **kwargs):
        """
        hook method which is called on window focus change and group change.
        Depending on 'on_focus_lost_xxx' arguments, the associated window may
        get hidden (by call to hide) or even killed.
        """
        if self.shown:
            currentGroup = self.window.qtile.currentGroup
            if (self.window.group is not currentGroup or
                    self.window is not currentGroup.currentWindow):
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
        window.setOpacity(ddconfig.opacity)
        WindowVisibilityToggler.__init__(self, scratchpad_name, window,
            ddconfig.on_focus_lost_hide, ddconfig.warp_pointer)

    def info(self):
        info = WindowVisibilityToggler.info(self)
        info.update(dict(name=self.name,
                         x=self.x,
                         y=self.y,
                         width=self.width,
                         height=self.height))
        return info

    def show(self):
        """
        Like WindowVisibilityToggler.show, but before showing the window,
        its floating x, y, width and height is set.
        """
        if (not self.visible) or (not self.shown):
            win = self.window
            screen = win.qtile.currentScreen
            # calculate windows floating position and width/height
            # these may differ for screens, and thus always recalculated.
            win.x = int(screen.dx + self.x * screen.dwidth)
            win.y = int(screen.dy + self.y * screen.dheight)
            win.float_x = win.x
            win.float_y = win.y
            win.width = int(screen.dwidth * self.width)
            win.height = int(screen.dheight * self.height)

            # SHOW
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
    def __init__(self, name='scratchpad', dropdowns=[], label=''):
        group._Group.__init__(self, name, label=label)
        self._dropdownconfig = {dd.name: dd for dd in dropdowns}
        self.dropdowns = {}
        self._spawned = {}

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
        if name not in self._spawned.values():
            if not self._spawned:
                hook.subscribe.client_new(self.on_client_new)
            cmd = self._dropdownconfig[name].command
            pid = self.qtile.cmd_spawn(cmd)
            self._spawned[pid] = name

    def on_client_new(self, client, *args, **kwargs):
        """
        hook method which is called on new windows.
        This method is subscribed if the given command is spawned
        and unsubscribed immediately if the associated window is detected.
        """
        client_pid = client.window.get_net_wm_pid()
        if client_pid in self._spawned:
            name = self._spawned.pop(client_pid)
            if not self._spawned:
                hook.unsubscribe.client_new(self.on_client_new)
            self.dropdowns[name] = DropDownToggler(client, self.name,
                                                   self._dropdownconfig[name])
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
                dd.unsubscribe()
                del self.dropdowns[name]
                break
        self._check_unsubscribe()

    def on_float_change(self, *args, **kwargs):
        """
        hook method which is called if window float state is changed.
        If the current associated window is not floated (any more) the window
        and process is detached from DRopDown, thus the next call to Show
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

    def cmd_dropdown_toggle(self, name):
        """
        Toggle visibility of named DropDown.
        """
        if name in self.dropdowns:
            self.dropdowns[name].toggle()
        else:
            if name in self._dropdownconfig:
                self._spawn(self._dropdownconfig[name])

    def cmd_dropdown_reconfigure(self, name, **kwargs):
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

    def cmd_dropdown_info(self, name=None):
        """
        Get information on configured or currently active DropDowns.
        If name is None, a list of all dropdown names is returned.
        """
        if name is None:
            return {'dropdowns': [ddname for ddname in self._dropdownconfig]}
        elif name in self.dropdowns:
            return self.dropdowns[name].info()
        elif name in self._dropdownconfig:
            return self._dropdownconfig[name].info()
        else:
            raise ValueError('No DropDown named "%s".' % name)
