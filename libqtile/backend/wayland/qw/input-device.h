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

void qw_input_device_config_accel_set_profile(struct libinput_device *device, int accel_profile);

void qw_input_device_config_tap_set_drag_enabled(struct libinput_device *device, int drag);

void qw_input_device_config_tap_set_drag_lock_enabled(struct libinput_device *input_device, int drag_lock);

void qw_input_device_config_scroll_set_natural_scroll_enabled(struct libinput_device *device, int natural_scroll);

#endif
