import asyncio
import os
from typing import Callable, Iterator, List, Optional, Tuple, TYPE_CHECKING

import xcffib
import xcffib.xproto

from . import base
from . import xcbq
from libqtile import config, utils, window
from libqtile.core.manager import Qtile
from libqtile.log_utils import logger
from libqtile.utils import QtileError

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

        wmname = "qtile"
        self._supporting_wm_check_window = self.conn.create_window(-1, -1, 1, 1)
        self._supporting_wm_check_window.set_property("_NET_WM_NAME", wmname)
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

        self.qtile = None  # type: Optional[Qtile]

        numlock_code = self.conn.keysym_to_keycode(xcbq.keysyms["Num_Lock"])
        self._numlock_mask = xcbq.ModMasks.get(self.conn.get_modifier(numlock_code), 0)
        self._valid_mask = ~(self._numlock_mask | xcbq.ModMasks["lock"])

    @property
    def masks(self) -> Tuple[int, int]:
        return self._numlock_mask, self._valid_mask

    def setup_listener(
        self, qtile: Qtile, eventloop: asyncio.AbstractEventLoop
    ) -> None:
        """Setup a listener for the given qtile instance

        :param qtile:
            The qtile instance to dispatch events to.
        :param eventloop:
            The eventloop to use to listen to the file descriptor.
        """
        logger.debug("Adding io watch")
        self.qtile = qtile
        fd = self.conn.conn.get_file_descriptor()
        eventloop.add_reader(fd, self._xpoll)

    def remove_listener(self, eventloop: asyncio.AbstractEventLoop) -> None:
        """Remove the listener from the given event loop

        :param eventloop:
            The eventloop that had been setup for listening.
        """
        logger.debug("Removing io watch")
        fd = self.conn.conn.get_file_descriptor()
        eventloop.remove_reader(fd)
        self.qtile = None
        self.conn.finalize()

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

        chain = []
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

        if window is not None and hasattr(window, handler):
            chain.append(getattr(window, handler))

        if hasattr(self.qtile, handler):
            chain.append(getattr(self.qtile, handler))

        if not chain:
            logger.info("Unhandled event: {event_type}".format(event_type=event_type))
        return chain

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

    def grab_key(self, keysym: int, modmask: int) -> None:
        """Map the key to receive events on it"""
        code = self.conn.keysym_to_keycode(keysym)
        for amask in self._auto_modmasks():
            self._root.grab_key(
                code,
                modmask | amask,
                True,
                xcffib.xproto.GrabMode.Async,
                xcffib.xproto.GrabMode.Async,
            )

    def ungrab_keys(self) -> None:
        """Ungrab all of the key events"""
        self._root.ungrab_key(None, None)

    def ungrab_key(
        self, keysym: int, modmask: int
    ) -> None:
        """Ungrab the key corresponding to the given keysym and modifier mask"""
        code = self.conn.keysym_to_keycode(keysym)

        for amask in self._auto_modmasks():
            self._root.ungrab_key(code, modmask | amask)

    def grab_pointer(self) -> None:
        """Get the focus for pointer events"""
        self._root.grab_pointer(
            True,
            xcbq.ButtonMotionMask | xcbq.AllButtonsMask | xcbq.ButtonReleaseMask,
            xcffib.xproto.GrabMode.Async,
            xcffib.xproto.GrabMode.Async,
        )

    def ungrab_pointer(self) -> None:
        """Ungrab the focus for pointer events"""
        self._root.ungrab_pointer()

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
            self._root.grab_button(
                mouse.button_code,
                modmask | amask,
                True,
                eventmask,
                grabmode,
                xcffib.xproto.GrabMode.Async,
            )

    def ungrab_buttons(self) -> None:
        """Un-grab all mouse events"""
        self._root.ungrab_button(None, None)

    def _auto_modmasks(self) -> Iterator[int]:
        """The modifier masks to add"""
        yield 0
        yield xcbq.ModMasks["lock"]
        if self._numlock_mask:
            yield self._numlock_mask
            yield self._numlock_mask | xcbq.ModMasks["lock"]
