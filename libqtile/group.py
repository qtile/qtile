# Copyright (c) 2012-2014 Tycho Andersen
# Copyright (c) 2013 xarvh
# Copyright (c) 2013 roger
# Copyright (c) 2013 Tao Sauvage
# Copyright (c) 2014 ramnes
# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 dequis
# Copyright (c) 2015 Dario Giovannetti
# Copyright (c) 2015 Alexander Lozovskoy
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

import contextlib
import xcffib
import xcffib.xproto

from libqtile.command_object import CommandObject
from . import hook
from . import window
from . import utils
from .log_utils import logger


class _Group(CommandObject):
    """A container for a bunch of windows

    Analogous to workspaces in other window managers. Each client window
    managed by the window manager belongs to exactly one group.

    A group is identified by its name but displayed in GroupBox widget by its label.
    """
    def __init__(self, name, layout=None, label=None):
        self.name = name
        self.label = name if label is None else label
        self.custom_layout = layout  # will be set on _configure
        self.windows = set()
        self.qtile = None
        self.layouts = []
        self.floating_layout = None
        # self.focus_history lists the group's windows in the order they
        # received focus, from the oldest (first item) to the currently
        # focused window (last item); NB the list does *not* contain any
        # windows that never received focus; refer to self.windows for the
        # complete set
        self.focus_history = []
        self.screen = None
        self.current_layout = None

    def _configure(self, layouts, floating_layout, qtile):
        self.screen = None
        self.current_layout = 0
        self.focus_history = []
        self.windows = set()
        self.qtile = qtile
        self.layouts = [i.clone(self) for i in layouts]
        self.floating_layout = floating_layout
        if self.custom_layout is not None:
            self.layout = self.custom_layout
            self.custom_layout = None

    @property
    def current_window(self):
        try:
            return self.focus_history[-1]
        except IndexError:
            # no window has focus
            return None

    @current_window.setter
    def current_window(self, win):
        try:
            self.focus_history.remove(win)
        except ValueError:
            # win has never received focus before
            pass
        self.focus_history.append(win)

    def _remove_from_focus_history(self, win):
        try:
            index = self.focus_history.index(win)
        except ValueError:
            # win has never received focus
            return False
        else:
            del self.focus_history[index]
            # return True if win was the last item (i.e. it was current_window)
            return index == len(self.focus_history)

    @property
    def layout(self):
        return self.layouts[self.current_layout]

    @layout.setter
    def layout(self, layout):
        """
        Parameters
        ==========
        layout :
            a string with matching the name of a Layout object.
        """
        for index, obj in enumerate(self.layouts):
            if obj.name == layout:
                self.current_layout = index
                hook.fire(
                    "layout_change",
                    self.layouts[self.current_layout],
                    self
                )
                self.layout_all()
                return
        raise ValueError("No such layout: %s" % layout)

    def use_layout(self, index):
        assert 0 <= index < len(self.layouts), "layout index out of bounds"
        self.layout.hide()
        self.current_layout = index
        hook.fire("layout_change", self.layouts[self.current_layout], self)
        self.layout_all()
        screen = self.screen.get_rect()
        self.layout.show(screen)

    def use_next_layout(self):
        self.use_layout((self.current_layout + 1) % (len(self.layouts)))

    def use_previous_layout(self):
        self.use_layout((self.current_layout - 1) % (len(self.layouts)))

    def layout_all(self, warp=False):
        """Layout the floating layer, then the current layout.

        If we have have a current_window give it focus, optionally moving warp
        to it.
        """
        if self.screen and self.windows:
            with self.disable_mask(xcffib.xproto.EventMask.EnterWindow):
                normal = [x for x in self.windows if not x.floating]
                floating = [
                    x for x in self.windows
                    if x.floating and not x.minimized
                ]
                screen = self.screen.get_rect()
                if normal:
                    try:
                        self.layout.layout(normal, screen)
                    except Exception:
                        logger.exception("Exception in layout %s",
                                         self.layout.name)
                if floating:
                    self.floating_layout.layout(floating, screen)
                if self.current_window and \
                        self.screen == self.qtile.current_screen:
                    self.current_window.focus(warp)

    def _set_screen(self, screen):
        """Set this group's screen to new_screen"""
        if screen == self.screen:
            return
        self.screen = screen
        if self.screen:
            # move all floating guys offset to new screen
            self.floating_layout.to_screen(self, self.screen)
            self.layout_all(warp=self.qtile.config.cursor_warp)
            rect = self.screen.get_rect()
            self.floating_layout.show(rect)
            self.layout.show(rect)
        else:
            self.hide()

    def hide(self):
        self.screen = None
        with self.disable_mask(xcffib.xproto.EventMask.EnterWindow |
                               xcffib.xproto.EventMask.FocusChange |
                               xcffib.xproto.EventMask.LeaveWindow):
            for i in self.windows:
                i.hide()
            self.layout.hide()

    @contextlib.contextmanager
    def disable_mask(self, mask):
        for i in self.windows:
            i._disable_mask(mask)
        yield
        for i in self.windows:
            i._reset_mask()

    def focus(self, win, warp=True, force=False):
        """Focus the given window

        If win is in the group, blur any windows and call ``focus`` on the
        layout (in case it wants to track anything), fire focus_change hook and
        invoke layout_all.

        Parameters
        ==========
        win :
            Window to focus
        warp :
            Warp pointer to win. This should basically always be True, unless
            the focus event is coming from something like EnterNotify, where
            the user is actively using the mouse, or on full screen layouts
            where only one window is "maximized" at a time, and it doesn't make
            sense for the mouse to automatically move.
        """
        if self.qtile._drag and not force:
            # don't change focus while dragging windows (unless forced)
            return
        if win:
            if win not in self.windows:
                return
            self.current_window = win
            if win.floating:
                for layout in self.layouts:
                    layout.blur()
                self.floating_layout.focus(win)
            else:
                self.floating_layout.blur()
                for layout in self.layouts:
                    layout.focus(win)
            hook.fire("focus_change")
            self.layout_all(warp)

    def info(self):
        return dict(
            name=self.name,
            label=self.label,
            focus=self.current_window.name if self.current_window else None,
            windows=[i.name for i in self.windows],
            focus_history=[i.name for i in self.focus_history],
            layout=self.layout.name,
            layouts=[l.name for l in self.layouts],
            floating_info=self.floating_layout.info(),
            screen=self.screen.index if self.screen else None
        )

    def add(self, win, focus=True, force=False):
        hook.fire("group_window_add")
        self.windows.add(win)
        win.group = self
        try:
            if 'fullscreen' in win.window.get_net_wm_state() and \
                    self.qtile.config.auto_fullscreen:
                win._float_state = window.FULLSCREEN
            elif self.floating_layout.match(win):
                # !!! tell it to float, can't set floating
                # because it's too early
                # so just set the flag underneath
                win._float_state = window.FLOATING
        except (xcffib.xproto.WindowError, xcffib.xproto.AccessError):
            pass  # doesn't matter
        if win.floating:
            self.floating_layout.add(win)
        else:
            for i in self.layouts:
                i.add(win)
        if focus:
            self.focus(win, warp=True, force=force)

    def remove(self, win, force=False):
        self.windows.remove(win)
        hadfocus = self._remove_from_focus_history(win)
        win.group = None

        if win.floating:
            nextfocus = self.floating_layout.remove(win)

            nextfocus = nextfocus or \
                self.current_window or \
                self.layout.focus_first() or \
                self.floating_layout.focus_first(group=self)
        else:
            for i in self.layouts:
                if i is self.layout:
                    nextfocus = i.remove(win)
                else:
                    i.remove(win)

            nextfocus = nextfocus or \
                self.floating_layout.focus_first(group=self) or \
                self.current_window or \
                self.layout.focus_first()

        # a notification may not have focus
        if hadfocus:
            self.focus(nextfocus, warp=True, force=force)
            # no next focus window means focus changed to nothing
            if not nextfocus:
                hook.fire("focus_change")
        elif self.screen:
            self.layout_all()

    def mark_floating(self, win, floating):
        if floating:
            if win in self.floating_layout.find_clients(self):
                # already floating
                pass
            else:
                for i in self.layouts:
                    i.remove(win)
                    if win is self.current_window:
                        i.blur()
                self.floating_layout.add(win)
                if win is self.current_window:
                    self.floating_layout.focus(win)
        else:
            self.floating_layout.remove(win)
            self.floating_layout.blur()
            for i in self.layouts:
                i.add(win)
                if win is self.current_window:
                    i.focus(win)
        self.layout_all()

    def _items(self, name):
        if name == "layout":
            return (True, list(range(len(self.layouts))))
        if name == "screen":
            return (True, None)
        if name == "window":
            return (True, [i.window.wid for i in self.windows])
        raise RuntimeError("Invalid item: {}".format(name))

    def _select(self, name, sel):
        if name == "layout":
            if sel is None:
                return self.layout
            return utils.lget(self.layouts, sel)
        if name == "screen":
            return self.screen
        if name == "window":
            if sel is None:
                return self.current_window
            for i in self.windows:
                if i.window.wid == sel:
                    return i
        raise RuntimeError("Invalid selection: {}".format(name))

    def cmd_setlayout(self, layout):
        self.layout = layout

    def cmd_info(self):
        """Returns a dictionary of info for this group"""
        return self.info()

    def cmd_toscreen(self, screen=None):
        """Pull a group to a specified screen.

        Parameters
        ==========
        screen :
            Screen offset. If not specified, we assume the current screen.

        Examples
        ========
        Pull group to the current screen::

            toscreen()

        Pull group to screen 0::

            toscreen(0)
        """
        if screen is None:
            screen = self.qtile.current_screen
        else:
            screen = self.qtile.screens[screen]
        screen.set_group(self)

    def _get_group(self, direction, skip_empty=False, skip_managed=False):
        """Find a group walking the groups list in the specified direction

        Parameters
        ==========
        skip_empty :
            skips the empty groups
        skip_managed :
            skips the groups that have a screen
        """

        def match(group):
            from . import scratchpad

            if group is self:
                return True
            if skip_empty and not group.windows:
                return False
            if skip_managed and group.screen:
                return False
            if isinstance(group, scratchpad.ScratchPad):
                return False
            return True

        groups = [group for group in self.qtile.groups if match(group)]
        index = (groups.index(self) + direction) % len(groups)
        return groups[index]

    def get_previous_group(self, skip_empty=False, skip_managed=False):
        return self._get_group(-1, skip_empty, skip_managed)

    def get_next_group(self, skip_empty=False, skip_managed=False):
        return self._get_group(1, skip_empty, skip_managed)

    def cmd_unminimize_all(self):
        """Unminimise all windows in this group"""
        for win in self.windows:
            win.minimized = False
        self.layout_all()

    def cmd_next_window(self):
        """
        Focus the next window in group.

        Method cycles _all_ windows in group regardless if tiled in current
        layout or floating. Cycling of tiled and floating windows is not mixed.
        The cycling order depends on the current Layout.
        """
        if not self.windows:
            return
        if self.current_window.floating:
            nxt = self.floating_layout.focus_next(self.current_window) or \
                self.layout.focus_first() or \
                self.floating_layout.focus_first(group=self)
        else:
            nxt = self.layout.focus_next(self.current_window) or \
                self.floating_layout.focus_first(group=self) or \
                self.layout.focus_first()
        self.focus(nxt, True)

    def cmd_prev_window(self):
        """
        Focus the previous window in group.

        Method cycles _all_ windows in group regardless if tiled in current
        layout or floating. Cycling of tiled and floating windows is not mixed.
        The cycling order depends on the current Layout.
        """
        if not self.windows:
            return
        if self.current_window.floating:
            nxt = self.floating_layout.focus_previous(self.current_window) or \
                self.layout.focus_last() or \
                self.floating_layout.focus_last(group=self)
        else:
            nxt = self.layout.focus_previous(self.current_window) or \
                self.floating_layout.focus_last(group=self) or \
                self.layout.focus_last()
        self.focus(nxt, True)

    def cmd_focus_back(self):
        """
        Focus the window that had focus before the current one got it.

        Repeated calls to this function would basically continuously switch
        between the last two focused windows. Do nothing if less than 2
        windows ever received focus.
        """
        try:
            win = self.focus_history[-2]
        except IndexError:
            pass
        else:
            self.focus(win)

    def cmd_focus_by_name(self, name):
        """
        Focus the first window with the given name. Do nothing if the name is
        not found.
        """
        for win in self.windows:
            if win.name == name:
                self.focus(win)
                break

    def cmd_info_by_name(self, name):
        """
        Get the info for the first window with the given name without giving it
        focus. Do nothing if the name is not found.
        """
        for win in self.windows:
            if win.name == name:
                return win.info()

    def cmd_switch_groups(self, name):
        """Switch position of current group with name"""
        self.qtile.cmd_switch_groups(self.name, name)

    def cmd_set_label(self, label):
        """
        Set the display name of current group to be used in GroupBox widget.
        If label is None, the name of the group is used as display name.
        If label is the empty string, the group is invisible in GroupBox.
        """
        self.label = label if label is not None else self.name
        hook.fire("changegroup")

    def __repr__(self):
        return "<group.Group (%r)>" % self.name
