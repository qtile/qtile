#include "keyboard.h"
#include "server.h"
#include "util.h"
#include <stdlib.h>
#include <wlr/types/wlr_keyboard.h>
#include <wlr/util/log.h>
#include <xkbcommon/xkbcommon.h>

// Called when the keyboard device is destroyed
static void qw_keyboard_handle_destroy(struct wl_listener *listener, void *data) {
    UNUSED(data);

    struct qw_keyboard *keyboard = wl_container_of(listener, keyboard, destroy);
    wl_list_remove(&keyboard->modifiers.link);
    wl_list_remove(&keyboard->key.link);
    wl_list_remove(&keyboard->destroy.link);
    wl_list_remove(&keyboard->link);
    free(keyboard);
}

// Called via a timer when key is held
static int qw_keyboard_do_repeat(void *data) {
    struct qw_keyboard *keyboard = data;
    struct qw_server *server = keyboard->server;

    // If key has been released, do nothing.
    if (!keyboard->key_pressed) {
        return 0;
    }

    // Repeat handled key: send callback
    uint32_t modifiers = wlr_keyboard_get_modifiers(keyboard->wlr_keyboard);
    server->keyboard_key_cb(keyboard->repeat_keysym, modifiers, server->cb_data);

    // Schedule next repeat according to repeat rate
    struct wlr_keyboard *wlr_kbd = keyboard->wlr_keyboard;
    int rate = wlr_kbd->repeat_info.rate;
    if (rate > 0 && keyboard->repeat_source) {
        int next = 1000 / rate;
        wl_event_source_timer_update(keyboard->repeat_source, next);
    }

    return 0;
}

// Called on each key event (press/release)
static void qw_keyboard_handle_key(struct wl_listener *listener, void *data) {
    struct qw_keyboard *keyboard = wl_container_of(listener, keyboard, key);
    struct qw_server *server = keyboard->server;
    struct wlr_keyboard_key_event *event = data;
    struct wlr_seat *seat = server->seat;

    qw_server_idle_notify_activity(server);

    // keycode offset by 8 as per evdev conventions
    uint32_t keycode = event->keycode + 8;

    int layout_index = xkb_state_key_get_layout(keyboard->wlr_keyboard->xkb_state, keycode);

    // Get the symbols for this key in the current layout and level 0
    const xkb_keysym_t *syms;
    int nsyms = xkb_keymap_key_get_syms_by_level(keyboard->wlr_keyboard->keymap, keycode,
                                                 layout_index, 0, &syms);

    bool handled = false;
    // Get current keyboard modifiers (shift, ctrl, alt, etc.)
    uint32_t modifiers = wlr_keyboard_get_modifiers(keyboard->wlr_keyboard);

    // If key is pressed...
    if (event->state == WL_KEYBOARD_KEY_STATE_PRESSED) {
        // Track key for repeat
        keyboard->key_pressed = true;

        // Call user callback for each symbol to check if handled
        for (int i = 0; i < nsyms; ++i) {
            // TODO: for efficiency maybe let c take control of the key list?
            // If callback returns 1, event is handled; no further processing needed
            if (server->keyboard_key_cb(syms[i], modifiers, server->cb_data) == 1) {
                handled = true;
                keyboard->repeat_keysym = syms[i];
                break;
            }
        }

        if (handled) {
            // Set up timer to repeat key press
            if (keyboard->repeat_source == NULL) {
                keyboard->repeat_source =
                    wl_event_loop_add_timer(server->event_loop, qw_keyboard_do_repeat, keyboard);
            }

            // Schedule the repeat timer
            if (keyboard->repeat_source != NULL) {
                struct wlr_keyboard *wlr_kbd = keyboard->wlr_keyboard;
                int delay = wlr_kbd->repeat_info.delay;
                if (delay <= 0)
                    delay = 600;
                wl_event_source_timer_update(keyboard->repeat_source, delay);
            }
        } else {
            // If not handled, forward the key event to the seat for default processing
            wlr_seat_set_keyboard(seat, keyboard->wlr_keyboard);
            wlr_seat_keyboard_notify_key(seat, event->time_msec, event->keycode, event->state);
        }

        // Remove the timer if key is released
    } else if (event->state == WL_KEYBOARD_KEY_STATE_RELEASED) {
        keyboard->key_pressed = false;
        if (keyboard->repeat_source != NULL) {
            wl_event_source_remove(keyboard->repeat_source);
            keyboard->repeat_source = NULL;
        }

        // Forward release to seat (handled or not — release must always be sent)
        wlr_seat_set_keyboard(seat, keyboard->wlr_keyboard);
        wlr_seat_keyboard_notify_key(seat, event->time_msec, event->keycode, event->state);
    }
}

// Called when keyboard modifiers change (shift, ctrl, etc.)
static void keyboard_handle_modifiers(struct wl_listener *listener, void *data) {
    UNUSED(data);

    struct qw_keyboard *keyboard = wl_container_of(listener, keyboard, modifiers);
    wlr_seat_set_keyboard(keyboard->server->seat, keyboard->wlr_keyboard);
    wlr_seat_keyboard_notify_modifiers(keyboard->server->seat, &keyboard->wlr_keyboard->modifiers);
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

    // Give keyboard input devices a reference to qw_keyboard
    device->data = keyboard;

    // Create new xkb context and default keymap
    struct xkb_context *context = xkb_context_new(XKB_CONTEXT_NO_FLAGS);
    struct xkb_keymap *keymap =
        xkb_keymap_new_from_names(context, NULL, XKB_KEYMAP_COMPILE_NO_FLAGS);

    // Assign the keymap to the keyboard and clean up refs
    wlr_keyboard_set_keymap(wlr_keyboard, keymap);
    xkb_keymap_unref(keymap);
    xkb_context_unref(context);

    wlr_keyboard_set_repeat_info(wlr_keyboard, 25, 600);

    // Setup event listeners for modifiers, key events, and destruction
    keyboard->modifiers.notify = keyboard_handle_modifiers;
    wl_signal_add(&wlr_keyboard->events.modifiers, &keyboard->modifiers);

    keyboard->key.notify = qw_keyboard_handle_key;
    wl_signal_add(&wlr_keyboard->events.key, &keyboard->key);

    keyboard->destroy.notify = qw_keyboard_handle_destroy;
    wl_signal_add(&device->events.destroy, &keyboard->destroy);

    wlr_seat_set_keyboard(server->seat, keyboard->wlr_keyboard);

    wl_list_insert(&server->keyboards, &keyboard->link);
}
