#include <libinput.h>
#include <wlr/backend/libinput.h>
#include "input-device.h"

void qw_server_input_device_new(struct qw_server *server, struct wlr_input_device *device) {
    struct qw_input_device *input_device = calloc(1, sizeof(*input_device));
    if (input_device == NULL) {
        wlr_log(WLR_ERROR, "failed to create qw_input_device struct");
        return;
    }

    input_device->server = server;
    input_device->device = device;
    wl_list_insert(&server->input_devices, &input_device->link); 

    // TODO: Remove devices from list when they are removed
}

struct libinput_device *qw_input_device_get_libinput_handle(struct qw_input_device *input_device) {
    if (wlr_input_device_is_libinput(input_device->device) == false) {
        return NULL;
    }
    return wlr_libinput_get_device_handle(input_device->device);
}

struct wlr_keyboard *qw_input_device_get_keyboard(struct qw_input_device *input_device) {
    struct wlr_keyboard *keyboard = wlr_keyboard_from_input_device(input_device->device);
    return keyboard;
}

void qw_input_device_config_kbd_set_repeat_info(struct wlr_keyboard *keyboard, int kb_repeat_rate, int kb_repeat_delay) {
    wlr_keyboard_set_repeat_info(keyboard, kb_repeat_rate, kb_repeat_delay);
}

void qw_input_device_config_accel_set_profile(struct libinput_device *device, int accel_profile) {
    if (libinput_device_config_accel_is_available(device) != 0) {
        libinput_device_config_accel_set_profile(device, accel_profile);
    }
}

void qw_input_device_config_tap_set_drag_enabled(struct libinput_device *device, int drag) {
    libinput_device_config_tap_set_drag_enabled(device, drag);
}

void qw_input_device_config_tap_set_drag_lock_enabled(struct libinput_device *device, int drag_lock) {
    libinput_device_config_tap_set_drag_lock_enabled(device, drag_lock);
}

void qw_input_device_config_scroll_set_natural_scroll_enabled(struct libinput_device *device, int natural_scroll) {
    if (libinput_device_config_scroll_has_natural_scroll(device) != 0) {
        libinput_device_config_scroll_set_natural_scroll_enabled(device, natural_scroll);
    }
}
