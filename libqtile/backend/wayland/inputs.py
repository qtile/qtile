# Copyright (c) 2022-3 Matt Colligan
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

from abc import ABC, abstractmethod
from functools import reduce
from operator import or_
from typing import TYPE_CHECKING

from pywayland.protocol.wayland import WlKeyboard
from xkbcommon import xkb

from libqtile import configurable
from libqtile.backend.wayland.wlrq import HasListeners, buttons
from libqtile.log_utils import logger

try:
    # Continue if ffi not built, so that docs can be built without wayland deps.
    from libqtile.backend.wayland._ffi import ffi, lib

    _has_ffi = True
except ModuleNotFoundError:
    _has_ffi = False

if TYPE_CHECKING:
    from asyncio import TimerHandle
    from typing import Any

    from pywayland.server import Listener
    from wlroots.wlr_types import InputDevice
    from wlroots.wlr_types.keyboard import Keyboard as WlrKeyboard
    from wlroots.wlr_types.keyboard import KeyboardKeyEvent, KeyboardModifier

    from libqtile.backend.wayland.core import Core

KEY_PRESSED = WlKeyboard.key_state.pressed
KEY_RELEASED = WlKeyboard.key_state.released

if _has_ffi:
    # Keep this around instead of creating it on every key
    xkb_keysym = ffi.new("const xkb_keysym_t **")

    ACCEL_PROFILES = {
        "adaptive": lib.LIBINPUT_CONFIG_ACCEL_PROFILE_ADAPTIVE,
        "flat": lib.LIBINPUT_CONFIG_ACCEL_PROFILE_FLAT,
    }

    CLICK_METHODS = {
        "none": lib.LIBINPUT_CONFIG_CLICK_METHOD_NONE,
        "button_areas": lib.LIBINPUT_CONFIG_CLICK_METHOD_BUTTON_AREAS,
        "clickfinger": lib.LIBINPUT_CONFIG_CLICK_METHOD_CLICKFINGER,
    }

    TAP_MAPS = {
        "lrm": lib.LIBINPUT_CONFIG_TAP_MAP_LRM,
        "lmr": lib.LIBINPUT_CONFIG_TAP_MAP_LMR,
    }

    SCROLL_METHODS = {
        "none": lib.LIBINPUT_CONFIG_SCROLL_NO_SCROLL,
        "two_finger": lib.LIBINPUT_CONFIG_SCROLL_2FG,
        "edge": lib.LIBINPUT_CONFIG_SCROLL_EDGE,
        "on_button_down": lib.LIBINPUT_CONFIG_SCROLL_ON_BUTTON_DOWN,
    }


class InputConfig(configurable.Configurable):
    """
    This is used to configure input devices. An instance of this class represents one
    set of settings that can be applied to an input device.

    To use this, define a dictionary called ``wl_input_rules`` in your config. The keys
    are used to match input devices, and the values are instances of this class with the
    desired settings. For example:

    .. code-block:: python

        from libqtile.backend.wayland import InputConfig

        wl_input_rules = {
            "1267:12377:ELAN1300:00 04F3:3059 Touchpad": InputConfig(left_handed=True),
            "*": InputConfig(left_handed=True, pointer_accel=True),
            "type:keyboard": InputConfig(kb_options="ctrl:nocaps,compose:ralt"),
        }

    When a input device is being configured, the most specific matching key in the
    dictionary is found and the corresponding settings are used to configure the device.
    Unique identifiers are chosen first, then ``"type:X"``, then ``"*"``.

    The command ``qtile cmd-obj -o core -f get_inputs`` can be used to get information
    about connected devices, including their identifiers.

    Options default to ``None``, leave a device's default settings intact. For
    information on what each option does, see the documenation for libinput:
    https://wayland.freedesktop.org/libinput/doc/latest/configuration.html. Note that
    devices often only support a subset of settings.

    This tries to mirror how Sway configures libinput devices. For more information
    check out sway-input(5): https://man.archlinux.org/man/sway-input.5#LIBINPUT_CONFIGURATION

    Keyboards, managed by `xkbcommon <https://github.com/xkbcommon/libxkbcommon>`_, are
    configured with the options prefixed by ``kb_``. X11's helpful `XKB guide
    <https://www.x.org/releases/X11R7.5/doc/input/XKB-Config.html>`_ may be useful for
    figuring out the syntax for some of these settings.
    """

    defaults = [
        ("accel_profile", None, "``'adaptive'`` or ``'flat'``"),
        ("click_method", None, "``'none'``, ``'button_areas'`` or ``'clickfinger'``"),
        ("drag", None, "``True`` or ``False``"),
        ("drag_lock", None, "``True`` or ``False``"),
        ("dwt", None, "True or False"),
        ("left_handed", None, "``True`` or ``False``"),
        ("middle_emulation", None, "``True`` or ``False``"),
        ("natural_scroll", None, "``True`` or ``False``"),
        ("pointer_accel", None, "A ``float`` between -1 and 1."),
        ("scroll_button", None, "``'disable'``, 'Button[1-3,8,9]' or a keycode"),
        (
            "scroll_method",
            None,
            "``'none'``, ``'two_finger'``, ``'edge'``, or ``'on_button_down'``",
        ),
        ("tap", None, "``True`` or ``False``"),
        ("tap_button_map", None, "``'lrm'`` or ``'lmr'``"),
        ("kb_layout", None, "Keyboard layout i.e. ``XKB_DEFAULT_LAYOUT``"),
        ("kb_options", None, "Keyboard options i.e. ``XKB_DEFAULT_OPTIONS``"),
        ("kb_variant", None, "Keyboard variant i.e. ``XKB_DEFAULT_VARIANT``"),
        ("kb_repeat_rate", 25, "Keyboard key repeats made per second"),
        ("kb_repeat_delay", 600, "Keyboard delay in milliseconds before repeating"),
    ]

    def __init__(self, **config: Any) -> None:
        configurable.Configurable.__init__(self, **config)
        self.add_defaults(InputConfig.defaults)


class _Device(ABC, HasListeners):
    def __init__(self, core: Core, wlr_device: InputDevice):
        self.core = core
        self.wlr_device = wlr_device

        self.add_listener(wlr_device.destroy_event, self._on_destroy)

    def finalize(self) -> None:
        self.finalize_listeners()

    def _on_destroy(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: wlr_device destroy (%s)", self.__class__.__name__)
        self.finalize()

    def get_info(self) -> tuple[str, str]:
        """
        Get the device type and identifier for this input device. These can be used be
        used to assign ``InputConfig`` options to devices or types of devices.
        """
        device = self.wlr_device
        name = device.name
        if name == " " or not name.isprintable():
            name = "_"
        type_key = "type:" + device.type.name.lower()
        identifier = f"{device.vendor:d}:{device.product:d}:{name!s}"

        if type_key == "type:pointer" and lib is not None:
            # This checks whether the pointer is a touchpad, so that we can target those
            # specifically.
            handle = device.libinput_get_device_handle()
            if handle and lib.libinput_device_config_tap_get_finger_count(handle) > 0:
                type_key = "type:touchpad"

        return type_key, identifier

    def _match_config(self, configs: dict[str, InputConfig]) -> InputConfig | None:
        """Finds a matching ``InputConfig`` rule."""
        type_key, identifier = self.get_info()

        if identifier in configs:
            conf = configs[identifier]
        elif type_key in configs:
            conf = configs[type_key]
        elif "*" in configs:
            conf = configs["*"]
        else:
            return None
        return conf

    @abstractmethod
    def configure(self, configs: dict[str, InputConfig]) -> None:
        """Applies ``InputConfig`` rules to this input device."""


class Keyboard(_Device):
    def __init__(self, core: Core, wlr_device: InputDevice, keyboard: WlrKeyboard):
        super().__init__(core, wlr_device)
        self.seat = core.seat
        self.keyboard = keyboard
        self.grabbed_keys = core.grabbed_keys
        self.repeat_delay_future: TimerHandle | None = None
        self.repeat_rate_future: TimerHandle | None = None

        self.keyboard.set_repeat_info(25, 600)
        self.xkb_context = xkb.Context()
        self._keymaps: dict[tuple[str | None, str | None, str | None], xkb.Keymap] = {}
        self.set_keymap(None, None, None)

        self.add_listener(self.keyboard.modifiers_event, self._on_modifier)
        self.add_listener(self.keyboard.key_event, self._on_key)

    def finalize(self) -> None:
        super().finalize()
        self.core.keyboards.remove(self)
        if self.core.seat.get_keyboard() == self.keyboard:
            # If this is the active keyboard and we have other keyboards enabled, set
            # the previous keyboard as the new active keyboard.
            if self.core.keyboards:
                self.seat.set_keyboard(self.core.keyboards[-1].keyboard)

    def set_keymap(self, layout: str | None, options: str | None, variant: str | None) -> None:
        """
        Set the keymap for this keyboard.
        """
        if (layout, options, variant) in self._keymaps:
            keymap = self._keymaps[(layout, options, variant)]
        else:
            keymap = self.xkb_context.keymap_new_from_names(
                layout=layout, options=options, variant=variant
            )
            self._keymaps[(layout, options, variant)] = keymap
        self._state = keymap.state_new()
        self.keyboard.set_keymap(keymap)

    def _on_modifier(self, _listener: Listener, _data: Any) -> None:
        self.seat.set_keyboard(self.keyboard)
        self.seat.keyboard_notify_modifiers(self.keyboard.modifiers)

    def _on_repeat_key(self, keysyms: list[int], mods: KeyboardModifier) -> None:
        repeat_rate = self.keyboard._ptr.repeat_info.rate
        if self.repeat_delay_future is None or repeat_rate <= 0:
            return
        # when the repeat rate is set to 25 it means that we need to repeat the key 25 times per second
        # so divide 1 by the repeat rate
        self.repeat_rate_future = self.qtile.call_later(
            1 / repeat_rate, self._on_repeat_key, keysyms, mods
        )
        for keysym in keysyms:
            if (keysym, mods) in self.grabbed_keys:
                if self.qtile.process_key_event(keysym, mods)[1]:
                    return

    def _on_key(self, _listener: Listener, event: KeyboardKeyEvent) -> None:
        self.qtile = self.core.qtile

        self.core.idle.notify_activity(self.seat)

        if not self.core.exclusive_client:
            # translate libinput keycode -> xkbcommon
            keycode = event.keycode + 8
            layout_index = lib.xkb_state_key_get_layout(self.keyboard._ptr.xkb_state, keycode)
            nsyms = lib.xkb_keymap_key_get_syms_by_level(
                self.keyboard._ptr.keymap,
                keycode,
                layout_index,
                0,
                xkb_keysym,
            )
            keysyms = [xkb_keysym[0][i] for i in range(nsyms)]
            mods = reduce(or_, [k.keyboard.modifier for k in self.core.keyboards])
            handled = False
            should_repeat = False
            if event.state == KEY_PRESSED:
                for keysym in keysyms:
                    if (keysym, mods) in self.grabbed_keys:
                        should_repeat = True
                        if self.qtile.process_key_event(keysym, mods)[1]:
                            handled = True
                            break

            repeat_delay = self.keyboard._ptr.repeat_info.delay
            if should_repeat and repeat_delay > 0:
                # repeat delay is the delay in ms, whereas call_later expects the delay in seconds
                self.repeat_delay_future = self.qtile.call_later(
                    repeat_delay / 1000, self._on_repeat_key, keysyms, mods
                )
            else:
                if self.repeat_delay_future is not None:
                    self.repeat_delay_future.cancel()
                    self.repeat_delay_future = None
                if self.repeat_rate_future is not None:
                    self.repeat_rate_future.cancel()
                    self.repeat_rate_future = None

            if handled:
                return
            if self.core.focused_internal:
                self.core.focused_internal.process_key_press(keysym)
                return

        self.seat.keyboard_notify_key(event)

    def configure(self, configs: dict[str, InputConfig]) -> None:
        """Applies ``InputConfig`` rules to this keyboard device."""
        config = self._match_config(configs)

        if config:
            self.keyboard.set_repeat_info(config.kb_repeat_rate, config.kb_repeat_delay)
            self.set_keymap(config.kb_layout, config.kb_options, config.kb_variant)


class Pointer(_Device):
    def finalize(self) -> None:
        super().finalize()
        self.core._pointers.remove(self)

    def configure(self, configs: dict[str, InputConfig]) -> None:
        """Applies ``InputConfig`` rules to this pointer device."""
        config = self._match_config(configs)
        if config is None:
            return

        handle = self.wlr_device.libinput_get_device_handle()
        if handle is None:
            logger.debug("Device not handled by libinput: %s", self.wlr_device.name)
            return

        if lib.libinput_device_config_accel_is_available(handle):
            if ACCEL_PROFILES.get(config.accel_profile):
                lib.libinput_device_config_accel_set_profile(
                    handle, ACCEL_PROFILES.get(config.accel_profile)
                )
            if config.pointer_accel is not None:
                lib.libinput_device_config_accel_set_speed(handle, config.pointer_accel)

        if CLICK_METHODS.get(config.click_method):
            lib.libinput_device_config_click_set_method(
                handle, CLICK_METHODS.get(config.click_method)
            )

        if config.drag is not None:
            lib.libinput_device_config_tap_set_drag_enabled(handle, int(config.drag))

        if config.drag_lock is not None:
            lib.libinput_device_config_tap_set_drag_lock_enabled(handle, int(config.drag_lock))

        if config.dwt is not None:
            if lib.libinput_device_config_dwt_is_available(handle):
                lib.libinput_device_config_dwt_set_enabled(handle, int(config.dwt))

        if config.left_handed is not None:
            if lib.libinput_device_config_left_handed_is_available(handle):
                lib.libinput_device_config_left_handed_set(handle, int(config.left_handed))

        if config.middle_emulation is not None:
            lib.libinput_device_config_middle_emulation_set_enabled(
                handle, int(config.middle_emulation)
            )

        if config.natural_scroll is not None:
            if lib.libinput_device_config_scroll_has_natural_scroll(handle):
                lib.libinput_device_config_scroll_set_natural_scroll_enabled(
                    handle, int(config.natural_scroll)
                )

        if SCROLL_METHODS.get(config.scroll_method):
            lib.libinput_device_config_scroll_set_method(
                handle, SCROLL_METHODS.get(config.scroll_method)
            )
            if config.scroll_method == "on_button_down":
                if isinstance(config.scroll_button, str):
                    if config.scroll_button == "disable":
                        button = 0
                    else:  # e.g. Button1
                        button = buttons[int(config.scroll_button[-1]) - 1]
                else:
                    button = config.scroll_button
                lib.libinput_device_config_scroll_set_button(handle, button)

        if lib.libinput_device_config_tap_get_finger_count(handle) > 1:
            if config.tap is not None:
                lib.libinput_device_config_tap_set_enabled(handle, int(config.tap))

            if config.tap_button_map is not None:
                if TAP_MAPS.get(config.tap_button_map):
                    lib.libinput_device_config_tap_set_button_map(
                        handle, TAP_MAPS.get(config.tap_button_map)
                    )
