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

import os
import signal

from . import command, configurable
from . import hook, window

# from .log_utils import logger

class DropDown(configurable.Configurable):
    """
    This class is a wrapper for a window of a specified command, allowing the
    window to be shown and hidden by keystroke on top of the current screen.

    On the first use a specified command is used to spawn a process.
    The associated window is bound to this wrapper and its visibility can be
    toggled.
    By default the window is shown centered in the upper area of the screen and
    hides if it looses focus.

    You may use this class to turn your favorite terminal emulator into a quake
    like drop down terminal.
    Add something like the following to you config.py to configure it:

    quake_terminal = scratchpad.DropDown('xterm')
    ...
    Key( [], 'F12', quake_terminal.toggle_command )

    Another interesting configuration is a temporary viewer for log file for
    example the qtile.log file. In this example a terminal is spawned to execute
    a command. If the terminal window looses focus it is killed.

    logviewer = scratchpad.DropDown(
        "urxvt -hold -name qtile.log "
        "-e tail -f -n 30 /home/dhannes/.local/share/qtile/qtile.log",
        x=0.05, y=0.4, width=0.9, height=0.6,
        on_focus_lost_kill=True)
    """
    defaults = (
        (
            'x',
            0.1,
            'X position of window as fraction of current screen width. '
            '0 is the left most position.'
        ),
        (
            'y',
            0.0,
            'Y position of window as fraction of current screen height. '
            '0 is the top most position. To show the window at bottom, '
            'you have to configure a value < 1 and an appropriate height.'
        ),
        (
            'width',
            0.8,
            'Width of window as fraction of current screen width'
        ),
        (
            'height',
            0.35,
            'Height of window as fraction of current screen.'
        ),
        (
            'opacity',
            0.9,
            'Opacity of window as fraction. Zero is opaque.'
        ),
        (
            'on_focus_lost_hide',
            True,
            'Shall the window be hidden if focus is lost? If so, the DropDown '
            'is hidden if window focus or the group is changed.'
        ),
        (
            'on_focus_lost_kill',
            False,
            'Shall the window be killed if focus is lost. If so, the window is '
            'closed and a new process is spawned on next call to `show`. '
            'If `on_focus_lost_kill` is True, the window is always killed'
            'regardless of state of `on_focus_lost_hide`.'
        ),
        (
            'warp_pointer',
            True,
            'Shall pointer warp to center of window on activation? '
            'This has only effect if any of the on_focus_lost_xxx '
            'configurations is True'
        ),
    )

    def __init__(self, cmd='xterm', **config):
        """
        Initialize DropDown window wrapper.
        Define a command to spawn a process for the first time the DropDown
        is shown.
        """
        configurable.Configurable.__init__(self, **config)
        self.add_defaults(self.defaults)
        self._command = cmd
        self._proc_id = None
        self._window = None
        self._visible = False

    @property
    def visible(self):
        """
        Determine if window is associated and is currently visible as
        floating window in a group.
        """
        return self._window is not None and self._visible

    def spawn(self, qtile):
        """
        Spawn a process by defined command.
        Method is only called if no window is associated. This is either on the
        first call to show or if the window was killed.
        The process id of spawned process is saved and compared to new windows.
        In case of a match the window gets associated to this DropDown object.
        """
        if self._proc_id is None:
            hook.subscribe.client_new(self.on_client_new)
            self._proc_id = qtile.cmd_spawn(self._command)
            # logger.debug('DropDown at %x :: Spawned: id="%x"' %
            #              (id(self), self._proc_id))

    def show(self, qtile):
        """
        Show the associated window on top of current screen.
        If no window is currently associated, the defined command is used
        to spawn a process. Otherwise the window is added to the current group
        as floating window and positioned as defined.

        If 'warp_pointer' is True the mouse pointer is warped to center of the
        window if 'on_focus_lost_hide' or 'on_focus_lost_kill' is True.
        Otherwise, if pointer is moved to window it might be closed before
        reaching it.
        """
        # logger.debug('DropDown at %x :: Show' % id(self))
        if self._proc_id is None:
            self.spawn(qtile)
        elif self._window is None:
            # window is not associated, yet
            # logger.debug('DropDown at %x :: Show - No window associated yet.' %
            #              id(self))
            return
        elif not self._visible:
            screen = qtile.currentScreen
            win = self._window
            # calculate windows floating position and width/height
            # these may differ for screens, and thus always recalculated.
            win.x = int(screen.dx + self.x * screen.dwidth)
            win.y = int(screen.dy + self.y * screen.dheight)
            win.float_x = win.x
            win.float_y = win.y
            win.width = int(screen.dwidth * self.width)
            win.height = int(screen.dheight * self.height)
            win._float_state = window.TOP
            # add to group and bring it to front.
            win.togroup()
            win.cmd_bring_to_front()
            # add hooks to determine if focus get lost
            if self.on_focus_lost_hide or self.on_focus_lost_kill:
                if self.warp_pointer:
                    win.window.warp_pointer(win.width // 2, win.height // 2)
                hook.subscribe.client_focus(self.on_focus_change)
                hook.subscribe.setgroup(self.on_focus_change)
            # float change hook is always subscribed
            hook.subscribe.float_change(self.on_float_change)
            # toggle internal flag of visibility
            self._visible = True

    def hide(self, qtile):
        """
        Hide the associated window.
        If the associated window is visible, it is hidden and removed from
        its group.
        """
        if self.visible:
            # logger.debug('DropDown at %x :: Hide' % id(self))
            # unsubscribe the hook methods, since the window is not shown
            if self.on_focus_lost_hide or self.on_focus_lost_kill:
                hook.unsubscribe.client_focus(self.on_focus_change)
                hook.unsubscribe.setgroup(self.on_focus_change)
            # float change is always unsubscribed
            hook.unsubscribe.float_change(self.on_float_change)
            # remove the window from its group, thus it is not shown in widgets
            self._window.hide()
            self._window.group.remove(self._window)
            self._visible = False
        # else:
        #    logger.debug('DropDown at %x :: Hide, but window is not visible' %
        #                 id(self))

    @property
    def toggle(self):
        """
        Toggle the visibility of associated window. Either show() or hide().
        Use this property in KeyBinding.
        Technically a lazy.function is returned by this property
        """
        @command.lazy.function
        def _toggle(qtile, *args, **kwargs):
            if not self.visible:
                self.show(qtile)
            else:
                # if window is visible on another group than the current, then it
                # is shown on current screen, since it is currently not visible
                if (self._window.group is not self._window.qtile.currentGroup):
                    # for show to work properly, set _visible to False
                    self._visible = False
                    self.show(qtile)
                else:
                    self.hide(qtile)
        return _toggle

    def on_client_new(self, client, *args, **kwargs):
        """
        hook method which is called on new windows.
        Method is subscribed if the given command is spawned and unsubscribed
        if the associated window is determined.
        """
        # logger.debug('DropDown at %x :: hook: New client' % id(self))
        if self._proc_id is not None and self._window is None:
            client_pid = client.window.get_net_wm_pid()
            # logger.debug('DropDown at %x :: hook: New client "%s", pid %s, wm_pid %s' %
            #              (id(self), client.name, self._proc_id, client_pid))
            if self._proc_id == client_pid:
                self._window = client
                self._window.setOpacity(self.opacity)
                self._visible = False
                # unsubscribe current hook method, the window is found
                hook.unsubscribe.client_new(self.on_client_new)
                # subscribe methods for current visible client
                hook.subscribe.client_killed(self.on_client_killed)
                hook.subscribe.float_change(self.on_float_change)
                # show is called to add the window as floating and placed
                # according to given x, y, width, height arguments
                self.show(self._window.qtile)

    def on_focus_change(self, *args, **kwargs):
        """
        hook method which is called on window focus change and group change.
        Depending on 'on_focus_lost_xxx' arguments, the associated window may
        get hidden (by call to hide) or even killed.
        """
        if self.visible:
            currentGroup = self._window.qtile.currentGroup
            if (self._window.group is not currentGroup or
                    self._window is not currentGroup.currentWindow):
                # logger.debug('DropDown at %x :: hook: focus change' % id(self))
                if self.on_focus_lost_kill:
                    # logger.debug('DropDown at %x :: --> kill' % id(self))
                    hook.unsubscribe.client_focus(self.on_focus_change)
                    hook.unsubscribe.setgroup(self.on_focus_change)
                    # kill the spawned process
                    os.kill(self._proc_id, signal.SIGTERM)
                elif self.on_focus_lost_hide:
                    self.hide(self._window.qtile)

    def reset(self):
        self._window = None
        self._proc_id = None
        self._visible = False
        hook.unsubscribe.float_change(self.on_float_change)

    def on_client_killed(self, client, *args, **kwargs):
        """
        hook method which is called if a client is killed.
        If the associated window is killed, reset internal state.
        """
        if client is self._window:
            # logger.debug('DropDown at %x :: hook: client killed' % id(self))
            self.reset()

    def on_float_change(self, *args, **kwargs):
        """
        hook method which is called if window float state is changed.
        If the current associated window is not floated (any more) the window
        and process is detached from DRopDown, thus the next call to Show
        will spawn a new process.
        """
        if self.visible and not self._window.floating:
            # logger.debug('DropDown at %x :: hook: float change - Reset' %
            #              id(self))
            hook.unsubscribe.client_focus(self.on_focus_change)
            hook.unsubscribe.setgroup(self.on_focus_change)
            self.reset()
