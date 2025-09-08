# Copyright (c) 2019 Aldo Cortesi
# Copyright (c) 2019 Sean Vig
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

import asyncio
import contextlib
import os
import signal
import time
from typing import TYPE_CHECKING

import xcffib
import xcffib.randr
import xcffib.render
import xcffib.xproto
import xcffib.xtest
from xcffib.xproto import EventMask

from libqtile import config, hook, utils
from libqtile.backend import base
from libqtile.backend.x11 import window, xcbq
from libqtile.backend.x11.xkeysyms import keysyms
from libqtile.config import ScreenRect
from libqtile.log_utils import logger
from libqtile.utils import QtileError

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

EVENT_TO_HANDLER = {
    xcffib.xproto.ButtonPressEvent: "handle_ButtonPress",
    xcffib.xproto.ButtonReleaseEvent: "handle_ButtonRelease",
    xcffib.xproto.ClientMessageEvent: "handle_ClientMessage",
    xcffib.xproto.ConfigureRequestEvent: "handle_ConfigureRequest",
    xcffib.xproto.DestroyNotifyEvent: "handle_DestroyNotify",
    xcffib.xproto.EnterNotifyEvent: "handle_EnterNotify",
    xcffib.xproto.ExposeEvent: "handle_Expose",
    xcffib.xproto.FocusOutEvent: "handle_FocusOut",
    xcffib.xproto.KeyPressEvent: "handle_KeyPress",
    xcffib.xproto.LeaveNotifyEvent: "handle_LeaveNotify",
    xcffib.xproto.MappingNotifyEvent: "handle_MappingNotify",
    xcffib.xproto.MapRequestEvent: "handle_MapRequest",
    xcffib.xproto.MotionNotifyEvent: "handle_MotionNotify",
    xcffib.xproto.PropertyNotifyEvent: "handle_PropertyNotify",
    xcffib.randr.ScreenChangeNotifyEvent: "handle_ScreenChangeNotify",
    xcffib.xproto.SelectionNotifyEvent: "handle_SelectionNotify",
    xcffib.xproto.UnmapNotifyEvent: "handle_UnmapNotify",
}

_IGNORED_EVENTS = {
    xcffib.xproto.CreateNotifyEvent,
    xcffib.xproto.FocusInEvent,
    xcffib.xproto.KeyReleaseEvent,
    # DWM handles this to help "broken focusing windows".
    xcffib.xproto.MapNotifyEvent,
    xcffib.xproto.NoExposureEvent,
    xcffib.xproto.ReparentNotifyEvent,
}


def get_keys() -> list[str]:
    return list(xcbq.keysyms.keys())


def get_modifiers() -> list[str]:
    return list(xcbq.ModMasks.keys())


class ExistingWMException(Exception):
    pass


class Core(base.Core):
    def __init__(self, display_name: str | None = None) -> None:
        """Setup the X11 core backend

        :param display_name:
            The display name to setup the X11 connection to.  Uses the DISPLAY
            environment variable if not given.
        """
        if display_name is None:
            display_name = os.environ.get("DISPLAY")
            if not display_name:
                raise QtileError("No DISPLAY set")

        self.conn = xcbq.Connection(display_name)
        self._display_name = display_name

        # Because we only do Xinerama multi-screening,
        # we can assume that the first
        # screen's root is _the_ root.
        self._root = self.conn.default_screen.root

        supporting_wm_wid = self._root.get_property(
            "_NET_SUPPORTING_WM_CHECK", "WINDOW", unpack=int
        )
        if len(supporting_wm_wid) > 0:
            supporting_wm_wid = supporting_wm_wid[0]

            supporting_wm = window.XWindow(self.conn, supporting_wm_wid)
            existing_wmname = supporting_wm.get_property(
                "_NET_WM_NAME", "UTF8_STRING", unpack=str
            )
            if existing_wmname:
                logger.error("not starting; existing window manager %s", existing_wmname)
                raise ExistingWMException(existing_wmname)

        self.eventmask = (
            EventMask.StructureNotify
            | EventMask.SubstructureNotify
            | EventMask.SubstructureRedirect
            | EventMask.EnterWindow
            | EventMask.LeaveWindow
            | EventMask.ButtonPress
        )
        self._root.set_attribute(eventmask=self.eventmask)

        self._root.set_property(
            "_NET_SUPPORTED", [self.conn.atoms[x] for x in xcbq.SUPPORTED_ATOMS]
        )

        self._wmname = "qtile"
        self._supporting_wm_check_window = self.conn.create_window(-1, -1, 1, 1)
        self._supporting_wm_check_window.set_property("_NET_WM_NAME", self._wmname)
        self._supporting_wm_check_window.set_property("_NET_WM_PID", os.getpid())
        self._supporting_wm_check_window.set_property(
            "_NET_SUPPORTING_WM_CHECK", self._supporting_wm_check_window.wid
        )
        self._root.set_property("_NET_SUPPORTING_WM_CHECK", self._supporting_wm_check_window.wid)

        self._selection = {
            "PRIMARY": {"owner": None, "selection": ""},
            "CLIPBOARD": {"owner": None, "selection": ""},
        }
        self._selection_window = self.conn.create_window(-1, -1, 1, 1)
        self._selection_window.set_attribute(eventmask=EventMask.PropertyChange)
        if hasattr(self.conn, "xfixes"):
            self.conn.xfixes.select_selection_input(self._selection_window, "PRIMARY")
            self.conn.xfixes.select_selection_input(self._selection_window, "CLIPBOARD")

        primary_atom = self.conn.atoms["PRIMARY"]
        reply = self.conn.conn.core.GetSelectionOwner(primary_atom).reply()
        self._selection["PRIMARY"]["owner"] = reply.owner

        clipboard_atom = self.conn.atoms["CLIPBOARD"]
        reply = self.conn.conn.core.GetSelectionOwner(primary_atom).reply()
        self._selection["CLIPBOARD"]["owner"] = reply.owner

        # ask for selection on start-up
        self.convert_selection(primary_atom)
        self.convert_selection(clipboard_atom)

        # setup the default cursor
        self._root.set_cursor("left_ptr")

        self._painter = None
        self._xtest = self.conn.conn(xcffib.xtest.key)

        numlock_code = self.conn.keysym_to_keycode(xcbq.keysyms["num_lock"])[0]
        self._numlock_mask = xcbq.ModMasks.get(self.conn.get_modifier(numlock_code), 0)
        self._valid_mask = ~(
            self._numlock_mask
            | xcbq.ModMasks["lock"]
            | xcbq.AllButtonsMask
            | xcbq.PointerMotionHintMask
        )

        # The last motion notify event that we still need to handle
        self._motion_notify: xcffib.Event | None = None
        # The last time we were handling a MotionNotify event
        self._last_motion_time = 0

        self.last_focused: base.Window | None = None

    @property
    def name(self):
        return "x11"

    def finalize(self) -> None:
        with contextlib.suppress(xcffib.ConnectionException):
            self.conn.conn.core.DeletePropertyChecked(
                self._root.wid,
                self.conn.atoms["_NET_SUPPORTING_WM_CHECK"],
            ).check()
        if hasattr(self, "qtile"):
            delattr(self, "qtile")
        self.conn.finalize()

    def get_screen_info(self) -> list[ScreenRect]:
        return self.conn.pseudoscreens

    @property
    def wmname(self):
        return self._wmname

    @wmname.setter
    def wmname(self, wmname):
        self._wmname = wmname
        self._supporting_wm_check_window.set_property("_NET_WM_NAME", wmname)

    def setup_listener(self) -> None:
        """Setup a listener for the given qtile instance

        :param qtile:
            The qtile instance to dispatch events to.
        :param eventloop:
            The eventloop to use to listen to the file descriptor.
        """
        logger.debug("Adding io watch")
        self.fd = self.conn.conn.get_file_descriptor()
        asyncio.get_running_loop().add_reader(self.fd, self._xpoll)

    def remove_listener(self) -> None:
        """Remove the listener from the given event loop"""
        if self.fd is not None:
            logger.debug("Removing io watch")
            loop = asyncio.get_running_loop()
            loop.remove_reader(self.fd)
            self.fd = None

    def on_config_load(self, initial) -> None:
        """Assign windows to groups"""
        assert self.qtile is not None

        # Ensure that properties are initialised at startup
        self.update_client_lists()

        self.conn.enable_screen_change_notifications()
        # previous to the enable_screen_change_notifications() refactoring,
        # we triggered a screen change notification on every boot,
        # regardless of whether the screen had actually changed. so, we do
        # that here, since we had tests that enforced that behavior so
        # maybe someone depended on it.
        hook.fire("screen_change", None)

        if not initial:
            # We are just reloading config
            managed_wins = [
                w for w in self.qtile.windows_map.values() if isinstance(w, window.Window)
            ]
            for managed_win in managed_wins:
                if managed_win.group and managed_win in managed_win.group.windows:
                    # Remove window from old group
                    managed_win.group.remove(managed_win)
                managed_win.set_group()
            return

        # Qtile just started - scan for clients
        for wid in self._root.query_tree():
            item = window.XWindow(self.conn, wid)
            try:
                attrs = item.get_attributes()
                state = item.get_wm_state()
                internal = item.get_property("QTILE_INTERNAL")
            except (xcffib.xproto.WindowError, xcffib.xproto.AccessError):
                continue

            if (
                attrs
                and attrs.map_state == xcffib.xproto.MapState.Unmapped
                or attrs.override_redirect
            ):
                continue
            if state and state[0] == window.WithdrawnState:
                item.unmap()
                continue

            if item.wid in self.qtile.windows_map:
                win = self.qtile.windows_map[item.wid]
                win.unhide()
                return

            if internal:
                win = window.Internal(item, self.qtile)
            else:
                win = window.Window(item, self.qtile)

                if item.get_wm_type() == "dock" or win.reserved_space:
                    assert self.qtile.current_screen is not None
                    win.static(self.qtile.current_screen.index)
                    continue

            self.qtile.manage(win)

            self.update_client_lists()
            win.change_layer()

    def warp_pointer(self, x, y):
        self._root.warp_pointer(x, y)
        self._root.set_input_focus()
        self._root.set_property("_NET_ACTIVE_WINDOW", self._root.wid)

    def convert_selection(self, selection_atom, _type="UTF8_STRING") -> None:
        type_atom = self.conn.atoms[_type]
        self.conn.conn.core.ConvertSelection(
            self._selection_window.wid,
            selection_atom,
            type_atom,
            selection_atom,
            xcffib.CurrentTime,
        )

    def handle_event(self, event):
        """Handle an X11 event by forwarding it to the right target"""
        targets = self._get_target_chain(event)
        logger.debug("X11 event: %s (targets: %s)", event.__class__.__name__, targets)
        for target in targets:
            ret = target(event)
            if not ret:
                break

    def _xpoll(self) -> None:
        """Poll the connection and dispatch incoming events"""
        assert self.qtile is not None

        while True:
            try:
                event = self.conn.conn.poll_for_event()
                if not event:
                    break

                if event.__class__ in _IGNORED_EVENTS:
                    continue

                # Motion Notifies are handled later
                # Otherwise this is too CPU intensive
                if isinstance(event, xcffib.xproto.MotionNotifyEvent):
                    self._motion_notify = event
                else:
                    # These events need the motion notify event handled first
                    handle_motion_first = type(event) in [
                        xcffib.xproto.EnterNotifyEvent,
                        xcffib.xproto.LeaveNotifyEvent,
                        xcffib.xproto.ButtonPressEvent,
                        xcffib.xproto.ButtonReleaseEvent,
                    ]
                    # Handle events in the correct order
                    if self._motion_notify and handle_motion_first:
                        self.handle_event(self._motion_notify)
                        self._motion_notify = None
                    self.handle_event(event)

            # Catch some bad X exceptions. Since X is event based, race
            # conditions can occur almost anywhere in the code. For example, if
            # a window is created and then immediately destroyed (before the
            # event handler is evoked), when the event handler tries to examine
            # the window properties, it will throw a WindowError exception. We
            # can essentially ignore it, since the window is already dead and
            # we've got another event in the queue notifying us to clean it up.
            except (
                xcffib.xproto.WindowError,
                xcffib.xproto.AccessError,
                xcffib.xproto.DrawableError,
                xcffib.xproto.GContextError,
                xcffib.xproto.PixmapError,
                xcffib.render.PictureError,
            ):
                pass
            except Exception:
                error_code = self.conn.conn.has_error()
                if error_code:
                    logger.warning("Shutting down due to disconnection from X server")
                    self.remove_listener()
                    self.qtile.stop()
                    return
                logger.exception("Got an exception in poll loop")
        # Handle any outstanding motion notify events
        if self._motion_notify:
            self.handle_event(self._motion_notify)
            self._motion_notify = None
        self.flush()

    def _get_target_chain(self, event) -> list[Callable]:
        """Returns a chain of targets that can handle this event

        Finds functions named `handle_X`, either on the window object itself or
        on the Qtile instance, where X is the event name (e.g.  EnterNotify,
        ConfigureNotify, etc).

        The event will be passed to each target in turn for handling, until one
        of the handlers returns False or None, or the end of the chain is
        reached.
        """
        assert self.qtile is not None

        handler = EVENT_TO_HANDLER.get(event.__class__)

        # If handler is None, this event has no handler and should be ignored
        if handler is None:
            return []

        # Certain events expose the affected window id as an "event" attribute.
        event_events = {
            xcffib.xproto.EnterNotifyEvent,
            xcffib.xproto.LeaveNotifyEvent,
            xcffib.xproto.MotionNotifyEvent,
            xcffib.xproto.ButtonPressEvent,
            xcffib.xproto.ButtonReleaseEvent,
            xcffib.xproto.KeyPressEvent,
        }
        if hasattr(event, "window"):
            window = self.qtile.windows_map.get(event.window)
        elif hasattr(event, "drawable"):
            window = self.qtile.windows_map.get(event.drawable)
        elif event.__class__ in event_events:
            window = self.qtile.windows_map.get(event.event)
        else:
            window = None

        chain = []
        if window is not None and hasattr(window, handler):
            chain.append(getattr(window, handler))

        if hasattr(self, handler):
            chain.append(getattr(self, handler))
        return chain

    def get_valid_timestamp(self):
        """Get a valid timestamp, i.e. not CurrentTime, for X server.

        It may be used in cases where CurrentTime is unacceptable for X server."""
        # do a zero length append to get the time offset as suggested by ICCCM
        # https://tronche.com/gui/x/icccm/sec-2.html#s-2.1
        # we do this on a separate connection since we can't receive events
        # without returning control to the event loop, which we can't do
        # because the event loop (via some window event) wants to know the
        # current time.
        conn = None
        try:
            conn = xcbq.Connection(self._display_name)
            conn.default_screen.root.set_attribute(eventmask=EventMask.PropertyChange)
            conn.conn.core.ChangePropertyChecked(
                xcffib.xproto.PropMode.Append,
                self._root.wid,
                self.conn.atoms["WM_CLASS"],
                self.conn.atoms["STRING"],
                8,
                0,
                "",
            ).check()
            while True:
                event = conn.conn.wait_for_event()
                if event.__class__ != xcffib.xproto.PropertyNotifyEvent:
                    continue
                return event.time
        finally:
            if conn is not None:
                conn.finalize()

    @property
    def display_name(self) -> str:
        """The name of the connected display"""
        return self._display_name

    def update_client_lists(self) -> None:
        """Updates the _NET_CLIENT_LIST and _NET_CLIENT_LIST_STACKING properties

        This is needed for third party tasklists and drag and drop of tabs in
        chrome
        """
        assert self.qtile
        # Regular top-level managed windows, i.e. excluding Static, Internal and Systray Icons
        wids = [wid for wid, c in self.qtile.windows_map.items() if isinstance(c, window.Window)]
        self._root.set_property("_NET_CLIENT_LIST", wids)

        # We rely on the stacking order from the X server
        stacked_wids = []
        for wid in self._root.query_tree():
            win = self.qtile.windows_map.get(wid)
            if not win:
                continue

            if isinstance(win, window.Window) and win.group:
                stacked_wids.append(wid)

        self._root.set_property("_NET_CLIENT_LIST_STACKING", stacked_wids)

    def update_desktops(self, groups, index: int) -> None:
        """Set the current desktops of the window manager

        The list of desktops is given by the list of groups, with the current
        desktop given by the index
        """
        self._root.set_property("_NET_NUMBER_OF_DESKTOPS", len(groups))
        self._root.set_property("_NET_DESKTOP_NAMES", "\0".join(i.name for i in groups))
        self._root.set_property("_NET_CURRENT_DESKTOP", index)
        viewport = []
        for group in groups:
            viewport += [group.screen.x, group.screen.y] if group.screen else [0, 0]
        self._root.set_property("_NET_DESKTOP_VIEWPORT", viewport)

    def lookup_key(self, key: config.Key | config.KeyChord) -> tuple[int, int]:
        """Find the keysym and the modifier mask for the given key"""
        if isinstance(key.key, str):
            keysym = xcbq.keysyms.get(key.key.lower())
            if not keysym:
                raise utils.QtileError(f"Unknown keysym: {key.key}")

        else:
            keysym = self.conn.code_to_syms[key.key][0]
            if not keysym:
                raise utils.QtileError(f"Unknown keycode: {key.key}")

        modmask = xcbq.translate_masks(key.modifiers)

        return keysym, modmask

    def grab_key(self, key: config.Key | config.KeyChord) -> tuple[int, int]:
        """Map the key to receive events on it"""
        keysym, modmask = self.lookup_key(key)
        codes = self.conn.keysym_to_keycode(keysym)

        for code in codes:
            if code == 0:
                logger.warning("Can't grab %s (unknown keysym: %02x)", key, keysym)
                continue
            for amask in self._auto_modmasks():
                self.conn.conn.core.GrabKey(
                    True,
                    self._root.wid,
                    modmask | amask,
                    code,
                    xcffib.xproto.GrabMode.Async,
                    xcffib.xproto.GrabMode.Async,
                )
        return keysym, modmask & self._valid_mask

    def ungrab_key(self, key: config.Key | config.KeyChord) -> tuple[int, int]:
        """Ungrab the key corresponding to the given keysym and modifier mask"""
        keysym, modmask = self.lookup_key(key)
        codes = self.conn.keysym_to_keycode(keysym)

        for code in codes:
            for amask in self._auto_modmasks():
                self.conn.conn.core.UngrabKey(code, self._root.wid, modmask | amask)

        return keysym, modmask & self._valid_mask

    def ungrab_keys(self) -> None:
        """Ungrab all of the key events"""
        self.conn.conn.core.UngrabKey(
            xcffib.xproto.Atom.Any, self._root.wid, xcffib.xproto.ModMask.Any
        )

    def grab_pointer(self) -> None:
        """Get the focus for pointer events"""
        self.conn.conn.core.GrabPointer(
            True,
            self._root.wid,
            xcbq.ButtonMotionMask | xcbq.AllButtonsMask | xcbq.ButtonReleaseMask,
            xcffib.xproto.GrabMode.Async,
            xcffib.xproto.GrabMode.Async,
            xcffib.xproto.Atom._None,
            xcffib.xproto.Atom._None,
            xcffib.xproto.Atom._None,
        )

    def ungrab_pointer(self) -> None:
        """Ungrab the focus for pointer events"""
        self.conn.conn.core.UngrabPointer(xcffib.xproto.Atom._None)

    def grab_button(self, mouse: config.Mouse) -> int:
        """Grab the given mouse button for events"""
        modmask = xcbq.translate_masks(mouse.modifiers)

        eventmask = EventMask.ButtonPress
        if isinstance(mouse, config.Drag):
            eventmask |= EventMask.ButtonRelease

        for amask in self._auto_modmasks():
            self.conn.conn.core.GrabButton(
                True,
                self._root.wid,
                eventmask,
                xcffib.xproto.GrabMode.Async,
                xcffib.xproto.GrabMode.Async,
                xcffib.xproto.Atom._None,
                xcffib.xproto.Atom._None,
                mouse.button_code,
                modmask | amask,
            )

        return modmask & self._valid_mask

    def ungrab_buttons(self) -> None:
        """Un-grab all mouse events"""
        self.conn.conn.core.UngrabButton(
            xcffib.xproto.Atom.Any, self._root.wid, xcffib.xproto.ModMask.Any
        )

    def _auto_modmasks(self) -> Iterator[int]:
        """The modifier masks to add"""
        yield 0
        yield xcbq.ModMasks["lock"]
        if self._numlock_mask:
            yield self._numlock_mask
            yield self._numlock_mask | xcbq.ModMasks["lock"]

    @contextlib.contextmanager
    def masked(self):
        for i in self.qtile.windows_map.values():
            i._disable_mask(EventMask.EnterWindow | EventMask.FocusChange | EventMask.LeaveWindow)
        yield
        for i in self.qtile.windows_map.values():
            i._reset_mask()

    def create_internal(
        self, x: int, y: int, width: int, height: int, desired_depth: int | None = 32
    ) -> base.Internal:
        assert self.qtile is not None

        win = self.conn.create_window(x, y, width, height, desired_depth)
        internal = window.Internal(win, self.qtile, desired_depth)
        internal.place(x, y, width, height, 0, None)
        self.qtile.manage(internal)
        return internal

    def handle_FocusOut(self, event) -> None:  # noqa: N802
        if event.detail == xcffib.xproto.NotifyDetail._None:
            self.conn.fixup_focus()

    def handle_SelectionNotify(self, event) -> None:  # noqa: N802
        if not getattr(event, "owner", None):
            return

        name = self.conn.atoms.get_name(event.selection)
        self._selection[name]["owner"] = event.owner
        self._selection[name]["selection"] = ""

        self.convert_selection(event.selection)

        hook.fire("selection_notify", name, self._selection[name])

    def handle_PropertyNotify(self, event) -> None:  # noqa: N802
        name = self.conn.atoms.get_name(event.atom)
        # it's the selection property
        if name in ("PRIMARY", "CLIPBOARD"):
            assert event.window == self._selection_window.wid
            prop = self._selection_window.get_property(event.atom, "UTF8_STRING")

            # If the selection property is None, it is unset, which means the
            # clipboard is empty.
            value = prop and prop.value.to_utf8() or ""

            self._selection[name]["selection"] = value
            hook.fire("selection_change", name, self._selection[name])

    def handle_ClientMessage(self, event) -> None:  # noqa: N802
        assert self.qtile is not None

        atoms = self.conn.atoms

        opcode = event.type
        data = event.data

        # handle change of desktop
        if atoms["_NET_CURRENT_DESKTOP"] == opcode:
            index = data.data32[0]
            try:
                self.qtile.groups[index].toscreen()
            except IndexError:
                logger.debug("Invalid desktop index: %s", index)

    def handle_KeyPress(self, event, *, simulated=False) -> None:  # noqa: N802
        assert self.qtile is not None
        keysym = self.conn.code_to_syms[event.detail][0]
        key, handled = self.qtile.process_key_event(keysym, event.state & self._valid_mask)

        if simulated:
            # Even though simulated keybindings could use a proper X11 event, we don't want do any fake input
            # This is because it needs extra code for e.g. pressing/releasing the modifiers
            # This we don't want to handle and instead leave to external tools such as xdotool
            return

        # As we're grabbing async we can't just replay it, so...
        # We need to forward the event to the focused window
        if not handled and key:
            # We need to ungrab the key as otherwise we get an event loop
            self.ungrab_key(key)
            # Modifier is pressed, just repeat the event with xtest
            self._fake_KeyPress(event)
            # Grab the key again
            self.grab_key(key)

    def handle_ButtonPress(self, event) -> None:  # noqa: N802
        assert self.qtile is not None

        button_code = event.detail
        state = event.state & self._valid_mask

        if not event.child:  # The client's handle_ButtonPress will focus it
            self.focus_by_click(event)

        self.qtile.process_button_click(button_code, state, event.event_x, event.event_y)
        self.conn.conn.core.AllowEvents(xcffib.xproto.Allow.ReplayPointer, event.time)

    def handle_ButtonRelease(self, event) -> None:  # noqa: N802
        assert self.qtile is not None

        button_code = event.detail
        state = event.state & self._valid_mask
        self.qtile.process_button_release(button_code, state)

    def handle_MotionNotify(self, event) -> None:  # noqa: N802
        assert self.qtile is not None

        # Limit the motion notify events from happening too frequently
        # As we already handle motion notify events "later", the default is None
        # So we also need to check if this has to be done in the first place
        resize_fps = self.qtile.current_screen.x11_drag_polling_rate
        if resize_fps is not None and (event.time - self._last_motion_time) <= (
            1000 / resize_fps
        ):
            return
        self._last_motion_time = event.time
        self.qtile.process_button_motion(event.event_x, event.event_y)

    def handle_ConfigureRequest(self, event):  # noqa: N802
        # It's not managed, or not mapped, so we just obey it.
        cw = xcffib.xproto.ConfigWindow
        args = {}
        if event.value_mask & cw.X:
            args["x"] = max(event.x, 0)
        if event.value_mask & cw.Y:
            args["y"] = max(event.y, 0)
        if event.value_mask & cw.Height:
            args["height"] = max(event.height, 0)
        if event.value_mask & cw.Width:
            args["width"] = max(event.width, 0)
        if event.value_mask & cw.BorderWidth:
            args["borderwidth"] = max(event.border_width, 0)
        w = window.XWindow(self.conn, event.window)
        w.configure(**args)

    def handle_MappingNotify(self, event):  # noqa: N802
        assert self.qtile is not None

        self.conn.refresh_keymap()
        if event.request == xcffib.xproto.Mapping.Keyboard:
            self.qtile.grab_keys()

    def handle_MapRequest(self, event) -> None:  # noqa: N802
        assert self.qtile is not None

        xwin = window.XWindow(self.conn, event.window)
        try:
            attrs = xwin.get_attributes()
            internal = xwin.get_property("QTILE_INTERNAL")
        except (xcffib.xproto.WindowError, xcffib.xproto.AccessError):
            return

        if attrs and attrs.override_redirect:
            return

        win = self.qtile.windows_map.get(xwin.wid)
        if win:
            if isinstance(win, window.Window) and win.group is self.qtile.current_group:
                win.unhide()
            return

        if internal:
            win = window.Internal(xwin, self.qtile)
            self.qtile.manage(win)
            win.unhide()
        else:
            win = window.Window(xwin, self.qtile)

            if xwin.get_wm_type() == "dock" or win.reserved_space:
                assert self.qtile.current_screen is not None
                win.static(self.qtile.current_screen.index)
                return

            self.qtile.manage(win)
            if not win.group or not win.group.screen:
                return
            win.unhide()
            self.update_client_lists()
            win.change_layer()

    def handle_DestroyNotify(self, event) -> None:  # noqa: N802
        assert self.qtile is not None

        self.qtile.unmanage(event.window)
        self.update_client_lists()
        if self.qtile.current_window is None:
            self.conn.fixup_focus()

    def handle_UnmapNotify(self, event) -> None:  # noqa: N802
        assert self.qtile is not None

        win = self.qtile.windows_map.get(event.window)

        if win and getattr(win, "group", None):
            try:
                win.hide()
                win.state = window.WithdrawnState  # type: ignore
            except xcffib.xproto.WindowError:
                # This means that the window has probably been destroyed,
                # but we haven't yet seen the DestroyNotify (it is likely
                # next in the queue). So, we just let these errors pass
                # since the window is dead.
                pass
            # Clear these atoms as per spec
            win.window.conn.conn.core.DeleteProperty(
                win.wid, win.window.conn.atoms["_NET_WM_STATE"]
            )
            win.window.conn.conn.core.DeleteProperty(
                win.wid, win.window.conn.atoms["_NET_WM_DESKTOP"]
            )
        self.qtile.unmanage(event.window)
        self.update_client_lists()
        if self.qtile.current_window is None:
            self.conn.fixup_focus()

    def handle_ScreenChangeNotify(self, event) -> None:  # noqa: N802
        hook.fire("screen_change", event)

    def _fake_input(self, input_type, detail, x=0, y=0) -> None:
        self._xtest.FakeInput(
            input_type,
            detail,
            0,  # This is a delay, not timestamp, according to AwesomeWM
            xcffib.XCB_NONE,
            x,  # x: Only used for motion events
            y,  # y: Only used for motion events
            0,
        )
        self.flush()

    def _fake_KeyPress(self, event) -> None:  # noqa: N802
        # First release the key as it is possibly already pressed
        for input_type in (
            xcbq.XCB_KEY_RELEASE,
            xcbq.XCB_KEY_PRESS,
            xcbq.XCB_KEY_RELEASE,
        ):
            self._fake_input(input_type, event.detail)

    @contextlib.contextmanager
    def disable_unmap_events(self):
        self._root.set_attribute(eventmask=self.eventmask & (~EventMask.SubstructureNotify))
        yield
        self._root.set_attribute(eventmask=self.eventmask)

    @property
    def painter(self):
        if self._painter is None:
            self._painter = xcbq.Painter(self._display_name)
        return self._painter

    def simulate_keypress(self, modifiers, key):
        """Simulates a keypress on the focused window."""
        modmasks = xcbq.translate_masks(modifiers)
        keysym = xcbq.keysyms.get(key.lower())

        class DummyEv:
            pass

        d = DummyEv()
        d.detail = self.conn.keysym_to_keycode(keysym)[0]
        d.state = modmasks
        self.handle_KeyPress(d, simulated=True)

    def focus_by_click(self, e, window=None):
        """Bring a window to the front

        Parameters
        ==========
        e: xcb event
            Click event used to determine window to focus
        """
        qtile = self.qtile
        assert qtile is not None

        if window:
            if qtile.config.bring_front_click and (
                qtile.config.bring_front_click != "floating_only"
                or getattr(window, "floating", False)
            ):
                window.bring_to_front()

            try:
                if window.group.screen is not qtile.current_screen:
                    qtile.focus_screen(window.group.screen.index, warp=False)
                qtile.current_group.focus(window, False)
                window.focus(False)
            except AttributeError:
                # probably clicked an internal window
                screen = qtile.find_screen(e.root_x, e.root_y)
                if screen:
                    qtile.focus_screen(screen.index, warp=False)

        else:
            # clicked on root window
            screen = qtile.find_screen(e.root_x, e.root_y)
            if screen:
                if qtile.current_window:
                    qtile.current_window._grab_click()
                qtile.focus_screen(screen.index, warp=False)

    def flush(self):
        self.conn.flush()

    def graceful_shutdown(self):
        """Try to close windows gracefully before exiting"""

        try:
            pids = []
            for win in self.qtile.windows_map.values():
                if not isinstance(win, base.Internal):
                    if pid := win.get_pid():
                        pids.append(pid)
        except xcffib.ConnectionException:
            logger.warning("Server disconnected, couldn't close windows gracefully.")
            return

        # Give the windows a chance to shut down nicely.
        for pid in pids:
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                # might have died recently
                pass

        def still_alive(pid):
            # most pids will not be children, so we can't use wait()
            try:
                os.kill(pid, 0)
                return True
            except OSError:
                return False

        # give everyone a little time to exit and write their state. but don't
        # sleep forever (1s).
        for i in range(10):
            pids = list(filter(still_alive, pids))
            if len(pids) == 0:
                break
            time.sleep(0.1)

    def get_mouse_position(self) -> tuple[int, int]:
        """
        Get mouse coordinates.
        """
        reply = self.conn.conn.core.QueryPointer(self._root.wid).reply()
        return reply.root_x, reply.root_y

    def keysym_from_name(self, name: str) -> int:
        """Get the keysym for a key from its name"""
        return keysyms[name.lower()]

    def check_stacking(self, win: base.Window) -> None:
        """Triggers restacking if a fullscreen window loses focus."""
        if win is self.last_focused:
            return

        if self.last_focused and self.last_focused.fullscreen:
            self.last_focused.change_layer()

        self.last_focused = win

    @property
    def hovered_window(self) -> base.WindowType | None:
        _hovered_window = self.conn.conn.core.QueryPointer(self._root.wid).reply().child
        return self.qtile.windows_map.get(_hovered_window)
