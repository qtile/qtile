#ifndef POINTER_H
#define POINTER_H

#include "server.h"

struct qw_swipe_sequence {
    uint32_t fingers;
    char sequence[32];
    size_t length;
};

struct qw_pinch {
    double scale;
    double rotation;
    uint32_t fingers;
};

// Pointer device for handling gestures
struct qw_pointer {
    struct qw_server *server;
    struct qw_swipe_sequence *swipe_sequence;
    struct qw_pinch *pinch;

    // Private data
    struct wlr_input_device *device;
    struct wl_listener swipe_begin;
    struct wl_listener swipe_update;
    struct wl_listener swipe_end;
    struct wl_listener pinch_begin;
    struct wl_listener pinch_update;
    struct wl_listener pinch_end;
    struct wl_listener destroy;
    struct wl_list link;
};

void qw_pointer_handle_new(struct qw_server *server, struct wlr_input_device *device);

#endif /* POINTER_H */