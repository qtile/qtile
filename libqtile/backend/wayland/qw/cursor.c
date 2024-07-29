#include <stdlib.h>

#include "cursor.h"
#include "server.h"
#include "util.h"
#include "wayland-util.h"

void qw_cursor_destroy(struct qw_cursor *cursor) {
    wl_list_remove(&cursor->request_set.link);
    wl_list_remove(&cursor->axis.link);
    wl_list_remove(&cursor->motion.link);
    wl_list_remove(&cursor->motion_absolute.link);
    wl_list_remove(&cursor->frame.link);
    wl_list_remove(&cursor->button.link);
    wlr_xcursor_manager_destroy(cursor->mgr);
    free(cursor);
}

static void qw_cursor_process_motion(struct qw_cursor *cursor, uint32_t time) {
    cursor->server->cursor_motion_cb((int)cursor->cursor->x, (int)cursor->cursor->y,
                                     cursor->server->cb_data);
    double sx, sy;
    struct wlr_seat *seat = cursor->server->seat;
    struct wlr_surface *surface = NULL;
    struct qw_view *view =
        qw_server_view_at(cursor->server, cursor->cursor->x, cursor->cursor->y, &surface, &sx, &sy);
    if (!view) {
        wlr_cursor_set_xcursor(cursor->cursor, cursor->mgr, "default");
    }
    if (surface) {
        wlr_seat_pointer_notify_enter(seat, surface, sx, sy);
        wlr_seat_pointer_notify_motion(seat, time, sx, sy);
    } else {
        wlr_seat_pointer_clear_focus(seat);
    }
}

static void qw_cursor_handle_motion(struct wl_listener *listener, void *data) {
    struct qw_cursor *cursor = wl_container_of(listener, cursor, motion);
    struct wlr_pointer_motion_event *event = data;

    wlr_cursor_move(cursor->cursor, &event->pointer->base, event->delta_x, event->delta_y);
    qw_cursor_process_motion(cursor, event->time_msec);
}

static void qw_cursor_handle_motion_absolute(struct wl_listener *listener, void *data) {
    struct qw_cursor *cursor = wl_container_of(listener, cursor, motion_absolute);
    struct wlr_pointer_motion_absolute_event *event = data;
    wlr_cursor_warp_absolute(cursor->cursor, &event->pointer->base, event->x, event->y);
    qw_cursor_process_motion(cursor, event->time_msec);
}

static void qw_cursor_handle_seat_request_set(struct wl_listener *listener, void *data) {
    struct qw_cursor *cursor = wl_container_of(listener, cursor, request_set);
    struct wlr_seat_pointer_request_set_cursor_event *event = data;
    struct wlr_seat_client *focused_client = cursor->server->seat->pointer_state.focused_client;
    if (focused_client == event->seat_client) {
        wlr_cursor_set_surface(cursor->cursor, event->surface, event->hotspot_x, event->hotspot_y);
    }
}

static bool qw_cursor_process_button(struct qw_cursor *cursor, int button, bool pressed) {
    struct wlr_keyboard *kb = wlr_seat_get_keyboard(cursor->server->seat);
    if (!kb) {
        wlr_log(WLR_INFO, "No active keyboard found, keybinding may be missed");
        return false;
    }
    uint32_t modifiers = wlr_keyboard_get_modifiers(kb);
    return cursor->server->cursor_button_cb(button, modifiers, pressed, (int)cursor->cursor->x,
                                            (int)cursor->cursor->y, cursor->server->cb_data) != 0;
}

static void qw_cursor_handle_button(struct wl_listener *listener, void *data) {
    struct qw_cursor *cursor = wl_container_of(listener, cursor, button);
    struct wlr_pointer_button_event *event = data;
    uint32_t button = qw_util_get_button_code(event->button);
    bool handled = false;
    if (button != 0) {
        bool pressed = event->state == WL_POINTER_BUTTON_STATE_PRESSED;
        handled = qw_cursor_process_button(cursor, button, pressed);
    }
    if (!handled) {
        wlr_seat_pointer_notify_button(cursor->server->seat, event->time_msec, event->button,
                                       event->state);
    }
}

static void qw_cursor_handle_axis(struct wl_listener *listener, void *data) {
    struct qw_cursor *cursor = wl_container_of(listener, cursor, axis);
    struct wlr_pointer_axis_event *event = data;

    bool handled = false;
    // TODO: exclusive client and implicit grab
    if (event->delta != 0) {
        uint32_t button = 0;
        if (event->orientation == WL_POINTER_AXIS_VERTICAL_SCROLL) {
            button = (0 < event->delta) ? BUTTON_SCROLL_DOWN : BUTTON_SCROLL_UP;
        } else {
            button = (0 < event->delta) ? BUTTON_SCROLL_RIGHT : BUTTON_SCROLL_LEFT;
        }
        handled = qw_cursor_process_button(cursor, button, true);
    }

    if (!handled) {
        wlr_seat_pointer_notify_axis(cursor->server->seat, event->time_msec, event->orientation,
                                     event->delta, event->delta_discrete, event->source,
                                     event->relative_direction);
    }
}

static void qw_cursor_handle_frame(struct wl_listener *listener, void *data) {
    struct qw_cursor *cursor = wl_container_of(listener, cursor, frame);
    wlr_seat_pointer_notify_frame(cursor->server->seat);
}

struct qw_cursor *qw_server_cursor_create(struct qw_server *server) {
    struct qw_cursor *cursor = calloc(1, sizeof(*cursor));
    if (!cursor) {
        wlr_log(WLR_ERROR, "failed to create qw_cursor struct");
        return NULL;
    }
    cursor->server = server;
    cursor->cursor = wlr_cursor_create();
    wlr_cursor_attach_output_layout(cursor->cursor, server->output_layout);
    cursor->mgr = wlr_xcursor_manager_create(NULL, 24);

    cursor->request_set.notify = qw_cursor_handle_seat_request_set;
    wl_signal_add(&server->seat->events.request_set_cursor, &cursor->request_set);
    cursor->motion.notify = qw_cursor_handle_motion;
    wl_signal_add(&cursor->cursor->events.motion, &cursor->motion);
    cursor->motion_absolute.notify = qw_cursor_handle_motion_absolute;
    wl_signal_add(&cursor->cursor->events.motion_absolute, &cursor->motion_absolute);
    cursor->axis.notify = qw_cursor_handle_axis;
    wl_signal_add(&cursor->cursor->events.axis, &cursor->axis);
    cursor->frame.notify = qw_cursor_handle_frame;
    wl_signal_add(&cursor->cursor->events.frame, &cursor->frame);
    cursor->button.notify = qw_cursor_handle_button;
    wl_signal_add(&cursor->cursor->events.button, &cursor->button);

    return cursor;
}
