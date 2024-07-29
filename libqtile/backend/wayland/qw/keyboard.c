#include "keyboard.h"
#include "server.h"
#include "xkbcommon/xkbcommon.h"
#include <stdlib.h>
#include <wlr/types/wlr_keyboard.h>
#include <wlr/util/log.h>

static void qw_keyboard_handle_destroy(struct wl_listener *listener, void *data) {
    struct qw_keyboard *keyboard = wl_container_of(listener, keyboard, destroy);
    wl_list_remove(&keyboard->modifiers.link);
    wl_list_remove(&keyboard->key.link);
    wl_list_remove(&keyboard->destroy.link);
    wl_list_remove(&keyboard->link);
    free(keyboard);
}

static void qw_keyboard_handle_key(struct wl_listener *listener, void *data) {
    struct qw_keyboard *keyboard = wl_container_of(listener, keyboard, key);
    struct qw_server *server = keyboard->server;
    struct wlr_keyboard_key_event *event = data;
    struct wlr_seat *seat = server->seat;

    uint32_t keycode = event->keycode + 8;
    const xkb_keysym_t *syms;
    int layout_index = xkb_state_key_get_layout(keyboard->wlr_keyboard->xkb_state, keycode);
    int nsyms = xkb_keymap_key_get_syms_by_level(keyboard->wlr_keyboard->keymap, keycode,
                                                 layout_index, 0, &syms);

    bool handled = false;
    uint32_t modifiers = wlr_keyboard_get_modifiers(keyboard->wlr_keyboard);
    if (event->state == WL_KEYBOARD_KEY_STATE_PRESSED) {
        for (int i = 0; i < nsyms; ++i) {
            // TODO: for efficiency maybe let c take control of the key list?
            if (server->keyboard_key_cb(syms[i], modifiers, server->cb_data) == 1) {
                handled = true;
                break;
            }
        }
    }

    if (!handled) {
        wlr_seat_set_keyboard(seat, keyboard->wlr_keyboard);
        wlr_seat_keyboard_notify_key(seat, event->time_msec, event->keycode, event->state);
    }
}

static void keyboard_handle_modifiers(struct wl_listener *listener, void *data) {
    struct qw_keyboard *keyboard = wl_container_of(listener, keyboard, modifiers);
    wlr_seat_set_keyboard(keyboard->server->seat, keyboard->wlr_keyboard);
    wlr_seat_keyboard_notify_modifiers(keyboard->server->seat, &keyboard->wlr_keyboard->modifiers);
}

void qw_server_keyboard_new(struct qw_server *server, struct wlr_input_device *device) {
    struct qw_keyboard *keyboard = calloc(1, sizeof(*keyboard));
    if (!keyboard) {
        wlr_log(WLR_ERROR, "failed to create qw_keyboard struct");
        return;
    }

    struct wlr_keyboard *wlr_keyboard = wlr_keyboard_from_input_device(device);

    keyboard->server = server;
    keyboard->wlr_keyboard = wlr_keyboard;

    struct xkb_context *context = xkb_context_new(XKB_CONTEXT_NO_FLAGS);
    struct xkb_keymap *keymap =
        xkb_keymap_new_from_names(context, NULL, XKB_KEYMAP_COMPILE_NO_FLAGS);

    wlr_keyboard_set_keymap(wlr_keyboard, keymap);
    xkb_keymap_unref(keymap);
    xkb_context_unref(context);
    wlr_keyboard_set_repeat_info(wlr_keyboard, 25, 600);

    keyboard->modifiers.notify = keyboard_handle_modifiers;
    wl_signal_add(&wlr_keyboard->events.modifiers, &keyboard->modifiers);
    keyboard->key.notify = qw_keyboard_handle_key;
    wl_signal_add(&wlr_keyboard->events.key, &keyboard->key);
    keyboard->destroy.notify = qw_keyboard_handle_destroy;
    wl_signal_add(&device->events.destroy, &keyboard->destroy);

    wlr_seat_set_keyboard(server->seat, keyboard->wlr_keyboard);

    wl_list_insert(&server->keyboards, &keyboard->link);
}
