#ifndef KEYBOARD_H
#define KEYBOARD_H

#include <wlr/types/wlr_input_device.h>

struct qw_server;

struct qw_keyboard {
    struct wl_list link;
    struct qw_server *server;
    struct wlr_keyboard *wlr_keyboard;

    struct wl_listener modifiers;
    struct wl_listener key;
    struct wl_listener destroy;
};

void qw_server_keyboard_new(struct qw_server *server, struct wlr_input_device *device);

#endif /* KEYBOARD_H */
