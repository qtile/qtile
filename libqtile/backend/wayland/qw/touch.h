#ifndef TOUCH_H
#define TOUCH_H

#include "server.h"

struct qw_touch_point {
    int32_t id;

    // Private data
    struct wlr_surface *surface;
    struct wl_list link;
};

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

    struct wl_list points; // qw_touch_point
    struct wl_list link;
};

// Functions to initialise and destroy touch device
void qw_touch_handle_new(struct qw_server *server, struct wlr_input_device *device);
void qw_touch_destroy(struct qw_server *server);

bool qw_touch_map_output(struct qw_touch *touch, const char *output_name, bool map_all_outputs);

#endif /* TOUCH_H */
