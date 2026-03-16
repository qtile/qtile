from __future__ import annotations

import typing

from libqtile import config
from libqtile.backend import base
from libqtile.log_utils import logger

if typing.TYPE_CHECKING:
    from libqtile.backend.macos.window import Window
    from libqtile.command.base import ItemT
    from libqtile.config import Mouse, Output
    from libqtile.core.manager import Qtile


class Core(base.Core):
    def __init__(self) -> None:
        from libqtile.backend.macos import _ffi  # type: ignore

        self._ffi = _ffi.ffi
        self._lib = _ffi.lib
        self._callback_handle = None
        self._observer_handle = None
        self._poll_handle: typing.Any = None
        self._running = False
        self._ax_trusted: bool | None = None
        self.qtile: Qtile = None  # type: ignore
        self.windows: dict[int, Window] = {}
        self.grabbed_buttons: set[tuple[int, int]] = set()

        from libqtile.backend.macos.idle import IdleNotifier
        from libqtile.backend.macos.idle_inhibit import IdleInhibitorManager
        from libqtile.backend.macos.inputs import InputManager

        self.idle_inhibitor_manager = IdleInhibitorManager(self)
        self.idle_notifier = IdleNotifier(self)
        self.input_manager: InputManager | None = None

        # macOS renders to native windows via AX; qtile's painter abstraction is unused.
        self.painter = None

    @property
    def name(self) -> str:
        return "macos"

    @property
    def display_name(self) -> str:
        return "macOS"

    def set_qtile(self, qtile: Qtile) -> None:
        from libqtile.backend.macos.inputs import InputManager

        self.qtile = qtile
        if self.input_manager is None:
            self.input_manager = InputManager(qtile, self)
        # Start polling CFRunLoop for AX notifications and EventTap
        self._running = True
        self._poll_handle = self.qtile.call_later(0.01, self._poll_cf)

    def _poll_cf(self) -> None:
        if not self._running:
            return

        try:
            self._lib.mac_poll_runloop()
        except Exception:
            logger.exception("mac_poll_runloop failed")
        finally:
            if self._running and self.qtile:
                self._poll_handle = self.qtile.call_later(0.01, self._poll_cf)

    def _check_ax_trust(self) -> bool:
        """Return True if AX trust is granted, log a warning if not.

        The result is cached after the first successful check so that
        repeated calls (e.g. from list_windows()) do not re-load the
        ApplicationServices framework on every invocation.
        """
        if self._ax_trusted is not None:
            return self._ax_trusted
        try:
            import ctypes
            import ctypes.util

            app_services = ctypes.cdll.LoadLibrary(
                ctypes.util.find_library("ApplicationServices") or "ApplicationServices"
            )
            ax_is_trusted = app_services.AXIsProcessTrusted
            ax_is_trusted.restype = ctypes.c_bool
            if not ax_is_trusted():
                logger.warning(
                    "Accessibility trust not granted — window management will not work. "
                    "Open System Settings > Privacy & Security > Accessibility and add qtile."
                )
                self._ax_trusted = False
                return False
        except Exception:
            logger.warning(
                "Could not verify Accessibility trust — ensure qtile has Accessibility "
                "permission in System Settings > Privacy & Security > Accessibility."
            )
            self._ax_trusted = False
            return False
        self._ax_trusted = True
        return True

    def on_config_load(self, initial: bool) -> None:
        if self.qtile:
            self.idle_notifier.start()
        if initial and self.qtile:
            self._check_ax_trust()
            for win in self.list_windows():
                if win.wid not in self.windows:
                    self.windows[win.wid] = win
                    self.qtile.manage(win)

    def _items(self, name: str) -> ItemT:
        if name == "window":
            return True, list(self.windows.keys())
        return None

    def _select(self, name, sel):
        if name == "window":
            if sel is None:
                return self.qtile.current_window
            else:
                return self.windows.get(sel)
        return None

    def finalize(self) -> None:
        self._running = False
        if self._poll_handle:
            self._poll_handle.cancel()
            self._poll_handle = None

        self.idle_notifier.clear_timers()

        if self.input_manager:
            self.input_manager.ungrab_keys()
        self.ungrab_buttons()
        self.windows.clear()

        self._lib.mac_observer_stop()
        self._lib.mac_event_tap_stop()
        self.qtile = None  # type: ignore

    def _translate_mask(self, modifiers: list[str]) -> int:
        mask = 0
        for mod in modifiers:
            m = mod.lower()
            if m == "shift":
                mask |= 1
            elif m == "control":
                mask |= 4
            elif m in ("mod1", "alt", "option"):
                mask |= 8
            elif m in ("mod4", "command", "meta", "super"):
                mask |= 64
            elif m in ("mod2", "num_lock"):
                # NumLock — macOS flag kCGEventFlagMaskNumericPad = 0x200000; use X11 mod2 bit
                mask |= 16
            elif m in ("hyper",):
                # No direct macOS equivalent; alias to Command (mod4) as closest super-key
                mask |= 64
            # mod3, mod5 have no macOS hardware equivalent; silently ignore to avoid mis-bindings
        return mask

    def setup_listener(self) -> None:
        # TODO(0040): Register NSApplicationDidChangeScreenParametersNotification
        # (or CGDisplayRegisterReconfigurationCallback) here to handle monitor
        # hotplug events and call self.qtile.reconfigure_screens() accordingly.
        if not getattr(self, "_callback_handle", None):

            @self._ffi.callback("event_tap_cb")
            def _event_tap_callback(type, flags, keycode, userdata):
                # Use getattr to avoid Mypy thinking self.qtile is always truthy
                qtile = getattr(self, "qtile", None)
                if not qtile:
                    return 0

                # Map macOS flags to Qtile mask
                mask = 0
                if flags & 0x20000:
                    mask |= 1  # Shift
                if flags & 0x40000:
                    mask |= 4  # Control
                if flags & 0x80000:
                    mask |= 8  # Option/Mod1
                if flags & 0x100000:
                    mask |= 64  # Command/Mod4

                # type 10: kCGEventKeyDown
                if type == 10:
                    if self.input_manager and self.input_manager.process_key_event(
                        mask, int(keycode)
                    ):
                        return 1  # Swallow

                # type 11: kCGEventKeyUp
                elif type == 11:
                    if self.input_manager:
                        self.input_manager.process_key_release(mask, int(keycode))

                # type 12: kCGEventFlagsChanged — modifier key pressed or released
                elif type == 12:
                    if self.input_manager and self.input_manager.process_key_event(
                        mask, int(keycode)
                    ):
                        return 1  # Swallow

                # type 1: kCGEventLeftMouseDown, 3: kCGEventRightMouseDown, 25: kCGEventOtherMouseDown
                elif type in (1, 3, 25):
                    button = 1 if type == 1 else (3 if type == 3 else 2)
                    x, y = self.get_mouse_position()

                    # Check if it's an internal window
                    for win in qtile.windows_map.values():
                        if isinstance(win, base.Internal):
                            if win.x <= x < win.x + win.width and win.y <= y < win.y + win.height:
                                qtile.call_soon_threadsafe(
                                    win.process_button_click, x - win.x, y - win.y, button
                                )
                                return 1  # Swallow for internal

                    if (button, mask) in self.grabbed_buttons:
                        qtile.call_soon_threadsafe(qtile.process_button_click, button, mask, x, y)
                        return 1  # Swallow

                # type 2: LeftMouseUp, 4: RightMouseUp, 26: OtherMouseUp
                elif type in (2, 4, 26):
                    button = 1 if type == 2 else (3 if type == 4 else 2)
                    x, y = self.get_mouse_position()
                    for win in qtile.windows_map.values():
                        if isinstance(win, base.Internal):
                            if win.x <= x < win.x + win.width and win.y <= y < win.y + win.height:
                                qtile.call_soon_threadsafe(
                                    win.process_button_release, x - win.x, y - win.y, button
                                )
                                return 1
                    # Don't swallow release events for non-internal windows.
                    return 0

                # type 5: MouseMoved, 6: LeftMouseDragged, 7: RightMouseDragged
                elif type in (5, 6, 7):
                    x, y = self.get_mouse_position()
                    for win in qtile.windows_map.values():
                        if isinstance(win, base.Internal):
                            if win.x <= x < win.x + win.width and win.y <= y < win.y + win.height:
                                qtile.call_soon_threadsafe(
                                    win.process_pointer_motion, x - win.x, y - win.y
                                )
                                break
                    return 0  # Never swallow motion events.

                # type 22: kCGEventScrollWheel
                # keycode encodes: vertical axis uses buttons 4/5, horizontal uses 6/7.
                # The native layer packs both axes: upper 16 bits = horizontal button (6/7 or 0),
                # lower 16 bits = vertical button (4/5 or 0).
                elif type == 22:
                    raw = int(keycode)
                    vertical_button = raw & 0xFFFF
                    horizontal_button = (raw >> 16) & 0xFFFF
                    x, y = self.get_mouse_position()
                    swallow = 0
                    if vertical_button and (vertical_button, mask) in self.grabbed_buttons:
                        qtile.call_soon_threadsafe(
                            qtile.process_button_click, vertical_button, mask, x, y
                        )
                        swallow = 1
                    if horizontal_button and (horizontal_button, mask) in self.grabbed_buttons:
                        qtile.call_soon_threadsafe(
                            qtile.process_button_click, horizontal_button, mask, x, y
                        )
                        swallow = 1
                    if swallow:
                        return 1

                return 0

            self._callback_handle = _event_tap_callback
            if self._lib.mac_event_tap_start(self._callback_handle, self._ffi.NULL):
                logger.error(
                    "Failed to create CGEventTap — check Accessibility permissions in System Settings"
                )

            @self._ffi.callback("ax_observer_cb")
            def _observer_callback(win_ptr, notification_ptr, userdata):
                notification = self._ffi.string(notification_ptr).decode()
                from libqtile.backend.macos.window import Window

                # Filter out non-window elements
                if not self._lib.mac_is_window(win_ptr):
                    return

                wid = int(self._ffi.cast("uintptr_t", win_ptr))

                qtile = getattr(self, "qtile", None)
                if qtile:
                    if notification == "AXWindowCreated":

                        def manage_new():
                            if wid not in self.windows:
                                w_struct = self._ffi.new("struct mac_window *")
                                w_struct.ptr = win_ptr
                                w_struct.wid = wid
                                self._lib.mac_window_retain(w_struct)
                                win = Window(qtile, w_struct)
                                self.windows[wid] = win
                                qtile.manage(win)

                        qtile.call_soon_threadsafe(manage_new)
                    elif notification == "AXUIElementDestroyed":

                        def unmanage():
                            if wid in self.windows:
                                self.windows.pop(wid)
                                qtile.unmanage(wid)

                        qtile.call_soon_threadsafe(unmanage)

                    elif notification == "AXFocusedWindowChanged":

                        def sync_focus():
                            win = self.windows.get(wid)
                            if win and qtile.current_window is not win:
                                qtile.current_group.focus(win, warp=False)

                        qtile.call_soon_threadsafe(sync_focus)

                    elif notification in ("AXWindowMoved", "AXWindowResized"):

                        def sync_geometry():
                            win = self.windows.get(wid)
                            if win:
                                win._x, win._y = win.get_position()
                                win._width, win._height = win.get_size()

                        qtile.call_soon_threadsafe(sync_geometry)

                    elif notification == "AXTitleChanged":

                        def sync_title():
                            win = self.windows.get(wid)
                            if win:
                                name_ptr = self._lib.mac_window_get_name(win._win)
                                if name_ptr != self._ffi.NULL:
                                    win.name = self._ffi.string(name_ptr).decode()
                                    self._lib.free(name_ptr)

                        qtile.call_soon_threadsafe(sync_title)

            self._observer_handle = _observer_callback
            if self._lib.mac_observer_start(self._observer_handle, self._ffi.NULL):
                logger.error(
                    "Failed to start AX observer — check Accessibility permissions in System Settings"
                )

    def remove_listener(self) -> None:
        self._lib.mac_event_tap_stop()
        self._lib.mac_observer_stop()
        self._callback_handle = None
        self._observer_handle = None

    def get_output_info(self) -> list[Output]:
        outputs_ptr = self._ffi.new("struct mac_output **")
        count_ptr = self._ffi.new("size_t *")

        self._lib.mac_get_outputs(outputs_ptr, count_ptr)

        outputs = outputs_ptr[0]
        count = count_ptr[0]

        res = []
        from libqtile.config import Output as CoreOutput

        for i in range(count):
            o = outputs[i]
            from libqtile.config import ScreenRect

            res.append(
                CoreOutput(
                    port=self._ffi.string(o.name).decode()
                    if o.name != self._ffi.NULL
                    else "Unknown",
                    make=None,
                    model=None,
                    serial=None,
                    rect=ScreenRect(o.x, o.y, o.width, o.height),
                )
            )

        self._lib.mac_free_outputs(outputs, count)
        return res

    def list_windows(self) -> list[Window]:
        from libqtile.backend.macos.window import Window

        if not self._check_ax_trust():
            return []

        windows_ptr = self._ffi.new("struct mac_window **")
        count_ptr = self._ffi.new("size_t *")

        if self._lib.mac_get_windows(windows_ptr, count_ptr):
            return []

        windows = windows_ptr[0]
        count = count_ptr[0]

        res = []
        for i in range(count):
            w_struct = self._ffi.new("struct mac_window *")
            w_struct.ptr = windows[i].ptr
            w_struct.wid = windows[i].wid
            self._lib.mac_window_retain(w_struct)
            res.append(Window(self.qtile, w_struct))

        self._lib.mac_free_windows(windows, count)
        return res

    def grab_key(self, key: config.Key | config.KeyChord) -> tuple[int, int]:
        if not self.input_manager:
            return 0, 0
        return self.input_manager.grab_key(key)

    def ungrab_key(self, key: config.Key | config.KeyChord) -> tuple[int, int]:
        if not self.input_manager:
            return 0, 0
        return self.input_manager.ungrab_key(key)

    def ungrab_keys(self) -> None:
        if self.input_manager:
            self.input_manager.ungrab_keys()

    def grab_button(self, mouse: Mouse) -> int:
        mask = self._translate_mask(mouse.modifiers)
        if mouse.button.startswith("button"):
            button_val = int(mouse.button[6:])
        else:
            button_val = int(mouse.button)
        self.grabbed_buttons.add((button_val, mask))
        return mask

    def ungrab_buttons(self) -> None:
        self.grabbed_buttons.clear()

    def grab_pointer(self) -> None:
        # macOS does not have an exclusive pointer-grab mechanism like X11/Wayland;
        # pointer events are always delivered to the focused app via CGEventTap.
        pass

    def ungrab_pointer(self) -> None:
        # See grab_pointer — no-op on macOS.
        pass

    def keysym_from_name(self, name: str) -> int:
        if self.input_manager:
            return self.input_manager.keysym_from_name(name)
        return 0

    def simulate_keypress(self, modifiers: list[str], key: str) -> None:
        keycode = self.keysym_from_name(key)
        if not keycode:
            return

        mask = 0
        for mod in modifiers:
            m = mod.lower()
            if m == "shift":
                mask |= 0x20000  # Shift
            elif m == "control":
                mask |= 0x40000  # Control
            elif m in ("mod1", "alt", "option"):
                mask |= 0x80000  # Option
            elif m in ("mod4", "command", "meta"):
                mask |= 0x100000  # Command

        self._lib.mac_simulate_keypress(keycode, mask)

    def clear_focus(self) -> None:
        pass

    def get_focused_window(self) -> Window | None:
        from libqtile.backend.macos.window import Window

        w_struct = self._ffi.new("struct mac_window *")
        if self._lib.mac_get_focused_window(w_struct):
            return None

        if w_struct.wid in self.windows:
            return self.windows[w_struct.wid]

        self._lib.mac_window_retain(w_struct)
        return Window(self.qtile, w_struct)

    def warp_pointer(self, x: int, y: int) -> None:
        self._lib.mac_warp_pointer(x, y)

    def get_mouse_position(self) -> tuple[int, int]:
        x = self._ffi.new("int *")
        y = self._ffi.new("int *")
        self._lib.mac_get_mouse_position(x, y)
        return x[0], y[0]

    def create_internal(self, x: int, y: int, width: int, height: int) -> base.Internal:
        from libqtile.backend.macos.drawer import Internal

        return Internal(self.qtile, x, y, width, height)

    def update_desktops(self, groups: list, index: int) -> None:
        # macOS has no virtual desktop protocol equivalent to EWMH
        # _NET_CURRENT_DESKTOP / _NET_NUMBER_OF_DESKTOPS or the Wayland
        # ext-workspace protocol.  There is no system-wide API to advertise
        # the current group list; external tools cannot query desktop state
        # on macOS in the same way as on X11/Wayland.
        pass
