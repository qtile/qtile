#include <server.h>
#include <wlr/types/wlr_seat.h>
#include <wlr/util/log.h>

#include "cursor.h"
#include "input-device.h"
#include "keyboard.h"
#include "util.h"

// Called when the device is destroyed
static void qw_input_device_handle_destroy(struct wl_listener *listener, void *data) {
    UNUSED(data);

    struct qw_input_device *input_device = wl_container_of(listener, input_device, destroy);
    wl_list_remove(&input_device->destroy.link);
    wl_list_remove(&input_device->link);
    free(input_device);
}

void qw_server_input_device_new(struct qw_server *server, struct wlr_input_device *device) {
    struct qw_input_device *input_device = calloc(1, sizeof(*input_device));
    if (input_device == NULL) {
        wlr_log(WLR_ERROR, "failed to create qw_input_device struct");
        return;
    }
    device->data = input_device;

    input_device->server = server;
    input_device->device = device;

    input_device->destroy.notify = qw_input_device_handle_destroy;
    wl_signal_add(&device->events.destroy, &input_device->destroy);

    wl_list_insert(&server->input_devices, &input_device->link);

    server->on_input_device_added_cb(server->cb_data);

    switch (device->type) {
    case WLR_INPUT_DEVICE_KEYBOARD:
        qw_server_keyboard_new(server, device);

        // If there's still an active lock then we need to direct
        // the keyboard to the lock surface.
        if (server->lock != NULL) {
            qw_session_lock_focus_first_lock_surface(server);
        }

        break;
    case WLR_INPUT_DEVICE_POINTER:
        // Attach a new pointer device to the server's cursor
        wlr_cursor_attach_input_device(server->cursor->cursor, device);
        break;
    default:
        break;
    }
    uint32_t caps = WL_SEAT_CAPABILITY_POINTER;
    if (!wl_list_empty(&server->keyboards)) {
        caps |= WL_SEAT_CAPABILITY_KEYBOARD;
    }
    wlr_seat_set_capabilities(server->seat, caps);
}

struct libinput_device *qw_input_device_get_libinput_handle(struct qw_input_device *input_device) {
    if (!wlr_input_device_is_libinput(input_device->device)) {
        return NULL;
    }
    return wlr_libinput_get_device_handle(input_device->device);
}

struct qw_keyboard *qw_input_device_get_keyboard(struct qw_input_device *input_device) {
    struct qw_keyboard *keyboard = (struct qw_keyboard *)(input_device->device->data);
    return keyboard;
}

bool qw_input_device_is_touchpad(struct qw_input_device *input_device) {
    struct libinput_device *device = qw_input_device_get_libinput_handle(input_device);
    return device && libinput_device_config_tap_get_finger_count(device) > 0;
}

void qw_input_device_config_accel_set_profile(struct libinput_device *device, int accel_profile) {
    if (libinput_device_config_accel_is_available(device)) {
        libinput_device_config_accel_set_profile(device, accel_profile);
    }
}

void qw_input_device_config_accel_set_speed(struct libinput_device *device, double pointer_accel) {
    if (libinput_device_config_accel_is_available(device)) {
        libinput_device_config_accel_set_speed(device, pointer_accel);
    }
}

void qw_input_device_config_click_set_method(struct libinput_device *device, int click_method) {
    libinput_device_config_click_set_method(device, click_method);
}

void qw_input_device_config_tap_set_drag_enabled(struct libinput_device *device, int drag) {
    libinput_device_config_tap_set_drag_enabled(device, drag);
}

void qw_input_device_config_tap_set_drag_lock_enabled(struct libinput_device *device,
                                                      int drag_lock) {
    libinput_device_config_tap_set_drag_lock_enabled(device, drag_lock);
}

void qw_input_device_config_tap_set_enabled(struct libinput_device *device, int tap) {
    if (libinput_device_config_tap_get_finger_count(device) > 1) {
        libinput_device_config_tap_set_enabled(device, tap);
    }
}

void qw_input_device_config_tap_set_button_map(struct libinput_device *device, int tap_button_map) {
    if (libinput_device_config_tap_get_finger_count(device) > 1) {
        libinput_device_config_tap_set_button_map(device, tap_button_map);
    }
}

void qw_input_device_config_scroll_set_natural_scroll_enabled(struct libinput_device *device,
                                                              int natural_scroll) {
    if (libinput_device_config_scroll_has_natural_scroll(device) != 0) {
        libinput_device_config_scroll_set_natural_scroll_enabled(device, natural_scroll);
    }
}

void qw_input_device_config_scroll_set_method(struct libinput_device *device, int scroll_method) {
    libinput_device_config_scroll_set_method(device, scroll_method);
}

void qw_input_device_config_scroll_set_button(struct libinput_device *device, int scroll_button) {
    if ((int)libinput_device_config_scroll_get_method(device) ==
        LIBINPUT_CONFIG_SCROLL_ON_BUTTON_DOWN) {
        libinput_device_config_scroll_set_button(device, scroll_button);
    }
}

void qw_input_device_config_dwt_set_enabled(struct libinput_device *device, int dwt) {
    if (libinput_device_config_dwt_is_available(device)) {
        libinput_device_config_dwt_set_enabled(device, dwt);
    }
}

void qw_input_device_config_left_handed_set(struct libinput_device *device, int left_handed) {
    if (libinput_device_config_left_handed_is_available(device)) {
        libinput_device_config_left_handed_set(device, left_handed);
    }
}

void qw_input_device_config_middle_emulation_set_enabled(struct libinput_device *device,
                                                         int middle_emulation) {
    libinput_device_config_middle_emulation_set_enabled(device, middle_emulation);
}
