#include <stdlib.h>

#include "cursor.h"
#include "output.h"
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

void qw_cursor_update_focus(struct qw_cursor *cursor, double *sx, double *sy) {
    struct wlr_seat *seat = cursor->server->seat;

    struct wlr_surface *surface = NULL;
    double tmp_sx = 0.0, tmp_sy = 0.0;

    cursor->view = qw_server_view_at(cursor->server, cursor->cursor->x, cursor->cursor->y, &surface,
                                     &tmp_sx, &tmp_sy);

    if (surface == NULL) {
        wlr_seat_pointer_clear_focus(seat);
        // Reset cursor if we're not over a surface and we're not dragging
        if (cursor->server->seat->drag == NULL) {
            wlr_cursor_set_xcursor(cursor->cursor, cursor->mgr, "default");
        }
    } else {
        struct wlr_surface *prev_surface = seat->pointer_state.focused_surface;
        if (surface != prev_surface) {
            wlr_seat_pointer_notify_enter(seat, surface, tmp_sx, tmp_sy);
        }
    }

    // Return surface-local position via output parameters, if provided
    if (sx)
        *sx = tmp_sx;
    if (sy)
        *sy = tmp_sy;
}

static void qw_cursor_process_motion(struct qw_cursor *cursor, uint32_t time) {
    struct wlr_seat *seat = cursor->server->seat;

    // Handle motion if server is in a locked state
    if (cursor->server->lock_state != QW_SESSION_LOCK_UNLOCKED) {
        if (cursor->server->lock && !wl_list_empty(&cursor->server->lock->lock->surfaces)) {
            struct wlr_session_lock_surface_v1 *lock_surface =
                wl_container_of(cursor->server->lock->lock->surfaces.next, lock_surface, link);

            // Compute surface-local coordinates
            struct qw_output *output = lock_surface->output->data;
            double sx = cursor->cursor->x - output->full_area.x;
            double sy = cursor->cursor->y - output->full_area.y;

            // Update pointer focus to the lock surface
            wlr_seat_pointer_notify_enter(seat, lock_surface->surface, sx, sy);
            wlr_seat_pointer_notify_motion(seat, time, sx, sy);
            cursor->view = NULL; // No normal view under cursor
        } else {
            // No lock surface available, clear pointer focus
            wlr_seat_pointer_clear_focus(seat);
            cursor->view = NULL;
        }

        // Still notify the server of cursor position for UI updates
        cursor->server->cursor_motion_cb(cursor->server->cb_data);
        return;
    }

    double sx = 0.0, sy = 0.0;
    qw_cursor_update_focus(cursor, &sx, &sy);

    // Notify server callback with current cursor position
    cursor->server->cursor_motion_cb(cursor->server->cb_data);

    wlr_scene_node_set_position(&cursor->server->drag_icon->node, (int)cursor->cursor->x,
                                (int)cursor->cursor->y);

    // Notify motion for focus or drag
    if (seat->pointer_state.focused_surface != NULL || seat->pointer_state.button_count > 0) {
        wlr_seat_pointer_notify_motion(seat, time, sx, sy);
    }
}

static void qw_cursor_implicit_grab_motion(struct qw_cursor *cursor, uint32_t time) {
    struct wlr_seat *seat = cursor->server->seat;

    double sx = cursor->cursor->x + cursor->implicit_grab.start_dx;
    double sy = cursor->cursor->y + cursor->implicit_grab.start_dy;
    wlr_seat_pointer_notify_motion(seat, time, sx, sy);
}

static void qw_cursor_handle_motion(struct wl_listener *listener, void *data) {
    // Handle relative pointer motion event
    struct qw_cursor *cursor = wl_container_of(listener, cursor, motion);
    struct wlr_pointer_motion_event *event = data;

    wlr_cursor_move(cursor->cursor, &event->pointer->base, event->delta_x, event->delta_y);

    if (cursor->implicit_grab.live) {
        qw_cursor_implicit_grab_motion(cursor, event->time_msec);
    } else {
        qw_cursor_process_motion(cursor, event->time_msec);
    }
}

static void qw_cursor_handle_motion_absolute(struct wl_listener *listener, void *data) {
    // Handle absolute pointer motion event
    struct qw_cursor *cursor = wl_container_of(listener, cursor, motion_absolute);
    struct wlr_pointer_motion_absolute_event *event = data;

    wlr_cursor_warp_absolute(cursor->cursor, &event->pointer->base, event->x, event->y);

    if (cursor->implicit_grab.live) {
        qw_cursor_implicit_grab_motion(cursor, event->time_msec);
    } else {
        qw_cursor_process_motion(cursor, event->time_msec);
    }
}

void qw_cursor_warp_cursor(struct qw_cursor *cursor, double x, double y) {
    wlr_cursor_warp_closest(cursor->cursor, NULL, x, y);
    qw_cursor_process_motion(cursor, 0);
}

static void qw_cursor_handle_seat_request_set(struct wl_listener *listener, void *data) {
    // Handle client request to set pointer cursor image
    struct qw_cursor *cursor = wl_container_of(listener, cursor, request_set);
    struct wlr_seat_pointer_request_set_cursor_event *event = data;

    // Only allow focused client to set cursor surface
    struct wlr_seat_client *focused_client = cursor->server->seat->pointer_state.focused_client;
    if (focused_client != event->seat_client) {
        return;
    }

    // Save the requested surface and hotspot info
    cursor->saved_surface = event->surface;
    cursor->saved_hotspot_x = event->hotspot_x;
    cursor->saved_hotspot_y = event->hotspot_y;

    if (cursor->hidden) {
        // Skip applying the cursor while hidden
        return;
    }

    wlr_cursor_set_surface(cursor->cursor, event->surface, event->hotspot_x, event->hotspot_y);
}

void qw_cursor_release_implicit_grab(struct qw_cursor *cursor, uint32_t time) {
    if (cursor->implicit_grab.live) {
        wlr_log(WLR_DEBUG, "Releasing implicit grab.");
        cursor->implicit_grab.live = false;
        // Pretend the cursor just appeared where it is.
        qw_cursor_process_motion(cursor, time);
    }
}

static void qw_cursor_create_implicit_grab(struct qw_cursor *cursor, uint32_t time) {
    struct wlr_seat *seat = cursor->server->seat;
    double x = cursor->cursor->x;
    double y = cursor->cursor->y;
    double sx = seat->pointer_state.sx;
    double sy = seat->pointer_state.sy;
    qw_cursor_release_implicit_grab(cursor, time);
    wlr_log(WLR_DEBUG, "Creating implicit grab.");

    cursor->implicit_grab.start_dx = sx - x;
    cursor->implicit_grab.start_dy = sy - y;
    cursor->implicit_grab.live = true;
}

static bool qw_cursor_process_button(struct qw_cursor *cursor, int button, bool pressed) {
    // Get current keyboard modifiers (shift, ctrl, etc)
    struct wlr_keyboard *kb = wlr_seat_get_keyboard(cursor->server->seat);
    if (!kb) {
        wlr_log(WLR_INFO, "No active keyboard found, keybinding may be missed");
        return false;
    }

    uint32_t modifiers = wlr_keyboard_get_modifiers(kb);

    // Call server's button callback with button info and modifiers
    if (cursor->server->lock_state == QW_SESSION_LOCK_UNLOCKED) {
        return cursor->server->cursor_button_cb(button, modifiers, pressed, (int)cursor->cursor->x,
                                                (int)cursor->cursor->y,
                                                cursor->server->cb_data) != 0;
    }
    return false;
}

static void qw_cursor_handle_button(struct wl_listener *listener, void *data) {
    // Handle pointer button press/release event
    struct qw_cursor *cursor = wl_container_of(listener, cursor, button);
    struct wlr_pointer_button_event *event = data;

    // Translate event button to internal code (e.g. BTN_LEFT)
    uint32_t button = qw_util_get_button_code(event->button);
    bool pressed = event->state == WL_POINTER_BUTTON_STATE_PRESSED;
    bool handled = false;
    static int pressed_button_count = 0;
    // TODO: exclusive client

    if (button != 0) {
        if (pressed) {
            pressed_button_count++;
        } else {
            pressed_button_count--;
        }

        if (cursor->implicit_grab.live) {
            wlr_seat_pointer_notify_button(cursor->server->seat, event->time_msec, event->button,
                                           event->state);
            qw_cursor_release_implicit_grab(cursor, event->time_msec);
            return;
        }

        handled = qw_cursor_process_button(cursor, button, pressed);
    }

    if (!handled) {
        struct wlr_seat *seat = cursor->server->seat;
        struct wlr_surface *surface = seat->pointer_state.focused_surface;
        struct wlr_drag *drag = cursor->server->seat->drag;

        if (pressed_button_count == 1 && surface != NULL && drag == NULL) {
            qw_cursor_create_implicit_grab(cursor, event->time_msec);
        }

        wlr_seat_pointer_notify_button(cursor->server->seat, event->time_msec, event->button,
                                       event->state);
    }
}

static void qw_cursor_handle_axis(struct wl_listener *listener, void *data) {
    // Handle scroll (axis) event
    struct qw_cursor *cursor = wl_container_of(listener, cursor, axis);
    struct wlr_pointer_axis_event *event = data;

    static double displacement = 0;
    static const uint32_t DISPLACEMENT_PER_STEP = 15; // could be configurable
    bool handled = false;
    // TODO: exclusive client

    // Determine which button this corresponds to
    uint32_t button = 0;
    if (event->orientation == WL_POINTER_AXIS_VERTICAL_SCROLL) {
        button = (event->delta > 0) ? BUTTON_SCROLL_DOWN : BUTTON_SCROLL_UP;
    } else if (event->orientation == WL_POINTER_AXIS_HORIZONTAL_SCROLL) {
        button = (event->delta > 0) ? BUTTON_SCROLL_RIGHT : BUTTON_SCROLL_LEFT;
    }

    uint32_t button_mapped = qw_util_get_button_code(button);

    if (!cursor->implicit_grab.live) {
        // If it's a physical wheel fire callback immediately if there is a discrete delta
        if (event->source == WL_POINTER_AXIS_SOURCE_WHEEL && event->delta_discrete != 0) {
            handled = qw_cursor_process_button(cursor, button_mapped, true);
            // for anything else, we're using rate limiting
        } else if (event->source != WL_POINTER_AXIS_SOURCE_WHEEL) {
            // Touchpad or smooth scroll: integrate displacement
            displacement += event->delta;

            double abs_displacement = fabs(displacement);
            if (abs_displacement >= DISPLACEMENT_PER_STEP) {
                int steps = (int)(abs_displacement / DISPLACEMENT_PER_STEP);
                displacement = fmod(displacement, DISPLACEMENT_PER_STEP);
                for (int step = 0; step < steps; step++) {
                    handled = qw_cursor_process_button(cursor, button_mapped, true);
                }
            }
        }
    }

    if (!handled) {
        // Forward axis event to seat if not handled
        wlr_seat_pointer_notify_axis(cursor->server->seat, event->time_msec, event->orientation,
                                     event->delta, event->delta_discrete, event->source,
                                     event->relative_direction);
    }
}

static void qw_cursor_handle_frame(struct wl_listener *listener, void *data) {
    UNUSED(data);
    // Handle frame event (batch end for pointer events)
    struct qw_cursor *cursor = wl_container_of(listener, cursor, frame);
    wlr_seat_pointer_notify_frame(cursor->server->seat);
}

struct qw_cursor *qw_server_cursor_create(struct qw_server *server) {
    // Allocate memory for qw_cursor
    struct qw_cursor *cursor = calloc(1, sizeof(*cursor));
    if (!cursor) {
        wlr_log(WLR_ERROR, "failed to create qw_cursor struct");
        return NULL;
    }

    cursor->server = server;
    cursor->cursor = wlr_cursor_create();
    wlr_cursor_attach_output_layout(cursor->cursor, server->output_layout);
    cursor->mgr = wlr_xcursor_manager_create(NULL, 24);

    // Setup listeners for various pointer events
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

void qw_cursor_hide(struct qw_cursor *cursor) {
    if (cursor->hidden)
        return;
    cursor->hidden = true;
    wlr_cursor_set_surface(cursor->cursor, NULL, 0, 0);
}

void qw_cursor_show(struct qw_cursor *cursor) {
    if (!cursor->hidden)
        return;
    cursor->hidden = false;

    if (cursor->saved_surface) {
        wlr_cursor_set_surface(cursor->cursor, cursor->saved_surface, cursor->saved_hotspot_x,
                               cursor->saved_hotspot_y);
    }
}
