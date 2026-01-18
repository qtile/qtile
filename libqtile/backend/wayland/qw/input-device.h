#ifndef INPUT_DEVICE_H
#define INPUT_DEVICE_H

#include <libinput.h>
#include <wlr/backend/libinput.h>

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

bool qw_input_device_is_touchpad(struct qw_input_device *input_device);

/* Acceleration */
void qw_input_device_config_accel_set_profile(struct libinput_device *device, int accel_profile);
void qw_input_device_config_accel_set_speed(struct libinput_device *device, double pointer_accel);

/* Click method */
void qw_input_device_config_click_set_method(struct libinput_device *device, int click_method);

/* Tap configuration */
void qw_input_device_config_tap_set_drag_enabled(struct libinput_device *device, int drag);
void qw_input_device_config_tap_set_drag_lock_enabled(struct libinput_device *device,
                                                      int drag_lock);
void qw_input_device_config_tap_set_enabled(struct libinput_device *device, int tap);
void qw_input_device_config_tap_set_button_map(struct libinput_device *device, int tap_button_map);

/* Scroll configuration */
void qw_input_device_config_scroll_set_natural_scroll_enabled(struct libinput_device *device,
                                                              int natural_scroll);
void qw_input_device_config_scroll_set_method(struct libinput_device *device, int scroll_method);
void qw_input_device_config_scroll_set_button(struct libinput_device *device, int scroll_button);

/* Disable-while-typing */
void qw_input_device_config_dwt_set_enabled(struct libinput_device *device, int dwt);

/* Left-handed setting */
void qw_input_device_config_left_handed_set(struct libinput_device *device, int left_handed);

/* Middle button emulation */
void qw_input_device_config_middle_emulation_set_enabled(struct libinput_device *device,
                                                         int middle_emulation);

#endif
