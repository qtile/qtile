import command
import hook
import window
import utils
import contextlib
import xcb
import xcb.xproto


class _Group(command.CommandObject):
    """
        A group is a container for a bunch of windows, analogous to workspaces
        in other window managers. Each client window managed by the window
        manager belongs to exactly one group.
    """
    def __init__(self, name, layout=None):
        self.name = name
        self.customLayout = layout  # will be set on _configure
        self.windows = set()
        self.qtile = None
        self.layouts = []
        self.floating_layout = None
        self.currentWindow = None
        self.screen = None
        self.currentLayout = None

    def _configure(self, layouts, floating_layout, qtile):
        self.screen = None
        self.currentLayout = 0
        self.currentWindow = None
        self.windows = set()
        self.qtile = qtile
        self.layouts = [i.clone(self) for i in layouts]
        self.floating_layout = floating_layout.clone(self)
        if self.customLayout is not None:
            self.layout = self.customLayout
            self.customLayout = None

    @property
    def layout(self):
        return self.layouts[self.currentLayout]

    @layout.setter
    def layout(self, layout):
        """
            "layout" is a string with matching the name of a Layout object.
        """
        for index, obj in enumerate(self.layouts):
            if obj.name == layout:
                self.currentLayout = index
                hook.fire(
                    "layout_change",
                    self.layouts[self.currentLayout],
                    self
                )
                self.layoutAll()
                return
        raise ValueError("No such layout: %s" % layout)

    def nextLayout(self):
        self.layout.hide()
        self.currentLayout = (self.currentLayout + 1) % (len(self.layouts))
        hook.fire("layout_change", self.layouts[self.currentLayout], self)
        self.layoutAll()
        screen = self.screen.get_rect()
        self.layout.show(screen)

    def prevLayout(self):
        self.layout.hide()
        self.currentLayout = (self.currentLayout - 1) % (len(self.layouts))
        hook.fire("layout_change", self.layouts[self.currentLayout], self)
        self.layoutAll()
        screen = self.screen.get_rect()
        self.layout.show(screen)

    def layoutAll(self, warp=False):
        """
        Layout the floating layer, then the current layout.

        If we have have a currentWindow give it focus, optionally
        moving warp to it.
        """
        if self.screen and len(self.windows):
            with self.disableMask(xcb.xproto.EventMask.EnterWindow):
                normal = [x for x in self.windows if not x.floating]
                floating = [
                    x for x in self.windows
                    if x.floating and not x.minimized
                ]
                screen = self.screen.get_rect()
                if normal:
                    self.layout.layout(normal, screen)
                if floating:
                    self.floating_layout.layout(floating, screen)
                if self.currentWindow and \
                        self.screen == self.qtile.currentScreen:
                    self.currentWindow.focus(warp)

    def _setScreen(self, screen):
        """
        Set this group's screen to new_screen
        """
        if screen == self.screen:
            return
        self.screen = screen
        if self.screen:
            # move all floating guys offset to new screen
            self.floating_layout.to_screen(self.screen)
            self.layoutAll()
            rect = self.screen.get_rect()
            self.floating_layout.show(rect)
            self.layout.show(rect)
        else:
            self.hide()

    def hide(self):
        self.screen = None
        with self.disableMask(xcb.xproto.EventMask.EnterWindow |
                              xcb.xproto.EventMask.FocusChange |
                              xcb.xproto.EventMask.LeaveWindow):
            for i in self.windows:
                i.hide()
            self.layout.hide()

    @contextlib.contextmanager
    def disableMask(self, mask):
        for i in self.windows:
            i._disableMask(mask)
        yield
        for i in self.windows:
            i._resetMask()

    def focus(self, win, warp):
        """
            if win is in the group, blur any windows and call
            ``focus`` on the layout (in case it wants to track
            anything), fire focus_change hook and invoke layoutAll.

            warp - warp pointer to win
        """
        if self.qtile._drag:
            # don't change focus while dragging windows
            return
        if win:
            if not win in self.windows:
                return
            else:
                self.currentWindow = win
                if win.floating:
                    for l in self.layouts:
                        l.blur()
                    self.floating_layout.focus(win)
                else:
                    self.floating_layout.blur()
                    for l in self.layouts:
                        l.focus(win)
        else:
            self.currentWindow = None
        hook.fire("focus_change")
        # !!! note that warp isn't hooked up now
        self.layoutAll(warp)

    def info(self):
        return dict(
            name=self.name,
            focus=self.currentWindow.name if self.currentWindow else None,
            windows=[i.name for i in self.windows],
            layout=self.layout.name,
            floating_info=self.floating_layout.info(),
            screen=self.screen.index if self.screen else None
        )

    def add(self, win):
        hook.fire("group_window_add")
        self.windows.add(win)
        win.group = self
        try:
            if win.window.get_net_wm_state() == 'fullscreen' and \
                    self.qtile.config.auto_fullscreen:
                win._float_state = window.FULLSCREEN
            elif self.floating_layout.match(win):
                # !!! tell it to float, can't set floating
                # because it's too early
                # so just set the flag underneath
                win._float_state = window.FLOATING
        except (xcb.xproto.BadWindow, xcb.xproto.BadAccess):
            pass  # doesn't matter
        if win.floating:
            self.floating_layout.add(win)
        else:
            for i in self.layouts:
                i.add(win)
        self.focus(win, True)

    def remove(self, win):
        self.windows.remove(win)
        win.group = None
        nextfocus = None
        if win.floating:
            nextfocus = self.floating_layout.remove(win)
            if nextfocus is None:
                nextfocus = self.layout.focus_first()
            if nextfocus is None:
                nextfocus = self.floating_layout.focus_first()
        else:
            for i in self.layouts:
                if i is self.layout:
                    nextfocus = i.remove(win)
                else:
                    i.remove(win)
            if nextfocus is None:
                nextfocus = self.floating_layout.focus_first()
            if nextfocus is None:
                nextfocus = self.layout.focus_first()
        self.focus(nextfocus, True)
        #else: TODO: change focus

    def mark_floating(self, win, floating):
        if floating and win in self.floating_layout.clients:
            # already floating
            pass
        elif floating:
            for i in self.layouts:
                i.remove(win)
                if win is self.currentWindow:
                    i.blur()
            self.floating_layout.add(win)
            if win is self.currentWindow:
                self.floating_layout.focus(win)
        else:
            self.floating_layout.remove(win)
            self.floating_layout.blur()
            for i in self.layouts:
                i.add(win)
                if win is self.currentWindow:
                    i.focus(win)
        self.layoutAll()

    def _items(self, name):
        if name == "layout":
            return (True, range(len(self.layouts)))
        elif name == "window":
            return (True, [i.window.wid for i in self.windows])
        elif name == "screen":
            return (True, None)

    def _select(self, name, sel):
        if name == "layout":
            if sel is None:
                return self.layout
            else:
                return utils.lget(self.layouts, sel)
        elif name == "window":
            if sel is None:
                return self.currentWindow
            else:
                for i in self.windows:
                    if i.window.wid == sel:
                        return i
        elif name == "screen":
            return self.screen

    def cmd_setlayout(self, layout):
        self.layout = layout

    def cmd_info(self):
        """
            Returns a dictionary of info for this group.
        """
        return self.info()

    def cmd_toscreen(self, screen=None):
        """
            Pull a group to a specified screen.

            - screen: Screen offset. If not specified,
                      we assume the current screen.

            Pull group to the current screen:
                toscreen()

            Pull group to screen 0:
                toscreen(0)
        """
        if screen is None:
            screen = self.qtile.currentScreen
        else:
            screen = self.qtile.screens[screen]
        screen.setGroup(self)

    def _dirGroup(self, direction, skip_empty=False, skip_managed=False):
        """
        Find a group walking the groups list in the specified
        direction.

        skip_empty skips the empty groups
        skip_managed skips the groups that have a screen
        """
        index = currentgroup = self.qtile.groups.index(self)
        while True:
            index = (index + direction) % len(self.qtile.groups)
            group = self.qtile.groups[index]

            matches = False
            if skip_empty and skip_managed and \
                    group.windows and not group.screen:
                matches = True
            elif skip_empty and group.windows:
                matches = True
            elif skip_managed and not group.screen:
                matches = True

            if index == currentgroup or matches:
                return group

    def prevGroup(self, skip_empty=False, skip_managed=False):
        return self._dirGroup(-1, skip_empty, skip_managed)

    def nextGroup(self, skip_empty=False, skip_managed=False):
        return self._dirGroup(1, skip_empty, skip_managed)

    def cmd_unminimise_all(self):
        """
            Unminimise all windows in this group.
        """
        for w in self.windows:
            w.minimised = False
        self.layoutAll()

    def cmd_next_window(self):
        if not self.windows:
            return
        if self.currentWindow.floating:
            nxt = self.floating_layout.focus_next(self.currentWindow) or \
                self.layout.focus_first() or \
                self.floating_layout.focus_first()
        else:
            nxt = self.layout.focus_next(self.currentWindow) or \
                self.floating_layout.focus_first() or \
                self.layout.focus_first()
        self.focus(nxt, True)

    def cmd_prev_window(self):
        if not self.windows:
            return
        if self.currentWindow.floating:
            nxt = self.floating_layout.focus_prev(self.currentWindow) or \
                self.layout.focus_last() or \
                self.floating_layout.focus_last()
        else:
            nxt = self.layout.focus_prev(self.currentWindow) or \
                self.floating_layout.focus_last() or \
                self.layout.focus_last()
        self.focus(nxt, True)

    def cmd_switch_groups(self, name):
        """
            Switch position of current group with name
        """
        self.qtile.cmd_switch_groups(self.name, name)
