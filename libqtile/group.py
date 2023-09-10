from __future__ import annotations

from typing import TYPE_CHECKING

from libqtile import hook, utils
from libqtile.config import ScreenRect
from libqtile.backend.base import WindowStates
from libqtile.command.base import CommandError, CommandObject, expose_command
from libqtile.log_utils import logger

if TYPE_CHECKING:
    from libqtile.command.base import ItemT


class _Group(CommandObject):
    """A container for a bunch of windows

    Analogous to workspaces in other window managers. Each client window
    managed by the window manager belongs to exactly one group.

    A group is identified by its name but displayed in GroupBox widget by its label.
    """

    def __init__(self, name, layout=None, label=None, screen_affinity=None, persist=False):
        self.screen_affinity = screen_affinity
        self.name = name
        self.label = name if label is None else label
        self.custom_layout = layout  # will be set on _configure
        self.previous_in_layout = []
        self.tiled_windows = set()
        self.windows = []
        self.qtile = None
        self.layouts = []
        self.floating_layout = None
        self.fullscreen_layout = None
        # self.focus_history lists the group's windows in the order they
        # received focus, from the oldest (first item) to the currently
        # focused window (last item); NB the list does *not* contain any
        # windows that never received focus; refer to self.windows for the
        # complete set
        self.focus_history = []
        self.screen = None
        self.current_layout = None
        self.last_focused = None
        self.persist = persist

    def _configure(self, layouts, floating_layout, fullscreen_layout, qtile):
        self.screen = None
        self.current_layout = 0
        self.focus_history = []
        self.windows = []
        self.qtile = qtile
        self.layouts = [i.clone(self) for i in layouts]
        self.floating_layout = floating_layout.clone(self)
        self.fullscreen_layout = fullscreen_layout.clone(self)
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
        # TODO: Do these if statements in use_layout instead
        curr = self.layouts[self.current_layout]
        if curr._manages_win_state == WindowStates.FLOATING:
            return self.floating_layout
        if curr._manages_win_state == WindowStates.FULLSCREEN:
            return self.fullscreen_layout
        return curr

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
                self.use_layout(index)
                return
        logger.error("No such layout: %s", layout)

    def use_layout(self, index: int):
        assert -len(self.layouts) <= index < len(self.layouts), "layout index out of bounds"
        self.layout.hide()
        self.current_layout = index % len(self.layouts)
        hook.fire("layout_change", self.layout, self)
        for x in self.windows:
            # Make sure the client is in the right layer
            # This happens for clients that are "tiling"
            # And also for floating,fullscreen,maximized windows that are only that because the current layout manages these windows
            # This makes it so that any windows which had the state manually set by the user will not be fiddled with (e.g. manually toggled fullscreen windows with toggle_fullscreen() will stay fullscreen when a switch happened to tiling windows)
            # But windows that are only fullscreen because the previous layout was fullscreen will switch to tiling
            if x._win_state_follows and x._win_state != self.layout._manages_win_state:
                self.switch_layer_noninteractive(x)
        self.layout_all()
        if self.screen is not None:
            screen_rect = self.get_screen_rect()
            self.layout.show(screen_rect)

    def use_next_layout(self):
        self.use_layout((self.current_layout + 1) % (len(self.layouts)))

    def use_previous_layout(self):
        self.use_layout((self.current_layout - 1) % (len(self.layouts)))

    def get_screen_rect(self, force_full=None) -> ScreenRect:
        if force_full is None:
            force_full = self.layout._manages_win_state == WindowStates.FULLSCREEN
        if force_full:
            return ScreenRect(self.screen.x, self.screen.y, self.screen.width, self.screen.height)
        return self.screen.get_rect()

    def switch_layer_noninteractive(self, client):
        # Remove from alt layouts if exists
        self.remove_alt_layouts(client)
        # We will set the win state to the managed layout
        # If we switch to a tiling layout, add the window
        if self.layout._manages_win_state == WindowStates.TILED:
            # This already checks if it's not in there already
            self.add_to_layouts(client)
        elif self.layout._manages_win_state == WindowStates.FULLSCREEN:
            self.fullscreen_layout.add_client(client)
        elif self.layout._manages_win_state == WindowStates.FLOATING:
            self.floating_layout.add_client(client)
        client._win_state = self.layout._manages_win_state

    def layout_all(self, warp=False, focus=True):
        """Layout the floating layer, then the current layout.

        Parameters
        ==========
        focus :
            If we have have a current_window give it focus, optionally moving warp
            to it.
        """
        if self.screen and self.windows:
            with self.qtile.core.masked():
                mainers = []
                floaters = []
                fullers = []
                maxers = []
                for x in self.windows:
                    # This is the main layer
                    if x._win_state == self.layout._manages_win_state:
                        mainers.append(x)
                    # The other layers are used if the window is that state but the current layout does not manage that state
                    elif x.floating:
                        floaters.append(x)
                    elif x.fullscreen:
                        fullers.append(x)
                    elif x.maximized:
                        maxers.append(x)
                screen_rect = self.get_screen_rect()
                if mainers:
                    try:
                        self.layout.layout(mainers, screen_rect)
                    except Exception:
                        logger.exception("Exception in layout %s", self.layout.name)
                if floaters:
                    self.floating_layout.layout(floaters, screen_rect)
                if fullers:
                    self.fullscreen_layout.layout(fullers, self.get_screen_rect(force_full=True))
                if focus:
                    if self.current_window and self.screen == self.qtile.current_screen:
                        self.current_window.focus(warp)
                    else:
                        # Screen has lost focus so we reset record of focused window so
                        # focus will warp when screen is focused again
                        self.last_focused = None
        elif self.screen and not self.windows and self.screen == self.qtile.current_screen:
            # Clear active window when switching to an empty group on the current screen
            self.qtile.core.clear_focus()

    def set_screen(self, screen, warp=True):
        """Set this group's screen to screen"""
        if screen == self.screen:
            return
        self.screen = screen
        if self.screen:
            # move all floating guys offset to new screen
            self.floating_layout.to_screen(self, self.screen)
            self.layout_all(warp=warp and self.qtile.config.cursor_warp)
            screen_rect = self.get_screen_rect()
            self.floating_layout.show(screen_rect)
            self.layout.show(screen_rect)
        else:
            self.hide()

    def hide(self):
        self.screen = None
        with self.qtile.core.masked():
            for i in self.windows:
                i.hide()
            self.layout.hide()

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

            # ignore focus events if window is the current window
            if win is self.last_focused:
                warp = False

            self.current_window = win
            self.last_focused = self.current_window
            if win.fullscreen:
                for layout in self.layouts:
                    layout.blur()
                self.fullscreen_layout.focus(win)
            elif win.floating:
                for layout in self.layouts:
                    layout.blur()
                self.floating_layout.focus(win)
            else:
                self.floating_layout.blur()
                self.fullscreen_layout.blur()
                for layout in self.layouts:
                    layout.focus(win)
            hook.fire("focus_change")
            self.layout_all(warp)

    @expose_command()
    def info(self):
        """Returns a dictionary of info for this group"""
        return dict(
            name=self.name,
            label=self.label,
            focus=self.current_window.name if self.current_window else None,
            tiled_windows={i.name for i in self.windows if i.tiling},
            windows=[i.name for i in self.windows],
            focus_history=[i.name for i in self.focus_history],
            layout=self.layout.name,
            layouts=[i.name for i in self.layouts],
            floating_info=self.floating_layout.info(),
            screen=self.screen.index if self.screen else None,
        )

    def add(self, win, force=False):
        hook.fire("group_window_add", self, win)
        if win not in self.windows:
            self.windows.append(win)
        win.group = self
        # Tiling windows follow the current layout's window state
        keep_layer = False
        if win._win_state is None or win.tiling:
            win._win_state = self.layout._manages_win_state
        if self.qtile.config.auto_fullscreen and win.wants_to_fullscreen:
            win._win_state = WindowStates.FULLSCREEN
            keep_layer = True
        elif self.floating_layout.match(win):
            win._win_state = WindowStates.FLOATING
            if self.qtile.config.floats_kept_above:
                win.keep_above(enable=True)
            keep_layer = True
        if win.floating:
            self.floating_layout.add_client(win)
        if win.fullscreen:
            self.fullscreen_layout.add_client(win)
        if win.tiling:
            self.add_to_layouts(win)
        win._win_state_follows = win._win_state == self.layout._manages_win_state
        if keep_layer:
            win._win_state_follows = False
        if win.can_steal_focus:
            self.focus(win, warp=True, force=force)
        else:
            self.layout_all(focus=False)

    def remove(self, win, force=False):
        hook.fire("group_window_remove", self, win)

        if self.qtile.config.focus_previous_on_window_remove:
            index = self.focus_history.index(win)
            try:
                previous_win = self.focus_history[index - 1]
            except IndexError:
                previous_win = None
            if previous_win not in self.windows:
                previous_win = None
        else:
            previous_win = None

        self.windows.remove(win)
        hadfocus = self._remove_from_focus_history(win)
        win.group = None
        nextfocus = None

        # Remove from the tiled layouts if present
        if win in self.tiled_windows:
            for i in self.layouts:
                if i is self.layout:
                    nextfocus = i.remove(win)
                else:
                    i.remove(win)

            self.tiled_windows.remove(win)

        if win.floating:
            nextfocus = self.floating_layout.remove(win)

            nextfocus = (
                previous_win
                or nextfocus
                or self.current_window
                or self.layout.focus_first()
                or self.floating_layout.focus_first(group=self)
                or self.fullscreen_layout.focus_first()
            )
        else:
            nextfocus = self.fullscreen_layout.remove(win)

            nextfocus = (
                previous_win
                or nextfocus
                or self.floating_layout.focus_first(group=self)
                or self.current_window
                or self.layout.focus_first()
                or self.fullscreen_layout.focus_first()
            )


        # a notification may not have focus
        if hadfocus:
            self.focus(nextfocus, warp=True, force=force)
            # no next focus window means focus changed to nothing
            if not nextfocus:
                hook.fire("focus_change")
        elif self.screen:
            self.layout_all()

    def remove_alt_layouts(self, win):
        if win.fullscreen:
            self.fullscreen_layout.remove(win)
            self.fullscreen_layout.blur()
        if win.floating:
            self.floating_layout.remove(win)
            self.floating_layout.blur()

    def mark_fullscreen(self, win):
        win._win_state_follows = False
        if win.fullscreen:
            return
        self.remove_alt_layouts(win)
        self.remove_from_layouts(win, pseudo=True)
        self.fullscreen_layout.add_client(win)
        if win is self.current_window:
            self.fullscreen_layout.focus(win)
        win._win_state = WindowStates.FULLSCREEN
        self.layout_all()

    def mark_tiling(self, win):
        if win.tiling:
            return
        win._win_state_follows = True
        if self.layout._manages_win_state != WindowStates.TILED:
            raise CommandError("The current layout does not support tiling windows")
        self.remove_alt_layouts(win)
        self.add_to_layouts(win)
        win._win_state = WindowStates.TILED
        self.layout_all()

    def add_to_layouts(self, win):
        if win not in self.tiled_windows:
            for i in self.layouts:
                i.add_client(win)
                if win is self.current_window:
                    i.focus(win)
                self.tiled_windows.add(win)

    def remove_from_layouts(self, win, pseudo=False):
        if win in self.tiled_windows:
            for i in self.layouts:
                if not pseudo:
                    i.remove(win)
                if win is self.current_window:
                    i.blur()
            if not pseudo:
                self.tiled_windows.remove(win)

    def mark_floating(self, win):
        win._win_state_follows = False
        if win.floating:
            return
        self.remove_alt_layouts(win)
        self.remove_from_layouts(win)
        self.floating_layout.add_client(win)
        if win is self.current_window:
            self.floating_layout.focus(win)
        win._win_state = WindowStates.FLOATING
        self.layout_all()

    def _items(self, name) -> ItemT:
        if name == "layout":
            return True, list(range(len(self.layouts)))
        if name == "screen" and self.screen is not None:
            return True, []
        if name == "window":
            return self.current_window is not None, [i.wid for i in self.windows]
        return None

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
                if i.wid == sel:
                    return i
        raise RuntimeError(f"Invalid selection: {name}")

    @expose_command()
    def setlayout(self, layout):
        self.layout = layout

    @expose_command()
    def toscreen(self, screen=None, toggle=False):
        """Pull a group to a specified screen.

        Parameters
        ==========
        screen :
            Screen offset. If not specified, we assume the current screen.
        toggle :
            If this group is already on the screen, then the group is toggled
            with last used

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

        if screen.group == self:
            if toggle:
                screen.toggle_group(self)
        else:
            screen.set_group(self)

        self.qtile.core.check_screen_fullscreen_background(screen)

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
            from libqtile import scratchpad

            if group is self:
                return True
            if skip_empty and not group.windows:
                return False
            if skip_managed and group.screen:
                return False
            if isinstance(group, scratchpad.ScratchPad):
                return False
            return True

        try:
            groups = [group for group in self.qtile.groups if match(group)]
            index = (groups.index(self) + direction) % len(groups)
            return groups[index]
        except ValueError:
            # group is not managed
            return None

    def get_previous_group(self, skip_empty=False, skip_managed=False):
        return self._get_group(-1, skip_empty, skip_managed)

    def get_next_group(self, skip_empty=False, skip_managed=False):
        return self._get_group(1, skip_empty, skip_managed)

    @expose_command()
    def unminimize_all(self):
        """Unminimise all windows in this group"""
        for win in self.windows:
            win.minimized = False
        self.layout_all()

    @expose_command()
    def next_window(self):
        """
        Focus the next window in group.

        Method cycles _all_ windows in group regardless if tiled in current
        layout or floating. Cycling of tiled and floating windows is not mixed.
        The cycling order depends on the current Layout.
        """
        if not self.windows:
            return
        if self.current_window.fullscreen:
            nxt = (
                self.fullscreen_layout.focus_next(self.current_window)
                or self.layout.focus_first()
                or self.fullscreen_layout.focus_first(group=self)
            )
        elif self.current_window.floating:
            nxt = (
                self.floating_layout.focus_next(self.current_window)
                or self.layout.focus_first()
                or self.floating_layout.focus_first(group=self)
            )
        else:
            nxt = (
                self.layout.focus_next(self.current_window)
                or self.floating_layout.focus_first(group=self)
                or self.layout.focus_first()
            )
        self.focus(nxt, True)

    @expose_command()
    def prev_window(self):
        """
        Focus the previous window in group.

        Method cycles _all_ windows in group regardless if tiled in current
        layout or floating. Cycling of tiled and floating windows is not mixed.
        The cycling order depends on the current Layout.
        """
        if not self.windows:
            return
        if self.current_window.fullscreen:
            nxt = (
                self.fullscreen_layout.focus_previous(self.current_window)
                or self.layout.focus_last()
                or self.fullscreen_layout.focus_last(group=self)
            )
        elif self.current_window.floating:
            nxt = (
                self.floating_layout.focus_previous(self.current_window)
                or self.layout.focus_last()
                or self.floating_layout.focus_last(group=self)
            )
        else:
            nxt = (
                self.layout.focus_previous(self.current_window)
                or self.floating_layout.focus_last(group=self)
                or self.layout.focus_last()
            )
        self.focus(nxt, True)

    @expose_command()
    def focus_back(self):
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

    @expose_command()
    def focus_by_name(self, name):
        """
        Focus the first window with the given name. Do nothing if the name is
        not found.
        """
        for win in self.windows:
            if win.name == name:
                self.focus(win)
                break

    @expose_command()
    def info_by_name(self, name):
        """
        Get the info for the first window with the given name without giving it
        focus. Do nothing if the name is not found.
        """
        for win in self.windows:
            if win.name == name:
                return win.info()

    @expose_command()
    def focus_by_index(self, index: int) -> None:
        """
        Change to the window at the specified index in the current group.
        """
        windows = self.windows
        if index < 0 or index > len(windows) - 1:
            return

        self.focus(windows[index])

    @expose_command()
    def swap_window_order(self, new_location: int) -> None:
        """
        Change the order of the current window within the current group.
        """
        if new_location < 0 or new_location > len(self.windows) - 1:
            return

        windows = self.windows
        current_window_index = windows.index(self.current_window)

        windows[current_window_index], windows[new_location] = (
            windows[new_location],
            windows[current_window_index],
        )

    @expose_command()
    def switch_groups(self, name):
        """Switch position of current group with name"""
        self.qtile.switch_groups(self.name, name)

    @expose_command()
    def set_label(self, label):
        """
        Set the display name of current group to be used in GroupBox widget.
        If label is None, the name of the group is used as display name.
        If label is the empty string, the group is invisible in GroupBox.
        """
        self.label = label if label is not None else self.name
        hook.fire("changegroup")

    def __repr__(self):
        return f"<group.Group ({self.name!r})>"
