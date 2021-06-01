import wlroots.ffi_build as wlr
from cffi import FFI

CDEF = """
enum libinput_config_status {
    LIBINPUT_CONFIG_STATUS_SUCCESS = 0,
    LIBINPUT_CONFIG_STATUS_UNSUPPORTED,
    LIBINPUT_CONFIG_STATUS_INVALID,
};

int
libinput_device_config_tap_get_finger_count(struct libinput_device *device);

enum libinput_config_tap_state {
    LIBINPUT_CONFIG_TAP_DISABLED,
    LIBINPUT_CONFIG_TAP_ENABLED,
};

enum libinput_config_status
libinput_device_config_tap_set_enabled(struct libinput_device *device,
                                       enum libinput_config_tap_state enable);

enum libinput_config_tap_button_map {
    LIBINPUT_CONFIG_TAP_MAP_LRM,
    LIBINPUT_CONFIG_TAP_MAP_LMR,
};

enum libinput_config_status
libinput_device_config_tap_set_button_map(struct libinput_device *device,
    enum libinput_config_tap_button_map map);

enum libinput_config_drag_state {
    LIBINPUT_CONFIG_DRAG_DISABLED,
    LIBINPUT_CONFIG_DRAG_ENABLED,
};

enum libinput_config_status
libinput_device_config_tap_set_drag_enabled(struct libinput_device *device,
                                            enum libinput_config_drag_state enable);

enum libinput_config_drag_lock_state {
    LIBINPUT_CONFIG_DRAG_LOCK_DISABLED,
    LIBINPUT_CONFIG_DRAG_LOCK_ENABLED,
};

enum libinput_config_status
libinput_device_config_tap_set_drag_lock_enabled(struct libinput_device *device,
                                                 enum libinput_config_drag_lock_state enable);

int
libinput_device_config_accel_is_available(struct libinput_device *device);

enum libinput_config_status
libinput_device_config_accel_set_speed(struct libinput_device *device,
                                       double speed);

enum libinput_config_accel_profile {
    LIBINPUT_CONFIG_ACCEL_PROFILE_NONE = 0,
    LIBINPUT_CONFIG_ACCEL_PROFILE_FLAT = (1 << 0),
    LIBINPUT_CONFIG_ACCEL_PROFILE_ADAPTIVE = (1 << 1),
};

enum libinput_config_status
libinput_device_config_accel_set_profile(struct libinput_device *device,
                                         enum libinput_config_accel_profile profile);

int
libinput_device_config_scroll_has_natural_scroll(struct libinput_device *device);

enum libinput_config_status
libinput_device_config_scroll_set_natural_scroll_enabled(struct libinput_device *device,
                                                         int enable);

int
libinput_device_config_left_handed_is_available(struct libinput_device *device);

enum libinput_config_status
libinput_device_config_left_handed_set(struct libinput_device *device,
                                       int left_handed);

enum libinput_config_click_method {
    LIBINPUT_CONFIG_CLICK_METHOD_NONE = 0,
    LIBINPUT_CONFIG_CLICK_METHOD_BUTTON_AREAS = (1 << 0),
    LIBINPUT_CONFIG_CLICK_METHOD_CLICKFINGER = (1 << 1),
};

enum libinput_config_status
libinput_device_config_click_set_method(struct libinput_device *device,
                                        enum libinput_config_click_method method);

enum libinput_config_middle_emulation_state {
    LIBINPUT_CONFIG_MIDDLE_EMULATION_DISABLED,
    LIBINPUT_CONFIG_MIDDLE_EMULATION_ENABLED,
};

enum libinput_config_status
libinput_device_config_middle_emulation_set_enabled(
    struct libinput_device *device,
    enum libinput_config_middle_emulation_state enable);

enum libinput_config_scroll_method {
    LIBINPUT_CONFIG_SCROLL_NO_SCROLL = 0,
    LIBINPUT_CONFIG_SCROLL_2FG = (1 << 0),
    LIBINPUT_CONFIG_SCROLL_EDGE = (1 << 1),
    LIBINPUT_CONFIG_SCROLL_ON_BUTTON_DOWN = (1 << 2),
};

enum libinput_config_status
libinput_device_config_scroll_set_method(struct libinput_device *device,
                                         enum libinput_config_scroll_method method);

enum libinput_config_status
libinput_device_config_scroll_set_button(struct libinput_device *device,
                                         uint32_t button);

enum libinput_config_dwt_state {
    LIBINPUT_CONFIG_DWT_DISABLED,
    LIBINPUT_CONFIG_DWT_ENABLED,
};

int
libinput_device_config_dwt_is_available(struct libinput_device *device);

enum libinput_config_status
libinput_device_config_dwt_set_enabled(struct libinput_device *device,
                                       enum libinput_config_dwt_state enable);
"""

libinput_ffi = FFI()
libinput_ffi.set_source(
    "libqtile.backend.wayland._libinput",
    "#include <libinput.h>\n" + wlr.SOURCE,
    libraries=["wlroots", "input"],
    define_macros=[("WLR_USE_UNSTABLE", None)],
    include_dirs=["/usr/include/pixman-1", wlr.include_dir],
)

libinput_ffi.include(wlr.ffi_builder)
libinput_ffi.cdef(CDEF)

if __name__ == "__main__":
    libinput_ffi.compile()
