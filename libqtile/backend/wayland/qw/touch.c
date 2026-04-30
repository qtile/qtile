#include "touch.h"
#include "cursor.h"
#include "output.h"
#include "util.h"
#include <linux/input-event-codes.h>

static struct qw_touch_point *qw_touch_get_point(struct qw_touch *touch, int32_t id) {
    struct qw_touch_point *point;
    wl_list_for_each(point, &touch->points, link) {
        if (point->id == id) {
            return point;
        }
    }
    return NULL;
}

static void qw_touch_add_point(struct qw_touch *touch, int32_t id, struct wlr_surface *surface) {
    struct qw_touch_point *point = calloc(1, sizeof(*point));
    point->id = id;
    point->surface = surface;
    wl_list_insert(&touch->points, &point->link);
}

static void qw_touch_remove_point(struct qw_touch *touch, int32_t id) {
    struct qw_touch_point *point, *tmp;
    wl_list_for_each_safe(point, tmp, &touch->points, link) {
        if (point->id == id) {
            wl_list_remove(&point->link);
            free(point);
            return;
        }
    }
}

static void qw_touch_handle_down(struct wl_listener *listener, void *data) {
    struct qw_touch *touch = wl_container_of(listener, touch, down);
    struct wlr_touch_down_event *event = data;
    struct qw_server *server = touch->server;

    double lx, ly;
    wlr_cursor_absolute_to_layout_coords(server->cursor->cursor, touch->device, event->x, event->y,
                                         &lx, &ly);

    struct wlr_surface *surface = NULL;
    double sx, sy;
    qw_server_view_at(server, lx, ly, &surface, &sx, &sy);

    if (surface) {
        qw_touch_add_point(touch, event->touch_id, surface);
        wlr_seat_touch_notify_down(server->seat, surface, event->time_msec, event->touch_id, sx,
                                   sy);
    }
}

static void qw_touch_handle_up(struct wl_listener *listener, void *data) {
    struct qw_touch *touch = wl_container_of(listener, touch, up);
    struct wlr_touch_up_event *event = data;
    struct qw_server *server = touch->server;

    qw_touch_remove_point(touch, event->touch_id);

    wlr_seat_touch_notify_up(server->seat, event->time_msec, event->touch_id);
}

static void qw_touch_handle_motion(struct wl_listener *listener, void *data) {
    struct qw_touch *touch = wl_container_of(listener, touch, motion);
    struct wlr_touch_motion_event *event = data;
    struct qw_server *server = touch->server;

    struct qw_touch_point *point = qw_touch_get_point(touch, event->touch_id);

    if (point == NULL || point->surface == NULL) {
        return;
    }

    double lx, ly;
    wlr_cursor_absolute_to_layout_coords(server->cursor->cursor, touch->device, event->x, event->y,
                                         &lx, &ly);

    double sx, sy;
    qw_server_view_at(server, lx, ly, NULL, &sx, &sy);

    wlr_seat_touch_notify_motion(server->seat, event->time_msec, event->touch_id, sx, sy);
}

static void qw_touch_handle_cancel(struct wl_listener *listener, void *data) {
    struct qw_touch *touch = wl_container_of(listener, touch, cancel);
    struct wlr_touch_cancel_event *event = data;
    UNUSED(event);
}

static void qw_touch_handle_frame(struct wl_listener *listener, void *data) {
    UNUSED(data);
    struct qw_touch *touch = wl_container_of(listener, touch, frame);
    struct qw_server *server = touch->server;

    wlr_seat_touch_notify_frame(server->seat);
}

static void qw_touch_handle_destroy(struct wl_listener *listener, void *data) {
    UNUSED(data);
    struct qw_touch *touch = wl_container_of(listener, touch, destroy);

    struct qw_touch_point *point, *tmp;
    wl_list_for_each_safe(point, tmp, &touch->points, link) {
        wl_list_remove(&point->link);
        free(point);
    }

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

bool qw_touch_map_output(struct qw_touch *touch, const char *output_name, bool map_all_outputs) {
    struct qw_server *server = touch->server;
    struct wlr_cursor *cursor = server->cursor->cursor;
    struct wlr_input_device *device = touch->device;

    if (map_all_outputs) {
        wlr_cursor_map_input_to_output(cursor, device, NULL);
        return true;
    }

    struct qw_output *output;
    wl_list_for_each(output, &server->outputs, link) {
        if (strcmp(output->wlr_output->name, output_name) == 0) {
            wlr_cursor_map_input_to_output(cursor, device, output->wlr_output);
            return true;
        }
    }

    return false;
}

void qw_touch_handle_new(struct qw_server *server, struct wlr_input_device *device) {
    struct wlr_touch *wtouch = wlr_touch_from_input_device(device);

    struct qw_touch *touch = calloc(1, sizeof(*touch));
    touch->device = device;
    touch->wtouch = wtouch;
    touch->server = server;

    device->data = touch;

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

    wl_list_init(&touch->points);

    wl_list_insert(&server->touches, &touch->link);
}
