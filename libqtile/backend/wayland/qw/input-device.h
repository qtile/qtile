#ifndef INPUT_DEVICE_H
#define INPUT_DEVICE_H

enum wlr_input_device_type {
    WLR_INPUT_DEVICE_KEYBOARD,
    WLR_INPUT_DEVICE_POINTER,
    WLR_INPUT_DEVICE_TOUCH,
    WLR_INPUT_DEVICE_TABLET,
    WLR_INPUT_DEVICE_TABLET_PAD,
    WLR_INPUT_DEVICE_SWITCH,
};

enum libinput_config_accel_profile {
    LIBINPUT_CONFIG_ACCEL_PROFILE_NONE = 0,
    LIBINPUT_CONFIG_ACCEL_PROFILE_FLAT = (1 << 0),
    LIBINPUT_CONFIG_ACCEL_PROFILE_ADAPTIVE = (1 << 1),
    LIBINPUT_CONFIG_ACCEL_PROFILE_CUSTOM = (1 << 2),
};

enum libinput_config_click_method {
        LIBINPUT_CONFIG_CLICK_METHOD_NONE = 0,
        LIBINPUT_CONFIG_CLICK_METHOD_BUTTON_AREAS = (1 << 0),
        LIBINPUT_CONFIG_CLICK_METHOD_CLICKFINGER = (1 << 1),
};

enum libinput_config_tap_button_map {
        LIBINPUT_CONFIG_TAP_MAP_LRM,
        LIBINPUT_CONFIG_TAP_MAP_LMR,
};

enum libinput_config_scroll_method {
        LIBINPUT_CONFIG_SCROLL_NO_SCROLL = 0,
        LIBINPUT_CONFIG_SCROLL_2FG = (1 << 0),
        LIBINPUT_CONFIG_SCROLL_EDGE = (1 << 1),
        LIBINPUT_CONFIG_SCROLL_ON_BUTTON_DOWN = (1 << 2),
};

struct qw_input_device {
    // Private data
    struct qw_server *server;
    struct wl_list link;
    struct wlr_input_device *device;

    struct wl_listener destroy;
};

void qw_server_input_device_new(struct qw_server *server, struct wlr_input_device *device);

struct libinput_device *qw_input_device_get_libinput_handle(struct qw_input_device *input_device);

struct qw_keyboard *qw_input_device_get_keyboard(struct qw_input_device *input_device);

/* Acceleration */
void qw_input_device_config_accel_set_profile(struct libinput_device *device, int accel_profile);
void qw_input_device_config_accel_set_speed(struct libinput_device *device, double pointer_accel);

/* Click method */
void qw_input_device_config_click_set_method(struct libinput_device *device, int click_method);

/* Tap configuration */
void qw_input_device_config_tap_set_drag_enabled(struct libinput_device *device, int drag);
void qw_input_device_config_tap_set_drag_lock_enabled(struct libinput_device *device, int drag_lock);
void qw_input_device_config_tap_set_enabled(struct libinput_device *device, int tap);
void qw_input_device_config_tap_set_button_map(struct libinput_device *device, int tap_button_map);

/* Scroll configuration */
void qw_input_device_config_scroll_set_natural_scroll_enabled(struct libinput_device *device, int natural_scroll);
void qw_input_device_config_scroll_set_method(struct libinput_device *device, int scroll_method);
void qw_input_device_config_scroll_set_button(struct libinput_device *device, int scroll_button);

/* Disable-while-typing */
void qw_input_device_config_dwt_set_enabled(struct libinput_device *device, int dwt);

/* Left-handed setting */
void qw_input_device_config_left_handed_set(struct libinput_device *device, int left_handed);

/* Middle button emulation */
void qw_input_device_config_middle_emulation_set_enabled(struct libinput_device *device, int middle_emulation);

#endif
