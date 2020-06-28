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

import asyncio
import os
from collections import OrderedDict
from typing import TYPE_CHECKING, Callable, Iterator, List, Optional, Tuple

import xcffib
import xcffib.render
import xcffib.xproto

from libqtile import config, hook, utils, window
from libqtile.backend import base
from libqtile.backend.x11 import xcbq
from libqtile.log_utils import logger
from libqtile.utils import QtileError

if TYPE_CHECKING:
    from typing import Dict
    from libqtile.core.manager import Qtile

_IGNORED_EVENTS = {
    xcffib.xproto.CreateNotifyEvent,
    xcffib.xproto.FocusInEvent,
    xcffib.xproto.FocusOutEvent,
    xcffib.xproto.KeyReleaseEvent,
    xcffib.xproto.LeaveNotifyEvent,
    # DWM handles this to help "broken focusing windows".
    xcffib.xproto.MapNotifyEvent,
    xcffib.xproto.NoExposureEvent,
    xcffib.xproto.ReparentNotifyEvent,
}


class XCore(base.Core):
    def __init__(self, display_name: str = None) -> None:
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
        self._fd = None  # type: Optional[int]

        # Because we only do Xinerama multi-screening,
        # we can assume that the first
        # screen's root is _the_ root.
        self._root = self.conn.default_screen.root
        self._root.set_attribute(
            eventmask=(
                xcffib.xproto.EventMask.StructureNotify
                | xcffib.xproto.EventMask.SubstructureNotify
                | xcffib.xproto.EventMask.SubstructureRedirect
                | xcffib.xproto.EventMask.EnterWindow
                | xcffib.xproto.EventMask.LeaveWindow
            )
        )

        self._root.set_property(
            "_NET_SUPPORTED", [self.conn.atoms[x] for x in xcbq.SUPPORTED_ATOMS]
        )

        self._wmname = "qtile"
        self._supporting_wm_check_window = self.conn.create_window(-1, -1, 1, 1)
        self._supporting_wm_check_window.set_property("_NET_WM_NAME", self._wmname)
        self._supporting_wm_check_window.set_property(
            "_NET_SUPPORTING_WM_CHECK", self._supporting_wm_check_window.wid
        )
        self._root.set_property(
            "_NET_SUPPORTING_WM_CHECK", self._supporting_wm_check_window.wid
        )

        self._selection = {
            "PRIMARY": {"owner": None, "selection": ""},
            "CLIPBOARD": {"owner": None, "selection": ""},
        }
        self._selection_window = self.conn.create_window(-1, -1, 1, 1)
        self._selection_window.set_attribute(
            eventmask=xcffib.xproto.EventMask.PropertyChange
        )
        if hasattr(self.conn, "xfixes"):
            self.conn.xfixes.select_selection_input(self._selection_window, "PRIMARY")  # type: ignore
            self.conn.xfixes.select_selection_input(self._selection_window, "CLIPBOARD")  # type: ignore

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

        self.qtile = None  # type: Optional[Qtile]
        self._painter = None

        numlock_code = self.conn.keysym_to_keycode(xcbq.keysyms["Num_Lock"])
        self._numlock_mask = xcbq.ModMasks.get(self.conn.get_modifier(numlock_code), 0)
        self._valid_mask = ~(self._numlock_mask | xcbq.ModMasks["lock"])

    def get_screen_info(self) -> List[Tuple[int, int, int, int]]:
        """Get the screen information for the current connection"""
        # What's going on here is a little funny. What we really want is only
        # screens that don't overlap here; overlapping screens should see the
        # same parts of the root window (i.e. for people doing xrandr
        # --same-as). However, the order that X gives us pseudo screens in is
        # important, because it indicates what people have chosen via xrandr
        # --primary or whatever. So we need to alias screens that should be
        # aliased, but preserve order as well. See #383.
        xywh = OrderedDict()  # type: Dict[Tuple[int, int], Tuple[int, int]]
        for screen in self.conn.pseudoscreens:
            pos = (screen.x, screen.y)
            width, height = xywh.get(pos, (0, 0))
            xywh[pos] = (max(width, screen.width), max(height, screen.height))

        if len(xywh) == 0:
            xywh[(0, 0)] = (
                self.conn.default_screen.width_in_pixels,
                self.conn.default_screen.height_in_pixels,
            )

        return [(x, y, w, h) for (x, y), (w, h) in xywh.items()]

    @property
    def wmname(self):
        return self._wmname

    @wmname.setter
    def wmname(self, wmname):
        self._wmname = wmname
        self._supporting_wm_check_window.set_property("_NET_WM_NAME", wmname)

    @property
    def masks(self) -> Tuple[int, int]:
        return self._numlock_mask, self._valid_mask

    def setup_listener(
        self, qtile: "Qtile", eventloop: asyncio.AbstractEventLoop
    ) -> None:
        """Setup a listener for the given qtile instance

        :param qtile:
            The qtile instance to dispatch events to.
        :param eventloop:
            The eventloop to use to listen to the file descriptor.
        """
        logger.debug("Adding io watch")
        self.qtile = qtile
        self.fd = self.conn.conn.get_file_descriptor()
        eventloop.add_reader(self.fd, self._xpoll)

    def remove_listener(self) -> None:
        """Remove the listener from the given event loop"""
        self._remove_listener()
        self.qtile = None
        self.conn.finalize()

    def _remove_listener(self) -> None:
        if self.fd is not None:
            logger.debug("Removing io watch")
            loop = asyncio.get_event_loop()
            loop.remove_reader(self.fd)
            self.fd = None

    def scan(self) -> None:
        """Scan for existing windows"""
        assert self.qtile is not None

        _, _, children = self._root.query_tree()
        for item in children:
            try:
                attrs = item.get_attributes()
                state = item.get_wm_state()
            except (xcffib.xproto.WindowError, xcffib.xproto.AccessError):
                continue

            if attrs and attrs.map_state == xcffib.xproto.MapState.Unmapped:
                continue
            if state and state[0] == window.WithdrawnState:
                continue
            self.qtile.manage(item)

    def convert_selection(self, selection_atom, _type="UTF8_STRING") -> None:
        type_atom = self.conn.atoms[_type]
        self.conn.conn.core.ConvertSelection(
            self._selection_window.wid,
            selection_atom,
            type_atom,
            selection_atom,
            xcffib.CurrentTime,
        )

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

                event_type = event.__class__.__name__
                if event_type.endswith("Event"):
                    event_type = event_type[:-5]

                logger.debug(event_type)

                for target in self._get_target_chain(event_type, event):
                    logger.debug("Handling: {event_type}".format(event_type=event_type))
                    ret = target(event)
                    if not ret:
                        break

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
                    error_string = xcbq.XCB_CONN_ERRORS[error_code]
                    logger.exception(
                        "Shutting down due to X connection error {error_string} ({error_code})".format(
                            error_string=error_string, error_code=error_code
                        )
                    )
                    self._remove_listener()
                    self.qtile.stop()
                    return
                logger.exception("Got an exception in poll loop")
        self.conn.flush()

    def _get_target_chain(self, event_type: str, event) -> List[Callable]:
        """Returns a chain of targets that can handle this event

        Finds functions named `handle_X`, either on the window object itself or
        on the Qtile instance, where X is the event name (e.g.  EnterNotify,
        ConfigureNotify, etc).

        The event will be passed to each target in turn for handling, until one
        of the handlers returns False or None, or the end of the chain is
        reached.
        """
        assert self.qtile is not None

        handler = "handle_{event_type}".format(event_type=event_type)
        # Certain events expose the affected window id as an "event" attribute.
        event_events = [
            "EnterNotify",
            "ButtonPress",
            "ButtonRelease",
            "KeyPress",
        ]
        if hasattr(event, "window"):
            window = self.qtile.windows_map.get(event.window)
        elif hasattr(event, "drawable"):
            window = self.qtile.windows_map.get(event.drawable)
        elif event_type in event_events:
            window = self.qtile.windows_map.get(event.event)
        else:
            window = None

        chain = []
        if window is not None and hasattr(window, handler):
            chain.append(getattr(window, handler))

        if hasattr(self, handler):
            chain.append(getattr(self, handler))

        if not chain:
            logger.info("Unhandled event: {event_type}".format(event_type=event_type))
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
            conn.default_screen.root.set_attribute(
                eventmask=xcffib.xproto.EventMask.PropertyChange
            )
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

    def get_keys(self) -> List[str]:
        return list(xcbq.keysyms.keys())

    def get_modifiers(self) -> List[str]:
        return list(xcbq.ModMasks.keys())

    def update_client_list(self, windows) -> None:
        """Set the current clients to the given list of windows"""
        self._root.set_property("_NET_CLIENT_LIST", windows)
        # TODO: check stack order
        self._root.set_property("_NET_CLIENT_LIST_STACKING", windows)

    def update_net_desktops(self, groups, index: int) -> None:
        """Set the current desktops of the window manager

        The list of desktops is given by the list of groups, with the current
        desktop given by the index
        """
        self._root.set_property("_NET_NUMBER_OF_DESKTOPS", len(groups))
        self._root.set_property("_NET_DESKTOP_NAMES", "\0".join(i.name for i in groups))
        self._root.set_property("_NET_CURRENT_DESKTOP", index)

    def lookup_key(self, key: config.Key) -> Tuple[int, int]:
        """Find the keysym and the modifier mask for the given key"""
        try:
            keysym = xcbq.get_keysym(key.key)
            modmask = xcbq.translate_masks(key.modifiers)
        except xcbq.XCBQError as err:
            raise utils.QtileError(err)

        return keysym, modmask

    def grab_key(self, key: config.Key) -> Tuple[int, int]:
        """Map the key to receive events on it"""
        keysym, modmask = self.lookup_key(key)
        code = self.conn.keysym_to_keycode(keysym)

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

    def ungrab_key(self, key: config.Key) -> Tuple[int, int]:
        """Ungrab the key corresponding to the given keysym and modifier mask"""
        keysym, modmask = self.lookup_key(key)
        code = self.conn.keysym_to_keycode(keysym)

        for amask in self._auto_modmasks():
            self.conn.conn.core.UngrabKey(code, self._root.wid, modmask | amask)

        return keysym, modmask & self._valid_mask

    def ungrab_keys(self) -> None:
        """Ungrab all of the key events"""
        self.conn.conn.core.UngrabKey(xcffib.xproto.Atom.Any, self._root.wid, xcffib.xproto.ModMask.Any)

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

    def grab_button(self, mouse: config.Mouse) -> None:
        """Grab the given mouse button for events"""
        try:
            modmask = xcbq.translate_masks(mouse.modifiers)
        except xcbq.XCBQError as err:
            raise utils.QtileError(err)

        if isinstance(mouse, config.Click) and mouse.focus:
            # Make a freezing grab on mouse button to gain focus
            # Event will propagate to target window
            grabmode = xcffib.xproto.GrabMode.Sync
        else:
            grabmode = xcffib.xproto.GrabMode.Async

        eventmask = xcffib.xproto.EventMask.ButtonPress
        if isinstance(mouse, config.Drag):
            eventmask |= xcffib.xproto.EventMask.ButtonRelease

        for amask in self._auto_modmasks():
            self.conn.conn.core.GrabButton(
                True,
                self._root.wid,
                eventmask,
                grabmode,
                xcffib.xproto.GrabMode.Async,
                xcffib.xproto.Atom._None,
                xcffib.xproto.Atom._None,
                mouse.button_code,
                modmask | amask,
            )

    def ungrab_buttons(self) -> None:
        """Un-grab all mouse events"""
        self.conn.conn.core.UngrabButton(xcffib.xproto.Atom.Any, self._root.wid, xcffib.xproto.ModMask.Any)

    def _auto_modmasks(self) -> Iterator[int]:
        """The modifier masks to add"""
        yield 0
        yield xcbq.ModMasks["lock"]
        if self._numlock_mask:
            yield self._numlock_mask
            yield self._numlock_mask | xcbq.ModMasks["lock"]

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

    def handle_EnterNotify(self, event) -> Optional[bool]:  # noqa: N802
        assert self.qtile is not None

        return self.qtile.enter_event(event)

    def handle_ClientMessage(self, event) -> None:  # noqa: N802
        assert self.qtile is not None

        atoms = self.conn.atoms

        opcode = event.type
        data = event.data

        # handle change of desktop
        if atoms["_NET_CURRENT_DESKTOP"] == opcode:
            index = data.data32[0]
            try:
                self.qtile.cmd_to_layout_index(index)
            except IndexError:
                logger.info("Invalid Desktop Index: %s" % index)

    def handle_KeyPress(self, event) -> None:  # noqa: N802
        assert self.qtile is not None

        keysym = self.conn.code_to_syms[event.detail][0]
        self.qtile.process_key_event(keysym, event.state & self._valid_mask)

    def handle_ButtonPress(self, event) -> None:  # noqa: N802
        assert self.qtile is not None

        self.mouse_position = (event.event_x, event.event_y)
        button_code = event.detail
        state = event.state
        state |= self._numlock_mask
        state &= self._valid_mask
        self.qtile.process_button_click(
            button_code, state, event.event_x, event.event_y, event
        )

    def handle_ButtonRelease(self, event) -> None:  # noqa: N802
        assert self.qtile is not None

        button_code = event.detail
        self.qtile.process_button_release(button_code)

    def handle_MotionNotify(self, event) -> None:  # noqa: N802
        assert self.qtile is not None

        self.qtile.process_button_motion(event.event_x, event.event_y)

    def handle_ConfigureNotify(self, event) -> None:  # noqa: N802
        """Handle xrandr events"""
        assert self.qtile is not None

        if event.window == self._root.wid:
            self.qtile.process_configure(event.width, event.height)

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
        w = xcbq.Window(self.conn, event.window)
        w.configure(**args)

    def handle_MappingNotify(self, event):  # noqa: N802
        assert self.qtile is not None

        self.conn.refresh_keymap()
        if event.request == xcffib.xproto.Mapping.Keyboard:
            self.qtile.grab_keys()

    def handle_MapRequest(self, event) -> None:  # noqa: N802
        assert self.qtile is not None

        window = xcbq.Window(self.conn, event.window)
        self.qtile.map_window(window)

    def handle_DestroyNotify(self, event) -> None:  # noqa: N802
        assert self.qtile is not None

        self.qtile.unmanage(event.window)

    def handle_UnmapNotify(self, event) -> None:  # noqa: N802
        assert self.qtile is not None

        if event.event != self._root.wid:
            self.qtile.unmap_window(event.window)

    def handle_ScreenChangeNotify(self, event) -> None:  # noqa: N802
        hook.fire("screen_change", self.qtile, event)

    @property
    def painter(self):
        if self._painter is None:
            self._painter = xcbq.Painter(self._display_name)
        return self._painter
