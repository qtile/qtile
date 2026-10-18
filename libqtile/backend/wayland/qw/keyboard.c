#include "keyboard.h"
#include "server.h"
#include "util.h"
#include <stdlib.h>
#include <wlr/types/wlr_keyboard.h>
#include <wlr/types/wlr_keyboard_group.h>
#include <wlr/util/log.h>
#include <xkbcommon/xkbcommon.h>

static bool qw_is_keyboard_inhibited(struct qw_server *server,
                                     struct wlr_surface *focused_surface) {
    if (focused_surface == NULL) {
        return false;
    }

    struct qw_keyboard_shortcut_inhibitor *inhibitor;
    wl_list_for_each(inhibitor, &server->shortcut_inhibitors, link) {
        if (inhibitor->wlr_inhibitor->surface == focused_surface &&
            inhibitor->wlr_inhibitor->active) {
            return true;
        }
    }

    return false;
}

// Called via a timer when key is held
static int qw_keyboard_do_repeat(void *data) {
    struct qw_server *server = data;
    struct wlr_keyboard *wlr_kbd = &server->keyboard_group->keyboard;

    // If key has been released, do nothing.
    if (!server->key_pressed) {
        return 0;
    }

    if (server->exclusive_layer != NULL) {
        // Something exclusive grabbed focus mid-repeat; stop delivering.
        if (server->repeat_source) {
            wl_event_source_remove(server->repeat_source);
            server->repeat_source = NULL;
        }
        return 0;
    }

    // Repeat handled key: send callback
    uint32_t modifiers = wlr_keyboard_get_modifiers(wlr_kbd);
    server->keyboard_key_cb(server->repeat_keysym, modifiers, server->cb_data);

    // Schedule next repeat according to repeat rate
    int rate = wlr_kbd->repeat_info.rate;
    if (rate > 0 && server->repeat_source) {
        int next = 1000 / rate;
        wl_event_source_timer_update(server->repeat_source, next);
    }

    return 0;
}

// Called on each key event (press/release) from the keyboard group
void qw_keyboard_group_handle_key(struct wl_listener *listener, void *data) {
    struct qw_server *server = wl_container_of(listener, server, keyboard_group_key);
    struct wlr_keyboard_key_event *event = data;
    struct wlr_keyboard *wlr_keyboard = &server->keyboard_group->keyboard;
    struct wlr_seat *seat = server->seat;

    qw_server_idle_notify_activity(server);

    // keycode offset by 8 as per evdev conventions
    uint32_t keycode = event->keycode + 8;

    xkb_layout_index_t layout_index = xkb_state_key_get_layout(wlr_keyboard->xkb_state, keycode);
    if (layout_index == XKB_LAYOUT_INVALID) {
        wlr_log(WLR_ERROR, "failed to get correct layout index");
        return;
    }

    // Get the symbols for this key in the current layout and level 0
    const xkb_keysym_t *syms;
    int nsyms =
        xkb_keymap_key_get_syms_by_level(wlr_keyboard->keymap, keycode, layout_index, 0, &syms);

    // Get current keyboard modifiers (shift, ctrl, alt, etc.)
    uint32_t modifiers = wlr_keyboard_get_modifiers(wlr_keyboard);

    bool handled = false;

    // Check if keyboard is inhibited
    bool inhibited = qw_is_keyboard_inhibited(server, seat->keyboard_state.focused_surface);

    // If key is pressed...
    if (event->state == WL_KEYBOARD_KEY_STATE_PRESSED) {
        // Track key for repeat
        server->key_pressed = true;

        // Don't handle presses if an exclusive layer has focus or shortcuts are inhibited
        if (server->exclusive_layer == NULL && !inhibited && server->keyboard_key_cb != NULL) {
            // Call user callback for each symbol to check if handled
            for (int i = 0; i < nsyms; ++i) {
                // If callback returns 1, event is handled; no further processing needed
                if (server->keyboard_key_cb(syms[i], modifiers, server->cb_data) == 1) {
                    handled = true;
                    server->repeat_keysym = syms[i];
                    break;
                }
            }
        }

        if (handled) {
            // Set up timer to repeat key press
            if (server->repeat_source == NULL) {
                server->repeat_source =
                    wl_event_loop_add_timer(server->event_loop, qw_keyboard_do_repeat, server);
            }

            // Schedule the repeat timer
            if (server->repeat_source != NULL) {
                int delay = wlr_keyboard->repeat_info.delay;
                if (delay <= 0)
                    delay = 600;
                wl_event_source_timer_update(server->repeat_source, delay);
            }
        } else {
            // If not handled, forward the key event to the seat for default processing
            wlr_seat_set_keyboard(seat, wlr_keyboard);
            wlr_seat_keyboard_notify_key(seat, event->time_msec, event->keycode, event->state);
        }

        // Remove the timer if key is released
    } else if (event->state == WL_KEYBOARD_KEY_STATE_RELEASED) {
        server->key_pressed = false;
        if (server->repeat_source != NULL) {
            wl_event_source_remove(server->repeat_source);
            server->repeat_source = NULL;
        }

        // Forward release to seat (handled or not — release must always be sent)
        wlr_seat_set_keyboard(seat, wlr_keyboard);
        wlr_seat_keyboard_notify_key(seat, event->time_msec, event->keycode, event->state);
    }
}

// Called when keyboard group modifiers change (shift, ctrl, etc.)
void qw_keyboard_group_handle_modifiers(struct wl_listener *listener, void *data) {
    UNUSED(data);
    struct qw_server *server = wl_container_of(listener, server, keyboard_group_modifiers);
    struct wlr_keyboard *wlr_keyboard = &server->keyboard_group->keyboard;

    wlr_seat_set_keyboard(server->seat, wlr_keyboard);
    wlr_seat_keyboard_notify_modifiers(server->seat, &wlr_keyboard->modifiers);
}

// Called when the keyboard device is destroyed
static void qw_keyboard_handle_destroy(struct wl_listener *listener, void *data) {
    UNUSED(data);

    struct qw_keyboard *keyboard = wl_container_of(listener, keyboard, destroy);
    struct qw_server *server = keyboard->server;

    if (server->keyboard_group != NULL) {
        wlr_keyboard_group_remove_keyboard(server->keyboard_group, keyboard->wlr_keyboard);
    }

    // A held key may have been on the removed device; don't leave repeat armed.
    if (server->repeat_source != NULL) {
        wl_event_source_remove(server->repeat_source);
        server->repeat_source = NULL;
    }
    server->key_pressed = false;

    wl_list_remove(&keyboard->destroy.link);
    wl_list_remove(&keyboard->link);

    free(keyboard);
}

void qw_keyboard_set_keymap(struct qw_keyboard *keyboard, const char *layout, const char *options,
                            const char *variant) {
    struct xkb_context *context = xkb_context_new(XKB_CONTEXT_NO_FLAGS);
    if (context == NULL) {
        wlr_log(WLR_ERROR, "failed to create xkb context");
        return;
    }

    struct xkb_rule_names names = {.layout = layout, .options = options, .variant = variant};

    struct xkb_keymap *keymap =
        xkb_keymap_new_from_names(context, &names, XKB_KEYMAP_COMPILE_NO_FLAGS);

    if (keymap == NULL) {
        wlr_log(WLR_ERROR, "failed to create xkb keymap for layout='%s' variant='%s' options='%s'",
                layout ? layout : "", variant ? variant : "", options ? options : "");
        xkb_context_unref(context);
        return;
    }

    wlr_keyboard_set_keymap(keyboard->wlr_keyboard, keymap);
    xkb_keymap_unref(keymap);
    xkb_context_unref(context);
}

void qw_keyboard_set_repeat_info(struct qw_keyboard *keyboard, int kb_repeat_rate,
                                 int kb_repeat_delay) {
    wlr_keyboard_set_repeat_info(keyboard->wlr_keyboard, kb_repeat_rate, kb_repeat_delay);

    // Key repeat is driven from the group keyboard, so it needs the same settings
    if (keyboard->server->keyboard_group != NULL) {
        wlr_keyboard_set_repeat_info(&keyboard->server->keyboard_group->keyboard, kb_repeat_rate,
                                     kb_repeat_delay);
    }
}

// Creates and initializes a new keyboard input device attached to the server
void qw_server_keyboard_new(struct qw_server *server, struct wlr_input_device *device) {
    struct qw_keyboard *keyboard = calloc(1, sizeof(*keyboard));
    if (!keyboard) {
        wlr_log(WLR_ERROR, "failed to create qw_keyboard struct");
        return;
    }

    struct wlr_keyboard *wlr_keyboard = wlr_keyboard_from_input_device(device);

    if (wlr_keyboard == NULL) {
        wlr_log(WLR_ERROR, "failed to get keyboard from input device");
        free(keyboard);
        return;
    }

    keyboard->server = server;
    keyboard->wlr_keyboard = wlr_keyboard;

    // Match the device keymap to the group keymap before adding it.
    // If the group already has a keymap, apply it to the physical keyboard.
    if (server->keyboard_group->keyboard.keymap != NULL) {
        wlr_keyboard_set_keymap(wlr_keyboard, server->keyboard_group->keyboard.keymap);
    } else {
        // Fallback: compile a default keymap if group doesn't have one yet
        struct xkb_context *context = xkb_context_new(XKB_CONTEXT_NO_FLAGS);
        if (context == NULL) {
            wlr_log(WLR_ERROR, "failed to create xkb context");
            free(keyboard);
            return;
        }

        struct xkb_keymap *keymap =
            xkb_keymap_new_from_names(context, NULL, XKB_KEYMAP_COMPILE_NO_FLAGS);
        if (keymap == NULL) {
            wlr_log(WLR_ERROR, "failed to create xkb keymap");
            xkb_context_unref(context);
            free(keyboard);
            return;
        }

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

void qw_keyboard_group_destroy(struct qw_server *server) {
    if (server->repeat_source != NULL) {
        wl_event_source_remove(server->repeat_source);
        server->repeat_source = NULL;
    }
    server->key_pressed = false;

    if (server->keyboard_group != NULL) {
        wlr_keyboard_group_destroy(server->keyboard_group);
        server->keyboard_group = NULL;
    }
}
