import enum
from typing import Any

from libqtile import configurable

try:
    from libqtile.backend.wayland._ffi import ffi, lib

except ModuleNotFoundError:
    print("Warning: Wayland backend not built. Backend will not run.")

    from libqtile.backend.wayland.ffi_stub import ffi, lib


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


class InputDeviceType(enum.IntEnum):
    KEYBOARD = lib.WLR_INPUT_DEVICE_KEYBOARD
    POINTER = lib.WLR_INPUT_DEVICE_POINTER
    TOUCH = lib.WLR_INPUT_DEVICE_TOUCH
    TABLET = lib.WLR_INPUT_DEVICE_TABLET
    TABLET_PAD = lib.WLR_INPUT_DEVICE_TABLET_PAD
    SWITCH = lib.WLR_INPUT_DEVICE_SWITCH


class AccelProfile(enum.IntEnum):
    adaptive = lib.LIBINPUT_CONFIG_ACCEL_PROFILE_ADAPTIVE
    flat = lib.LIBINPUT_CONFIG_ACCEL_PROFILE_FLAT


class ClickMethod(enum.IntEnum):
    none = lib.LIBINPUT_CONFIG_CLICK_METHOD_NONE
    button_areas = lib.LIBINPUT_CONFIG_CLICK_METHOD_BUTTON_AREAS
    clickfinger = lib.LIBINPUT_CONFIG_CLICK_METHOD_CLICKFINGER


class TapMap(enum.IntEnum):
    lrm = lib.LIBINPUT_CONFIG_TAP_MAP_LRM
    lmr = lib.LIBINPUT_CONFIG_TAP_MAP_LMR


class ScrollMethod(enum.IntEnum):
    none = lib.LIBINPUT_CONFIG_SCROLL_NO_SCROLL
    two_finger = lib.LIBINPUT_CONFIG_SCROLL_2FG
    edge = lib.LIBINPUT_CONFIG_SCROLL_EDGE
    on_button_down = lib.LIBINPUT_CONFIG_SCROLL_ON_BUTTON_DOWN


def configure_input_devices(server: ffi.CData, configs: dict[str, Any]) -> None:
    @ffi.callback(
        "void(struct qw_input_device *input_device, char *name, int type, int vendor, int product)"
    )
    def input_device_cb(
        input_device: ffi.CData, name: ffi.CData, type: int, vendor: int, product: int
    ) -> None:
        # Get the device type and identifier for this input device. These can be used be
        # used to assign ``InputConfig`` options to devices or types of devices.
        name = ffi.string(name).decode()
        if name == " " or not name.isprintable():
            name = "_"
        type_key = "type:" + InputDeviceType(type).name.lower()
        identifier = f"{vendor:d}:{product:d}:{name!s}"

        if type_key == "type:pointer" and lib is not None:
            # This checks whether the pointer is a touchpad, so that we can target those
            # specifically.
            if lib.qw_input_device_is_touchpad(input_device):
                type_key = "type:touchpad"

        if identifier in configs:
            conf = configs[identifier]
        elif type_key in configs:
            conf = configs[type_key]
        elif "*" in configs:
            conf = configs["*"]
        else:
            conf = None

        if conf is not None:
            if type == InputDeviceType.POINTER:
                device = lib.qw_input_device_get_libinput_handle(input_device)
                if device == ffi.NULL:
                    return

                if conf.accel_profile is not None:
                    lib.qw_input_device_config_accel_set_profile(
                        device, AccelProfile[conf.accel_profile].value
                    )

                if conf.pointer_accel is not None:
                    lib.qw_input_device_config_accel_set_speed(device, conf.pointer_accel)

                if conf.click_method is not None:
                    lib.qw_input_device_config_click_set_method(
                        device, ClickMethod[conf.click_method].value
                    )

                if conf.drag is not None:
                    lib.qw_input_device_config_tap_set_drag_enabled(device, int(conf.drag))

                if conf.drag_lock is not None:
                    lib.qw_input_device_config_tap_set_drag_lock_enabled(
                        device, int(conf.drag_lock)
                    )

                if conf.tap is not None:
                    lib.qw_input_device_config_tap_set_enabled(device, int(conf.tap))

                if conf.tap_button_map is not None:
                    lib.qw_input_device_config_tap_set_button_map(
                        device, TapMap[conf.tap_button_map].value
                    )

                if conf.natural_scroll is not None:
                    lib.qw_input_device_config_scroll_set_natural_scroll_enabled(
                        device, int(conf.natural_scroll)
                    )

                if conf.scroll_method is not None:
                    lib.qw_input_device_config_scroll_set_method(
                        device, ScrollMethod[conf.scroll_method].value
                    )

                if conf.scroll_button is not None:
                    if isinstance(conf.scroll_button, str):
                        if conf.scroll_button == "disable":
                            button = 0
                        else:
                            button = lib.qw_util_get_button_code(int(conf.scroll_button[-1]) - 1)
                    else:
                        button = conf.scroll_button
                    lib.qw_input_device_config_scroll_set_button(device, button)

                if conf.dwt is not None:
                    lib.qw_input_device_config_dwt_set_enabled(device, int(conf.dwt))

                if conf.left_handed is not None:
                    lib.qw_input_device_config_left_handed_set(device, int(conf.left_handed))

                if conf.middle_emulation is not None:
                    lib.qw_input_device_config_middle_emulation_set_enabled(
                        device, int(conf.middle_emulation)
                    )

            elif type == InputDeviceType.KEYBOARD:
                keyboard = lib.qw_input_device_get_keyboard(input_device)
                if keyboard == ffi.NULL:
                    return

                lib.qw_keyboard_set_repeat_info(
                    keyboard, conf.kb_repeat_rate, conf.kb_repeat_delay
                )
                lib.qw_keyboard_set_keymap(
                    keyboard,
                    ffi.new("char[]", (conf.kb_layout or "").encode()),
                    ffi.new("char[]", (conf.kb_options or "").encode()),
                    ffi.new("char[]", (conf.kb_variant or "").encode()),
                )

    lib.qw_server_loop_input_devices(server, input_device_cb)
