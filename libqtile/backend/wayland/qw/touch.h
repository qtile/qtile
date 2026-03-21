#ifndef TOUCH_H
#define TOUCH_H

#include "server.h"

struct qw_touch {
    struct qw_server *server;

    // Private data
    struct wlr_touch *wtouch;
    struct wlr_input_device *device;

    struct wl_listener down;
    struct wl_listener up;
    struct wl_listener motion;
    struct wl_listener cancel;
    struct wl_listener frame;
    struct wl_listener destroy;

    struct wl_list link;
};

// Functions to initialise and destroy touch device
void qw_touch_handle_new(struct qw_server *server, struct wlr_input_device *device);
void qw_touch_destroy(struct qw_server *server);

#endif /* TOUCH_H */
