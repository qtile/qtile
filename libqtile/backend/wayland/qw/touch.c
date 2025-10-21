#include "touch.h"
#include "output.h"
#include "util.h"
#include <linux/input-event-codes.h>

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

static void qw_touch_handle_down(struct wl_listener *listener, void *data) {
    struct qw_touch *touch = wl_container_of(listener, touch, down);
    struct wlr_touch_down_event *event = data;
    struct qw_server *server = touch->server;

    double lx, ly;
    qw_touch_absolute_position_to_screen(server, event->x, event->y, &lx, &ly);

    struct wlr_surface *surface = NULL;
    double sx, sy;
    qw_server_view_at(server, lx, ly, &surface, &sx, &sy);

    if (surface) {
        wlr_seat_touch_point_focus(server->seat, surface, event->time_msec, event->touch_id, sx,
                                   sy);
        wlr_seat_touch_notify_down(server->seat, surface, event->time_msec, event->touch_id, lx,
                                   ly);
    }
}

static void qw_touch_handle_up(struct wl_listener *listener, void *data) {
    struct qw_touch *touch = wl_container_of(listener, touch, up);
    struct wlr_touch_up_event *event = data;
    struct qw_server *server = touch->server;

    wlr_seat_touch_notify_up(server->seat, event->time_msec, event->touch_id);
    wlr_seat_touch_point_clear_focus(server->seat, event->time_msec, event->touch_id);
}

static void qw_touch_handle_motion(struct wl_listener *listener, void *data) {
    struct qw_touch *touch = wl_container_of(listener, touch, motion);
    struct wlr_touch_motion_event *event = data;
    struct qw_server *server = touch->server;

    double lx, ly;
    qw_touch_absolute_position_to_screen(server, event->x, event->y, &lx, &ly);
    wlr_seat_touch_notify_motion(server->seat, event->time_msec, event->touch_id, lx, ly);
}

static void qw_touch_handle_cancel(struct wl_listener *listener, void *data) {
    struct qw_touch *touch = wl_container_of(listener, touch, cancel);
    struct wlr_touch_cancel_event *event = data;
    UNUSED(event);
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
