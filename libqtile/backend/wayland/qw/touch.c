#include "touch.h"
#include "output.h"
#include "util.h"
#include <linux/input-event-codes.h>

#include <math.h>
#include <stdlib.h>

static void qw_touch_absolute_position_to_screen(struct qw_server *server, double x, double y,
                                                 double *lx, double *ly) {
    struct qw_output *output, *tmp;
    wl_list_for_each_safe(output, tmp, &server->outputs, link) {
        *lx = x * output->wlr_output->width;
        *ly = y * output->wlr_output->height;
        return;
    }
    *lx = *ly = 0;
}

static double distance_between(struct qw_touch_point *p1, struct qw_touch_point *p2) {
    double dx = p1->x - p2->x;
    double dy = p1->y - p2->y;
    return sqrt(dx * dx + dy * dy);
}

static double angle_between(struct qw_touch_point *p1, struct qw_touch_point *p2) {
    return atan2(p2->y - p1->y, p2->x - p1->x);
}

static double angle_delta(double prev, double current) {
    double delta = current - prev;
    while (delta > M_PI)
        delta -= 2 * M_PI;
    while (delta < -M_PI)
        delta += 2 * M_PI;
    return delta;
}

static enum qw_swipe_dir swipe_direction_from_angle(double angle) {
    if (angle > -M_PI_4 && angle <= M_PI_4)
        return QW_SWIPE_RIGHT;
    else if (angle > M_PI_4 && angle <= 3 * M_PI_4)
        return QW_SWIPE_DOWN;
    else if (angle <= -M_PI_4 && angle > -3 * M_PI_4)
        return QW_SWIPE_UP;
    else
        return QW_SWIPE_LEFT;
}

static struct qw_touch_point *qw_touch_point_get(struct qw_touch *touch, int32_t id) {
    struct qw_touch_point *p;
    wl_list_for_each(p, &touch->points, link) {
        if (p->id == id)
            return p;
    }
    return NULL;
}

static void qw_touch_point_remove(struct qw_touch_point *p) {
    wl_list_remove(&p->link);
    free(p);
}

static void qw_gesture_reset(struct qw_touch *touch) {
    touch->gesture.active = false;
    touch->gesture.finger_count = 0;
    touch->gesture.start_distance = 0;
    touch->gesture.start_angle = 0;
    touch->gesture.accumulated_rotation = 0;
}

void qw_handle_tap(struct qw_server *server, double x, double y) {
    wlr_log(WLR_DEBUG, "Tap detected at %.3f, %.3f", x, y);
}

void qw_handle_pinch_or_rotate(struct qw_server *server, double pinch, double rotate,
                               double total_rotation) {
    if (fabs(pinch) > 0.0)
        wlr_log(WLR_DEBUG, "Pinch end: Δdistance=%.3f", pinch);
    if (fabs(rotate) > 0.0)
        wlr_log(WLR_DEBUG, "Rotate end: rotation=%.3f radians", rotate);
}

static void qw_handle_swipe(struct qw_server *server, size_t fingers, enum qw_swipe_dir dir,
                            double distance) {
    const char *dir_str = (dir == QW_SWIPE_LEFT)    ? "left"
                          : (dir == QW_SWIPE_RIGHT) ? "right"
                          : (dir == QW_SWIPE_UP)    ? "up"
                                                    : "down";

    wlr_log(WLR_DEBUG, "%zu-finger swipe %s (distance=%.3f)", fingers, dir_str, distance);
    // TODO: integrate with Qtile actions here
}

static void handle_touch_down(struct wl_listener *listener, void *data) {
    struct qw_touch *touch = wl_container_of(listener, touch, down);
    struct wlr_touch_down_event *event = data;

    struct qw_touch_point *p = calloc(1, sizeof(*p));
    if (p == NULL) {
        return;
    }

    p->id = event->touch_id;
    p->x = event->x;
    p->y = event->y;
    p->start_x = event->x;
    p->start_y = event->y;
    p->start_time_msec = event->time_msec;
    p->time_msec = event->time_msec;
    wl_list_insert(&touch->points, &p->link);

    int num_touches = wl_list_length(&touch->points);

    double lx, ly;
    qw_touch_absolute_position_to_screen(server, event->x, event->y, &lx, &ly);

    if (num_touches == 1) {
        struct wlr_surface *surface = NULL;
        double sx, sy;
        qw_server_view_at(touch->server, lx, ly, &surface, &sx, &sy);

        if (surface) {
            wlr_seat_touch_point_focus(server->seat, surface, event->time_msec, event->touch_id, sx,
                                       sy);
            wlr_seat_touch_notify_down(server->seat, surface, event->time_msec, event->touch_id, sx,
                                       sy);
            touch->touched_surface = surface;
            touch->origin_sx = lx - sx;
            touch->origin_sy - ly - sy;
        } else {
            touch->touched_surface = NULL;
            touch->origin_sx = 0;
            touch->origin_sy = 0;
        }

    } else if (num_touches == 2) {
        struct qw_touch_point *p1 = wl_container_of(touch->points.next, p1, link);
        struct qw_touch_point *p2 = wl_container_of(p1->link.next, p2, link);

        touch->gesture.active = true;
        touch->gesture.finger_count = 2;
        touch->gesture.start_distance = distance_between(p1, p2);
        touch->gesture.start_angle = angle_between(p1, p2);
        touch->gesture.last_distance = touch->gesture.start_distance;
        touch->gesture.last_angle = touch->gesture.start_angle;
        touch->gesture.accumulated_rotation = 0;
    } else {
        touch->gesture.finger_count = wl_list_length(&touch->points);
    }
}

// static void qw_touch_handle_down(struct wl_listener *listener, void *data) {
//     struct qw_touch *touch = wl_container_of(listener, touch, down);
//     struct wlr_touch_down_event *event = data;
//     struct qw_server *server = touch->server;

//     double lx, ly;
//     qw_touch_absolute_position_to_screen(server, event->x, event->y, &lx, &ly);

//     struct wlr_surface *surface = NULL;
//     double sx, sy;
//     qw_server_view_at(server, lx, ly, &surface, &sx, &sy);

//     if (surface) {
//         wlr_seat_touch_point_focus(server->seat, surface, event->time_msec, event->touch_id, sx,
//                                    sy);
//         wlr_seat_touch_notify_down(server->seat, surface, event->time_msec, event->touch_id, lx,
//                                    ly);
//     }
// }

static void handle_touch_up(struct wl_listener *listener, void *data) {
    struct qw_touch *touch = wl_container_of(listener, touch, up);
    struct wlr_touch_up_event *event = data;

    struct qw_touch_point *point = qw_touch_point_get(touch, event->touch_id);
    if (point == NULL) {
        return;
    }

    uint32_t duration = event->time_msec - point->start_time_msec;
    double dx = point->x - point->start_x;
    double dy = point->y - point->start_y;
    double distance = sqrt(dx * dx + dy * dy);

    wlr_seat_touch_notify_up(touch->server->seat, event->time_msec, point->id);
    // wlr_seat_touch_point_clear_focus(server->seat, event->time_msec, event->touch_id);
    qw_touch_point_remove(point);

    if (wl_list_empty(&touch->points)) {
        size_t fingers = touch->gesture.finger_count;

        if (fingers >= 2 && touch->gesture.active) {
            double dist_delta = touch->gesture.last_distance - touch->gesture.start_distance;
            double rotation = touch->gesture.accumulated_rotation;

            if (fabs(dist_delta) > PINCH_THRESHOLD) {
                qw_handle_pinch_or_rotate(touch->server, dist_delta, 0, 0);
            } else if (fabs(rotation) > ROTATE_THRESHOLD) {
                qw_handle_pinch_or_rotate(touch->server, 0, rotation, rotation);
            }
        } else if (fingers == 1) {
            if (distance > SWIPE_MIN_DISTANCE) {
                double angle = atan2(dy, dx);
                enum qw_swipe_dir dir = swipe_direction_from_angle(angle);
                qw_handle_swipe(touch->server, 1, dir, distance);
            } else if (distance < TAP_MAX_DISTANCE && duration < TAP_MAX_DURATION) {
                qw_handle_tap(touch->server, point->x, point->y);
            }
        } else if (fingers >= 3) {
            // Multi-finger swipe
            double avg_dx = 0.0, avg_dy = 0.0;
            struct qw_touch_point *p;
            wl_list_for_each(p, &touch->points, link) {
                avg_dx += (p->x - p->start_x);
                avg_dy += (p->y - p->start_y);
            }
            avg_dx /= fingers;
            avg_dy /= fingers;

            double avg_dist = sqrt(avg_dx * avg_dx + avg_dy * avg_dy);
            if (avg_dist > SWIPE_MIN_DISTANCE) {
                enum qw_swipe_dir dir = swipe_direction_from_angle(atan2(avg_dy, avg_dx));
                qw_handle_swipe(touch->server, fingers, dir, avg_dist);
            }
        }

        qw_gesture_reset(touch);
    }
}

static void handle_touch_motion(struct wl_listener *listener, void *data) {
    struct qw_touch *touch = wl_container_of(listener, touch, motion);
    struct wlr_touch_motion_event *event = data;

    struct qw_touch_point *point = qw_touch_point_get(touch, event->touch_id);
    if (!point)
        return;

    point->x = event->x;
    point->y = event->y;
    point->time_msec = event->time_msec;

    if (touch->gesture.active && wl_list_length(&touch->points) >= 2) {
        struct qw_touch_point *p1 = wl_container_of(touch->points.next, p1, link);
        struct qw_touch_point *p2 = wl_container_of(p1->link.next, p2, link);

        double angle_now = angle_between(p1, p2);
        double dist_now = distance_between(p1, p2);
        double d_angle = angle_delta(touch->gesture.last_angle, angle_now);

        touch->gesture.accumulated_rotation += d_angle;
        touch->gesture.last_angle = angle_now;
        touch->gesture.last_distance = dist_now;
    }

    wlr_seat_touch_notify_motion(touch->server->seat, event->time_msec, point->id, point->x,
                                 point->y);
}

// static void qw_touch_handle_motion(struct wl_listener *listener, void *data) {
//     struct qw_touch *touch = wl_container_of(listener, touch, motion);
//     struct wlr_touch_motion_event *event = data;
//     struct qw_server *server = touch->server;

//     double lx, ly;
//     qw_touch_absolute_position_to_screen(server, event->x, event->y, &lx, &ly);
//     wlr_seat_touch_notify_motion(server->seat, event->time_msec, event->touch_id, lx, ly);
// }

static void qw_touch_handle_cancel(struct wl_listener *listener, void *data) {
    struct qw_touch *touch = wl_container_of(listener, touch, cancel);
    struct wlr_touch_cancel_event *event = data;
    UNUSED(event);
    // TODO: cancel gestures? Send cancellation?
}

static void qw_touch_handle_frame(struct wl_listener *listener, void *data) {
    UNUSED(data);
    struct qw_touch *touch = wl_container_of(listener, touch, frame);
}

static void qw_touch_handle_destroy(struct wl_listener *listener, void *data) {
    UNUSED(data);
    struct qw_touch *touch = wl_container_of(listener, touch, destroy);

    wl_list_remove(&touch->link);
    wl_list_remove(&touch->down.link);
    wl_list_remove(&touch->up.link);
    wl_list_remove(&touch->motion.link);
    wl_list_remove(&touch->cancel.link);
    wl_list_remove(&touch->frame.link);
    wl_list_remove(&touch->destroy.link);

    free(touch);
}

void qw_touch_destroy(struct qw_server *server) {
    struct qw_touch *touch, *tmp;
    wl_list_for_each_safe(touch, tmp, &server->touches, link) {
        touch->destroy.notify(&touch->destroy, NULL);
    }
}

void qw_touch_handle_new(struct qw_server *server, struct wlr_input_device *device) {
    struct wlr_touch *wtouch = wlr_touch_from_input_device(device);

    struct qw_touch *touch = calloc(1, sizeof(*touch));
    touch->device = device;
    touch->wtouch = wtouch;
    touch->server = server;

    touch->down.notify = qw_touch_handle_down;
    wl_signal_add(&wtouch->events.down, &touch->down);

    touch->up.notify = qw_touch_handle_up;
    wl_signal_add(&wtouch->events.up, &touch->up);

    touch->motion.notify = qw_touch_handle_motion;
    wl_signal_add(&wtouch->events.motion, &touch->motion);

    touch->cancel.notify = qw_touch_handle_cancel;
    wl_signal_add(&wtouch->events.cancel, &touch->cancel);

    touch->frame.notify = qw_touch_handle_frame;
    wl_signal_add(&wtouch->events.frame, &touch->frame);

    touch->destroy.notify = qw_touch_handle_destroy;
    wl_signal_add(&wtouch->base.events.destroy, &touch->destroy);

    wl_list_insert(&server->touches, &touch->link);
}
