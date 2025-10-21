#ifndef TOUCH_H
#define TOUCH_H

#include "server.h"

static const double TAP_MAX_DURATION = 200;
static const double TAP_MAX_DISTANCE = 0.02;
static const double PINCH_THRESHOLD = 0.05;
static const double ROTATE_THRESHOLD = (M_PI / 12.0);
static const double SWIPE_MIN_DISTANCE = 0.05;

struct qw_touch_point {
    int32_t id;
    double x, y;
    double start_x, start_y;
    uint32_t start_time_msec;
    uint32_t time_msec;

    // Private data
    struct wl_list link;
};

struct qw_gesture_state {
    bool active;
    size_t finger_count;
    double start_distance;
    double start_angle;
    double last_distance;
    double last_angle;
    double accumulated_rotation;
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

    struct wl_list points;
    struct qw_gesture_state gesture;

    struct wl_list link;
};

enum qw_swipe_dir {
    QW_SWIPE_LEFT,
    QW_SWIPE_RIGHT,
    QW_SWIPE_UP,
    QW_SWIPE_DOWN,
};

// Functions to initialise and destroy touch device
void qw_touch_handle_new(struct qw_server *server, struct wlr_input_device *device);
void qw_touch_destroy(struct qw_server *server);

// /* Gesture handlers (to implement in compositor) */
// void qw_handle_tap(struct qw_server *server, double x, double y);
// void qw_handle_pinch_or_rotate(struct qw_server *server, double pinch, double rotate, double
// total_rotation); void qw_handle_swipe(struct qw_server *server, size_t fingers, enum qw_swipe_dir
// dir, double distance);

#endif /* TOUCH_H */
