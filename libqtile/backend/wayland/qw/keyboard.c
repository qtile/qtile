#include "keyboard.h"
#include "server.h"
#include "util.h"
#include <stdlib.h>
#include <wlr/types/wlr_keyboard.h>
#include <wlr/types/wlr_keyboard_group.h>
#include <wlr/util/log.h>
#include <xkbcommon/xkbcommon.h>

void qw_keyboard_group_handle_key(struct wl_listener *listener, void *data) {
    struct qw_server *server = wl_container_of(listener, server, keyboard_group_key);
    struct wlr_keyboard_key_event *event = data;
    struct wlr_keyboard *wlr_keyboard = &server->keyboard_group->keyboard;
    struct wlr_seat *seat = server->seat;

    qw_server_idle_notify_activity(server);

    uint32_t keycode = event->keycode + 8;
    int layout_index = xkb_state_key_get_layout(wlr_keyboard->xkb_state, keycode);

    const xkb_keysym_t *syms;
    int nsyms =
        xkb_keymap_key_get_syms_by_level(wlr_keyboard->keymap, keycode, layout_index, 0, &syms);

    uint32_t modifiers = wlr_keyboard_get_modifiers(wlr_keyboard);

    wlr_log(WLR_ERROR, "[DEBUG] KEY EVENT: keycode=%u, state=%s, nsyms=%d, mods=0x%x",
            event->keycode, event->state == WL_KEYBOARD_KEY_STATE_PRESSED ? "PRESSED" : "RELEASED",
            nsyms, modifiers);

    bool handled = false;

    if (event->state == WL_KEYBOARD_KEY_STATE_PRESSED) {
        if (server->exclusive_layer == NULL && server->keyboard_key_cb != NULL) {
            for (int i = 0; i < nsyms; ++i) {
                if (server->keyboard_key_cb(syms[i], modifiers, server->cb_data) == 1) {
                    handled = true;
                    break;
                }
            }
        }

        if (!handled) {
            wlr_seat_set_keyboard(seat, wlr_keyboard);
            wlr_seat_keyboard_notify_key(seat, event->time_msec, event->keycode, event->state);
        }
    } else if (event->state == WL_KEYBOARD_KEY_STATE_RELEASED) {
        // Forward release to seat (handled or not — release must always be sent)
        wlr_seat_set_keyboard(seat, wlr_keyboard);
        wlr_seat_keyboard_notify_key(seat, event->time_msec, event->keycode, event->state);
    }
}

// Called when keyboard modifiers change (shift, ctrl, etc.)
void qw_keyboard_group_handle_modifiers(struct wl_listener *listener, void *data) {
    UNUSED(data);
    struct qw_server *server = wl_container_of(listener, server, keyboard_group_modifiers);
    struct wlr_keyboard *wlr_keyboard = &server->keyboard_group->keyboard;

    wlr_seat_set_keyboard(server->seat, wlr_keyboard);
    wlr_seat_keyboard_notify_modifiers(server->seat, &wlr_keyboard->modifiers);
}

static void qw_keyboard_handle_destroy(struct wl_listener *listener, void *data) {
    UNUSED(data);

    struct qw_keyboard *keyboard = wl_container_of(listener, keyboard, destroy);

    if (keyboard->server->keyboard_group != NULL) {
        wlr_keyboard_group_remove_keyboard(keyboard->server->keyboard_group,
                                           keyboard->wlr_keyboard);
    }

    wl_list_remove(&keyboard->destroy.link);
    wl_list_remove(&keyboard->link);

    free(keyboard);
}

void qw_keyboard_set_keymap(struct qw_keyboard *keyboard, const char *layout, const char *options,
                            const char *variant) {
    struct xkb_context *context = xkb_context_new(XKB_CONTEXT_NO_FLAGS);

    struct xkb_rule_names names = {.layout = layout, .options = options, .variant = variant};

    struct xkb_keymap *keymap =
        xkb_keymap_new_from_names(context, &names, XKB_KEYMAP_COMPILE_NO_FLAGS);

    wlr_keyboard_set_keymap(keyboard->wlr_keyboard, keymap);
    xkb_keymap_unref(keymap);
    xkb_context_unref(context);
}

void qw_keyboard_set_repeat_info(struct qw_keyboard *keyboard, int kb_repeat_rate,
                                 int kb_repeat_delay) {
    wlr_keyboard_set_repeat_info(keyboard->wlr_keyboard, kb_repeat_rate, kb_repeat_delay);
}

// Creates and initializes a new keyboard input device attached to the server
void qw_server_keyboard_new(struct qw_server *server, struct wlr_input_device *device) {
    struct qw_keyboard *keyboard = calloc(1, sizeof(*keyboard));
    if (!keyboard) {
        wlr_log(WLR_ERROR, "failed to create qw_keyboard struct");
        return;
    }

    struct wlr_keyboard *wlr_keyboard = wlr_keyboard_from_input_device(device);

    keyboard->server = server;
    keyboard->wlr_keyboard = wlr_keyboard;

    // Match the device keymap to the group keymap before adding it.
    // If the group already has a keymap, apply it to the physical keyboard.
    if (server->keyboard_group->keyboard.keymap != NULL) {
        wlr_keyboard_set_keymap(wlr_keyboard, server->keyboard_group->keyboard.keymap);
    } else {
        // Fallback: compile a default keymap if group doesn't have one yet
        struct xkb_context *context = xkb_context_new(XKB_CONTEXT_NO_FLAGS);
        struct xkb_keymap *keymap =
            xkb_keymap_new_from_names(context, NULL, XKB_KEYMAP_COMPILE_NO_FLAGS);
        wlr_keyboard_set_keymap(wlr_keyboard, keymap);
        xkb_keymap_unref(keymap);
        xkb_context_unref(context);
    }

    if (!wlr_keyboard_group_add_keyboard(server->keyboard_group, wlr_keyboard)) {
        wlr_log(WLR_ERROR, "Failed to add keyboard to keyboard group");
        free(keyboard);
        return;
    }

    keyboard->destroy.notify = qw_keyboard_handle_destroy;
    wl_signal_add(&device->events.destroy, &keyboard->destroy);

    wl_list_insert(&server->keyboards, &keyboard->link);
}
