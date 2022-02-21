# Copyright (c) 2022 Matt Colligan
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

from typing import TYPE_CHECKING

from pywayland.protocol.wayland import WlKeyboard
from wlroots import ffi, lib
from wlroots.wlr_types import input_device
from xkbcommon import xkb

from libqtile import configurable
from libqtile.backend.wayland.wlrq import HasListeners, buttons
from libqtile.log_utils import logger

try:
    from libqtile.backend.wayland._libinput import lib as libinput  # type: ignore
except ImportError:
    # We want to continue without erroring here, so that the docs can build without the
    # hard dependency of wlroots.
    libinput = None

if TYPE_CHECKING:
    from typing import Any

    from pywayland.server import Listener
    from wlroots.wlr_types import InputDevice
    from wlroots.wlr_types.keyboard import KeyboardKeyEvent

    from libqtile.backend.wayland.core import Core

KEY_PRESSED = WlKeyboard.key_state.pressed
KEY_RELEASED = WlKeyboard.key_state.released

# Keep this around instead of creating it on every key
xkb_keysym = ffi.new("const xkb_keysym_t **")


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
            "type:keyboard": InputConfig(xkb_options="caps:swapescape"),
        }

    When a input device is being configured, the most specific matching key in the
    dictionary is found and the corresponding settings are used to configure the device.
    Unique identifiers are chosen first, then ``"type:X"``, then ``"*"``.

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

    def __init__(self, **config: dict[str, Any]) -> None:
        configurable.Configurable.__init__(self, **config)
        self.add_defaults(InputConfig.defaults)


if libinput:
    ACCEL_PROFILES = {
        "adaptive": libinput.LIBINPUT_CONFIG_ACCEL_PROFILE_ADAPTIVE,
        "flat": libinput.LIBINPUT_CONFIG_ACCEL_PROFILE_FLAT,
    }

    CLICK_METHODS = {
        "none": libinput.LIBINPUT_CONFIG_CLICK_METHOD_NONE,
        "button_areas": libinput.LIBINPUT_CONFIG_CLICK_METHOD_BUTTON_AREAS,
        "clickfinger": libinput.LIBINPUT_CONFIG_CLICK_METHOD_CLICKFINGER,
    }

    TAP_MAPS = {
        "lrm": libinput.LIBINPUT_CONFIG_TAP_MAP_LRM,
        "lmr": libinput.LIBINPUT_CONFIG_TAP_MAP_LMR,
    }

    SCROLL_METHODS = {
        "none": libinput.LIBINPUT_CONFIG_SCROLL_NO_SCROLL,
        "two_finger": libinput.LIBINPUT_CONFIG_SCROLL_2FG,
        "edge": libinput.LIBINPUT_CONFIG_SCROLL_EDGE,
        "on_button_down": libinput.LIBINPUT_CONFIG_SCROLL_ON_BUTTON_DOWN,
    }


class Keyboard(HasListeners):
    def __init__(self, core: Core, device: InputDevice):
        self.core = core
        self.device = device
        self.qtile = core.qtile
        self.seat = core.seat
        self.keyboard = device.keyboard
        self.keyboard.data = self
        self.grabbed_keys = core.grabbed_keys

        self.keyboard.set_repeat_info(25, 600)
        self.xkb_context = xkb.Context()
        self._keymaps: dict[tuple[str | None, str | None, str | None], xkb.Keymap] = {}
        self.set_keymap(None, None, None)

        self.add_listener(self.keyboard.modifiers_event, self._on_modifier)
        self.add_listener(self.keyboard.key_event, self._on_key)
        self.add_listener(self.keyboard.destroy_event, self._on_destroy)

    def finalize(self) -> None:
        self.finalize_listeners()
        self.core.keyboards.remove(self)
        if self.core.keyboards and self.core.seat.keyboard.destroyed:
            self.seat.set_keyboard(self.core.keyboards[-1].device)

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
        self.keyboard.set_keymap(keymap)

    def _on_destroy(self, _listener: Listener, _data: Any) -> None:
        logger.debug("Signal: keyboard destroy")
        self.finalize()

    def _on_modifier(self, _listener: Listener, _data: Any) -> None:
        self.seat.set_keyboard(self.device)
        self.seat.keyboard_notify_modifiers(self.keyboard.modifiers)

    def _on_key(self, _listener: Listener, event: KeyboardKeyEvent) -> None:
        if self.qtile is None:
            # shushes mypy
            self.qtile = self.core.qtile
            assert self.qtile is not None

        self.core.idle.notify_activity(self.seat)

        if event.state == KEY_PRESSED:
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
            mods = self.keyboard.modifier
            for keysym in keysyms:
                if (keysym, mods) in self.grabbed_keys:
                    self.qtile.process_key_event(keysym, mods)
                    return

            if self.core.focused_internal:
                self.core.focused_internal.process_key_press(keysym)
                return

        self.seat.keyboard_notify_key(event)


def _configure_keyboard(device: InputDevice, conf: InputConfig) -> None:
    """Applies ``InputConfig`` rules to a keyboard device"""
    device.keyboard.set_repeat_info(conf.kb_repeat_rate, conf.kb_repeat_delay)
    if isinstance(device.keyboard.data, Keyboard):
        device.keyboard.data.set_keymap(conf.kb_layout, conf.kb_options, conf.kb_variant)
    else:
        logger.error("Couldn't configure keyboard. Please report this.")


_logged_unsupported = False


def _configure_pointer(device: InputDevice, conf: InputConfig, name: str) -> None:
    """Applies ``InputConfig`` rules to a pointer device"""
    handle = device.libinput_get_device_handle()
    if handle is None:
        logger.debug(f"Device not handled by libinput: {name}")
        return

    if libinput is None:
        global _logged_unsupported

        if not _logged_unsupported:
            logger.error(
                "Qtile was not built with libinput configuration support. "
                "For support, pywlroots must be installed at build time."
            )
            _logged_unsupported = True
        return

    if libinput.libinput_device_config_accel_is_available(handle):
        if ACCEL_PROFILES.get(conf.accel_profile):
            libinput.libinput_device_config_accel_set_profile(
                handle, ACCEL_PROFILES.get(conf.accel_profile)
            )
        if conf.pointer_accel is not None:
            libinput.libinput_device_config_accel_set_speed(handle, conf.pointer_accel)

    if CLICK_METHODS.get(conf.click_method):
        libinput.libinput_device_config_click_set_method(
            handle, CLICK_METHODS.get(conf.click_method)
        )

    if conf.drag is not None:
        libinput.libinput_device_config_tap_set_drag_enabled(handle, int(conf.drag))

    if conf.drag_lock is not None:
        libinput.libinput_device_config_tap_set_drag_lock_enabled(handle, int(conf.drag_lock))

    if conf.dwt is not None:
        if libinput.libinput_device_config_dwt_is_available(handle):
            libinput.libinput_device_config_dwt_set_enabled(handle, int(conf.dwt))

    if conf.left_handed is not None:
        if libinput.libinput_device_config_left_handed_is_available(handle):
            libinput.libinput_device_config_left_handed_set(handle, int(conf.left_handed))

    if conf.middle_emulation is not None:
        libinput.libinput_device_config_middle_emulation_set_enabled(
            handle, int(conf.middle_emulation)
        )

    if conf.natural_scroll is not None:
        if libinput.libinput_device_config_scroll_has_natural_scroll(handle):
            libinput.libinput_device_config_scroll_set_natural_scroll_enabled(
                handle, int(conf.natural_scroll)
            )

    if SCROLL_METHODS.get(conf.scroll_method):
        libinput.libinput_device_config_scroll_set_method(
            handle, SCROLL_METHODS.get(conf.scroll_method)
        )
        if conf.scroll_method == "on_button_down":
            if isinstance(conf.scroll_button, str):
                if conf.scroll_button == "disable":
                    button = 0
                else:  # e.g. Button1
                    button = buttons[int(conf.scroll_button[-1]) - 1]
            else:
                button = conf.scroll_button
            libinput.libinput_device_config_scroll_set_button(handle, button)

    if libinput.libinput_device_config_tap_get_finger_count(handle) > 1:
        if conf.tap is not None:
            libinput.libinput_device_config_tap_set_enabled(handle, int(conf.tap))

        if conf.tap_button_map is not None:
            if TAP_MAPS.get(conf.tap_button_map):
                libinput.libinput_device_config_tap_set_button_map(
                    handle, TAP_MAPS.get(conf.tap_button_map)
                )


def configure_device(device: InputDevice, configs: dict[str, InputConfig]) -> None:
    if not configs:
        return

    # Find a matching InputConfig
    name = device.name
    if name == " " or not name.isprintable():
        name = "_"
    identifier = "%d:%d:%s" % (device.vendor, device.product, name)
    type_key = "type:" + device.device_type.name.lower()

    if type_key == "type:pointer":
        # This checks whether the pointer is a touchpad.
        handle = device.libinput_get_device_handle()
        if handle and libinput.libinput_device_config_tap_get_finger_count(handle) > 0:
            type_key = "type:touchpad"

    if identifier in configs:
        conf = configs[identifier]
    elif type_key in configs:
        conf = configs[type_key]
    elif "*" in configs:
        conf = configs["*"]
    else:
        return

    if device.device_type == input_device.InputDeviceType.POINTER:
        _configure_pointer(device, conf, name)
    elif device.device_type == input_device.InputDeviceType.KEYBOARD:
        _configure_keyboard(device, conf)
    else:
        logger.warning("Device not configured. Type '%s' not recognised.", device.device_type)
