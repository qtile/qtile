#include "session-lock.h"
#include "output.h"
#include "server.h"
#include <wayland-util.h>
#include <wlr/types/wlr_session_lock_v1.h>

void qw_session_lock_restore_focus(struct qw_server *server) {
    wlr_log(WLR_ERROR, "SESSION LOCK - RESTORE FOCUS");
    // To do:
    // - Move focus to client window
    // - Restore keyboard focus?
    // - Restore pointer focus?
    // qw_cursor_process_motion(server->cursor, 0);
}

// Focus the first available lock surface
void qw_session_lock_focus_first_lock_surface(struct qw_server *server) {
    struct wlr_seat *seat = server->seat;
    struct wlr_keyboard *keyboard = wlr_seat_get_keyboard(seat);
    struct wlr_session_lock_surface_v1 *surface;
    surface = wl_container_of(server->lock->surfaces.next, surface, link);

    if (keyboard != NULL) {
        wlr_seat_keyboard_notify_enter(seat, surface->surface, keyboard->keycodes,
                                       keyboard->num_keycodes, &keyboard->modifiers);
    }
    if (server->cursor != NULL) {
        wlr_log(WLR_ERROR, "SESSION LOCK - CURSOR FOCUS");
        wlr_seat_pointer_notify_enter(seat, surface->surface, 0, 0);
    }
}

// When output changes, we need to reposition and resize any lock surface and
// blanking rect attached to that output
void qw_session_lock_output_change(struct qw_output *output) {
    int x, y, w, h;
    x = output->full_area.x;
    y = output->full_area.y;
    w = output->full_area.width;
    h = output->full_area.height;

    if (output->lock_surface != NULL) {
        wlr_log(WLR_INFO, "SESSION LOCK - OUTPUT - UPDATING LOCK SURFACE");
        struct wlr_scene_tree *scene_tree = output->lock_surface->surface->data;
        wlr_scene_node_set_position(&scene_tree->node, x, y);
        wlr_session_lock_surface_v1_configure(output->lock_surface, w, h);
    }

    if (output->blanking_rect != NULL) {
        wlr_log(WLR_INFO, "SESSION LOCK - OUTPUT - UPDATING BLANKING RECT (%d,%d %dx%d)", x, y, w,
                h);
        wlr_scene_node_set_position(&output->blanking_rect->node, x, y);
        wlr_scene_rect_set_size(output->blanking_rect, w, h);
    }
}

// If an output is destroyed, remove its blanking rect
void qw_session_lock_output_destroy(struct qw_output *output) {
    if (output->blanking_rect != NULL) {
        wlr_scene_node_destroy(&output->blanking_rect->node);
    }
}

// If the lock client crashes we change the blanking rect colours to let
// the user know
void qw_session_lock_crashed_update_rects(struct qw_server *server) {
    wlr_log(WLR_INFO, "SESSION LOCK - Blanking rect crashed");
    struct qw_output *o;
    wl_list_for_each(o, &server->outputs, link) {
        if (!o->wlr_output || !o->wlr_output->enabled) {
            continue;
        }
        struct wlr_scene_rect *old_rect = o->blanking_rect;
        int width, height;
        wlr_output_effective_resolution(o->wlr_output, &width, &height);
        struct wlr_scene_rect *blanking_rect =
            wlr_scene_rect_create(server->scene_windows_layers[LAYER_LOCK], width, height,
                                  QW_SESSION_LOCK_BLANKING_RECT_CRASHED);
        wlr_scene_node_set_position(&blanking_rect->node, o->x, o->y);
        o->blanking_rect = blanking_rect;
        if (old_rect != NULL) {
            wlr_scene_node_destroy(&old_rect->node);
        }
    }
}

void qw_session_lock_surface_handle_destroy(struct wl_listener *listener, void *data) {
    struct qw_output *output = wl_container_of(listener, output, destroy_lock_surface);
    wlr_log(WLR_ERROR, "SESSION LOCK - HANDLE SURFACE DESTROY at %d,%d", output->x, output->y);
    struct qw_server *server = output->server;
    wlr_log(WLR_ERROR, "SESSION LOCK - LOCK STATE: %d", server->lock_state);

    output->lock_surface = NULL;
    wl_list_remove(&output->destroy_lock_surface.link);
    wlr_log(WLR_INFO, "Destroy link removed");

    if (server->lock_state != QW_SESSION_LOCK_UNLOCKED) {
        wlr_log(WLR_ERROR, "SESSION LOCK - NOT UNLOCKED");
        if (server->lock != NULL && wl_list_length(&server->lock->surfaces) > 1) {
            // We've lost a lock surface but there are other lock surfaces
            // available (e.g. one output has been disconnected while we're locked)
            // so we move focus to first available lock surface
            qw_session_lock_focus_first_lock_surface(server);
        } else {
            // No more lock surfaces but we're still locked - client has crashed
            wlr_log(WLR_ERROR, "SESSION LOCK - CRAAAAASH!");
            server->lock_state = QW_SESSION_LOCK_CRASHED;
            qw_session_lock_crashed_update_rects(server);
            struct wlr_seat *seat = server->seat;
            wlr_seat_keyboard_clear_focus(seat);
            wlr_seat_pointer_clear_focus(seat);
        }
    }
    // We shouldn't need to do anything if the server is unlocked as this
    // should have already been handled in qw_session_lock_destroy
}

void qw_session_lock_destroy(struct qw_session_lock *session_lock, bool unlock) {
    wlr_log(WLR_INFO, "SESSION LOCK - destroy lock (unlock %d)", unlock);
    struct qw_server *server = session_lock->server;
    struct wlr_seat *seat = server->seat;
    // Stop focusing
    wlr_log(WLR_INFO, "SESSION LOCK - stop focus keyboard");
    wlr_seat_keyboard_notify_clear_focus(seat);
    wlr_log(WLR_INFO, "SESSION LOCK - stop focus pointer");
    wlr_seat_pointer_clear_focus(seat);

    if (server->lock_state == QW_SESSION_LOCK_LOCKED && unlock) {
        // Hide the lock layer
        wlr_log(WLR_INFO, "SESSION LOCK - hide blanking rects");
        wlr_scene_node_set_enabled(&session_lock->server->scene_windows_layers[LAYER_LOCK]->node,
                                   false);

        qw_session_lock_restore_focus(server);

        wlr_log(WLR_INFO, "SESSION LOCK - mark unlocked");
        server->lock_state = QW_SESSION_LOCK_UNLOCKED;
    }
    wlr_log(WLR_ERROR, "Destroying lock.");

    wlr_log(WLR_INFO, "Removing new surface link");
    wl_list_remove(&session_lock->new_surface.link);
    wlr_log(WLR_INFO, "Removing unlock link");
    wl_list_remove(&session_lock->unlock.link);
    wlr_log(WLR_INFO, "Removing destroy link");
    wl_list_remove(&session_lock->destroy.link);

    wlr_scene_node_destroy(&session_lock->scene->node);
    session_lock->server->lock = NULL;
    free(session_lock);
}

void qw_session_lock_handle_unlock(struct wl_listener *listener, void *data) {
    wlr_log(WLR_ERROR, "SESSION LOCK - HANDLE UNLOCK");
    struct qw_session_lock *lock = wl_container_of(listener, lock, unlock);
    // Destroy the lock and unlock the system
    qw_session_lock_destroy(lock, true);
}

void qw_session_lock_handle_destroy(struct wl_listener *listener, void *data) {
    wlr_log(WLR_ERROR, "SESSION LOCK - DESTROY");
    struct qw_session_lock *lock = wl_container_of(listener, lock, destroy);
    // Destroy the lock but leave the system locked as we've not
    // had a valid unlock event
    qw_session_lock_destroy(lock, false);
}

void qw_session_lock_handle_new_surface(struct wl_listener *listener, void *data) {
    wlr_log(WLR_ERROR, "SESSION LOCK - NEW SURFACE");
    struct qw_session_lock *lock = wl_container_of(listener, lock, new_surface);
    struct wlr_session_lock_surface_v1 *lock_surface = data;
    struct qw_output *output = lock_surface->output->data;

    struct wlr_scene_tree *scene_tree = lock_surface->surface->data =
        wlr_scene_subsurface_tree_create(lock->scene, lock_surface->surface);
    output->lock_surface = lock_surface;

    // Configure the lock surface to the size and position of the output
    int o_width, o_height;
    wlr_output_effective_resolution(output->wlr_output, &o_width, &o_height);
    wlr_scene_node_set_position(&scene_tree->node, output->x, output->y);
    wlr_session_lock_surface_v1_configure(lock_surface, output->full_area.width,
                                          output->full_area.height);

    // Focus the surface on the current screen
    struct wlr_keyboard *keyboard = wlr_seat_get_keyboard(lock->server->seat);
    if (keyboard && output->wlr_output == lock->server->current_output) {
        wlr_log(WLR_ERROR, "SESSION LOCK - NEW SURFACE - KEYBOARD + POINTER REDIRECT");
        wlr_seat_keyboard_notify_enter(lock->server->seat, lock_surface->surface,
                                       keyboard->keycodes, keyboard->num_keycodes,
                                       &keyboard->modifiers);
        wlr_seat_pointer_notify_enter(lock->server->seat, lock_surface->surface, 0, 0);
    }

    // Listen for destroy events on this lock surface
    output->destroy_lock_surface.notify = qw_session_lock_surface_handle_destroy;
    wl_signal_add(&lock_surface->events.destroy, &output->destroy_lock_surface);
}

void qw_session_lock_handle_new(struct wl_listener *listener, void *data) {
    struct qw_server *server = wl_container_of(listener, server, new_session_lock);
    struct wlr_session_lock_v1 *session_lock = data;

    wlr_log(WLR_ERROR, "SESSION LOCK - HANDLE NEW LOCK");

    // Reject any income lock request if we're not unlocked
    if (server->lock_state != QW_SESSION_LOCK_UNLOCKED) {
        wlr_session_lock_v1_destroy(session_lock);
        return;
    }

    // Enable the LOCK layer to show blanking rects
    wlr_scene_node_set_enabled(&server->scene_windows_layers[LAYER_LOCK]->node, true);

    // Block focus of other windows

    // Stop input in other windows

    struct qw_session_lock *lock = calloc(1, sizeof(*lock));
    if (lock == NULL) {
        wlr_log(WLR_ERROR, "Could not allocate memory for session lock.");
        wlr_session_lock_v1_destroy(session_lock);
        return;
    }

    lock->scene = wlr_scene_tree_create(server->scene_windows_layers[LAYER_LOCK]);
    lock->server = server;
    lock->lock = session_lock;
    server->lock = session_lock;
    server->lock_state = QW_SESSION_LOCK_LOCKED;

    lock->new_surface.notify = qw_session_lock_handle_new_surface;
    wl_signal_add(&session_lock->events.new_surface, &lock->new_surface);

    lock->destroy.notify = qw_session_lock_handle_destroy;
    wl_signal_add(&session_lock->events.destroy, &lock->destroy);

    lock->unlock.notify = qw_session_lock_handle_unlock;
    wl_signal_add(&session_lock->events.unlock, &lock->unlock);

    wlr_session_lock_v1_send_locked(session_lock);
}
