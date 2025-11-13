#ifndef KEYBOARD_H
#define KEYBOARD_H

#include <wlr/types/wlr_input_device.h> // For wlr_input_device type
#include <xkbcommon/xkbcommon.h>

struct qw_server; // Forward declaration since qw_server is used but not defined here

struct qw_keyboard {
    // Private data
    struct wl_list link;
    struct qw_server *server;
    struct wlr_keyboard *wlr_keyboard;

    struct wl_listener modifiers;
    struct wl_listener key;
    struct wl_listener destroy;

    // tracking for key repeats
    bool key_pressed;
    struct wl_event_source *repeat_source;
    xkb_keysym_t repeat_keysym;
};

// Creates and sets up a new keyboard on the server from the input device
void qw_server_keyboard_new(struct qw_server *server, struct wlr_input_device *device);

void qw_keyboard_set_keymap(struct qw_keyboard *keyboard, const char *layout, const char *options,
                            const char *variant);

void qw_keyboard_set_repeat_info(struct qw_keyboard *keyboard, int kb_repeat_rate,
                                 int kb_repeat_delay);

#endif /* KEYBOARD_H */
