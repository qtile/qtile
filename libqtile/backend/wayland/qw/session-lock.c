/*
 * Session Lock Implementation (wlroots protocol: wlr_session_lock_v1)
 * see: https://wayland.app/protocols/ext-session-lock-v1
 */
#include "session-lock.h"
#include "cursor.h"
#include "output.h"
#include "server.h"
#include "util.h"
#include <wayland-util.h>
#include <wlr/types/wlr_session_lock_v1.h>

void qw_session_lock_restore_focus(struct qw_server *server) {
    bool success = server->focus_current_window_cb(server->cb_data);

    if (!success) {
        wlr_log(WLR_ERROR, "Could not restore focus after unlocking session.");
    }
}

// Focus the first available lock surface
// Useful if one lock surface disappears (e.g. output disconnect)
// but others remain.
void qw_session_lock_focus_first_lock_surface(struct qw_server *server) {
    struct wlr_seat *seat = server->seat;
    struct wlr_keyboard *keyboard = wlr_seat_get_keyboard(seat);
    struct wlr_session_lock_surface_v1 *surface;
    surface = wl_container_of(server->lock->lock->surfaces.next, surface, link);

    if (keyboard != NULL) {
        // Redirect keyboard input to the chosen lock surface
        wlr_seat_keyboard_notify_enter(seat, surface->surface, keyboard->keycodes,
                                       keyboard->num_keycodes, &keyboard->modifiers);
    }
    if (server->cursor != NULL) {
        // Redirect pointer focus as well
        wlr_seat_pointer_notify_enter(seat, surface->surface, 0, 0);
    }
}

void qw_session_lock_output_create_blanking_rects(struct qw_output *output) {
    struct qw_server *server = output->server;

    // Get colour of the blanking rects depending on lock state
    const float *rect_color = (server->lock_state != QW_SESSION_LOCK_CRASHED)
                                  ? QW_SESSION_LOCK_BLANKING_RECT_LOCKED
                                  : QW_SESSION_LOCK_BLANKING_RECT_CRASHED;

    int o_width, o_height;
    wlr_output_effective_resolution(output->wlr_output, &o_width, &o_height);
    struct wlr_scene_rect *blanking_rect = wlr_scene_rect_create(
        server->scene_windows_layers[LAYER_LOCK], o_width, o_height, rect_color);
    wlr_scene_node_set_position(&blanking_rect->node, output->x, output->y);

    // Make sure blanking rects are below any lock surfaces
    wlr_scene_node_lower_to_bottom(&blanking_rect->node);

    output->blanking_rect = blanking_rect;
}

// When output changes, we need to reposition and resize any lock surface and
// blanking rect attached to that output.
// Ensures lock surfaces always cover the full output geometry.
void qw_session_lock_output_change(struct qw_output *output) {
    int x, y, w, h;
    x = output->full_area.x;
    y = output->full_area.y;
    w = output->full_area.width;
    h = output->full_area.height;

    if (output->lock_surface != NULL) {
        struct wlr_scene_tree *scene_tree = output->lock_surface->surface->data;
        wlr_scene_node_set_position(&scene_tree->node, x, y);
        wlr_session_lock_surface_v1_configure(output->lock_surface, w, h);
    }

    if (output->blanking_rect != NULL) {
        wlr_scene_node_set_position(&output->blanking_rect->node, x, y);
        wlr_scene_rect_set_size(output->blanking_rect, w, h);
    }
}

// If the lock client crashes we change the blanking rect colours to let
// the user know.
// This visually indicates "something went wrong" instead of showing unlocked windows.
void qw_session_lock_crashed_update_rects(struct qw_server *server) {
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
    UNUSED(data);
    struct qw_session_lock_surface *sls = wl_container_of(listener, sls, surface_destroy);
    struct qw_server *server = sls->server;

    if (server->lock != NULL && server->lock->lock != NULL) {
        struct wlr_session_lock_surface_v1 *lock_surface = sls->lock_surface;
        if (lock_surface->link.prev != NULL && lock_surface->link.next != NULL) {
            wl_list_remove(&lock_surface->link);
            wl_list_init(&lock_surface->link);
        }

        // Focus shifts if other surfaces remain
        if (!wl_list_empty(&server->lock->lock->surfaces)) {
            qw_session_lock_focus_first_lock_surface(server);
        }
    }

    wl_list_remove(&sls->surface_destroy.link);
    free(sls);
}

void qw_session_lock_destroy(struct qw_session_lock *session_lock, bool unlock) {
    struct qw_server *server = session_lock->server;
    struct wlr_seat *seat = server->seat;
    // Always clear focus when lock is destroyed
    wlr_seat_keyboard_notify_clear_focus(seat);
    wlr_seat_pointer_clear_focus(seat);

    if (server->lock_state == QW_SESSION_LOCK_LOCKED && unlock) {
        // Lock was explicitly unlocked → disable lock layer, restore focus
        wlr_scene_node_set_enabled(&session_lock->server->scene_windows_layers[LAYER_LOCK]->node,
                                   false);

        server->lock_state = QW_SESSION_LOCK_UNLOCKED;
        qw_session_lock_restore_focus(server);

    } else if (server->lock_state == QW_SESSION_LOCK_LOCKED && !unlock) {
        wlr_log(WLR_ERROR, "Session lock client vanished without unlocking.");
        server->lock_state = QW_SESSION_LOCK_CRASHED;

        // Bring blanking rects to top so contents stay hidden
        qw_session_lock_crashed_update_rects(server);
    }

    wl_list_remove(&session_lock->new_surface.link);
    wl_list_remove(&session_lock->unlock.link);
    wl_list_remove(&session_lock->destroy.link);

    wlr_scene_node_destroy(&session_lock->scene->node);
    session_lock->server->lock = NULL;
    free(session_lock);
}

void qw_session_lock_handle_unlock(struct wl_listener *listener, void *data) {
    UNUSED(data);
    struct qw_session_lock *lock = wl_container_of(listener, lock, unlock);
    struct qw_server *server = lock->server;
    // Unlock event from client → destroy lock with unlock=true
    qw_session_lock_destroy(lock, true);
    server->on_session_lock_cb(false, server->cb_data);
}

void qw_session_lock_handle_destroy(struct wl_listener *listener, void *data) {
    UNUSED(data);
    struct qw_session_lock *lock = wl_container_of(listener, lock, destroy);
    // Lock object destroyed without unlock → destroy lock with unlock=false
    // This leaves the compositor in a "crashed lock" state.
    qw_session_lock_destroy(lock, false);
}

void qw_session_lock_handle_new_surface(struct wl_listener *listener, void *data) {
    struct qw_session_lock *lock = wl_container_of(listener, lock, new_surface);
    struct wlr_session_lock_surface_v1 *lock_surface = data;
    struct qw_output *output = lock_surface->output->data;

    struct wlr_scene_tree *scene_tree = lock_surface->surface->data =
        wlr_scene_subsurface_tree_create(lock->scene, lock_surface->surface);
    output->lock_surface = lock_surface;

    // Make sure lock surface is at the top.
    wlr_scene_node_raise_to_top(&scene_tree->node);

    // Configure the lock surface to the size and position of the output
    int o_width, o_height;
    wlr_output_effective_resolution(output->wlr_output, &o_width, &o_height);
    wlr_scene_node_set_position(&scene_tree->node, output->x, output->y);
    wlr_session_lock_surface_v1_configure(lock_surface, output->full_area.width,
                                          output->full_area.height);

    // If this is the current output, redirect keyboard + pointer input to it
    // The qw_server_handle_new_input function will also redirect keyboard to a lock
    // surface if a keyboard appears after the lock surface.
    struct wlr_keyboard *keyboard = wlr_seat_get_keyboard(lock->server->seat);
    struct wlr_output *current_output = qw_server_get_current_output(lock->server);
    if (keyboard && output->wlr_output == current_output) {
        wlr_seat_keyboard_notify_enter(lock->server->seat, lock_surface->surface,
                                       keyboard->keycodes, keyboard->num_keycodes,
                                       &keyboard->modifiers);
        wlr_seat_pointer_notify_enter(lock->server->seat, lock_surface->surface, 0, 0);
    }

    struct qw_session_lock_surface *sls = calloc(1, sizeof(*sls));
    sls->server = lock->server;
    sls->lock_surface = lock_surface;

    sls->surface_destroy.notify = qw_session_lock_surface_handle_destroy;
    wl_signal_add(&lock_surface->surface->events.destroy, &sls->surface_destroy);
}

void qw_session_lock_handle_new(struct wl_listener *listener, void *data) {
    struct qw_server *server = wl_container_of(listener, server, new_session_lock);
    struct wlr_session_lock_v1 *session_lock = data;

    // Reject any incoming lock request if already locked or crashed
    if (server->lock_state != QW_SESSION_LOCK_UNLOCKED) {
        wlr_session_lock_v1_destroy(session_lock);
        return;
    }

    qw_cursor_release_implicit_grab(server->cursor, 0);

    // Enable the LOCK layer to show blanking rects
    wlr_scene_node_set_enabled(&server->scene_windows_layers[LAYER_LOCK]->node, true);

    struct qw_session_lock *lock = calloc(1, sizeof(*lock));
    if (lock == NULL) {
        wlr_session_lock_v1_destroy(session_lock);
        return;
    }

    lock->scene = wlr_scene_tree_create(server->scene_windows_layers[LAYER_LOCK]);
    lock->server = server;
    lock->lock = session_lock;
    server->lock = lock;
    server->lock_state = QW_SESSION_LOCK_LOCKED;

    lock->new_surface.notify = qw_session_lock_handle_new_surface;
    wl_signal_add(&session_lock->events.new_surface, &lock->new_surface);

    lock->destroy.notify = qw_session_lock_handle_destroy;
    wl_signal_add(&session_lock->events.destroy, &lock->destroy);

    lock->unlock.notify = qw_session_lock_handle_unlock;
    wl_signal_add(&session_lock->events.unlock, &lock->unlock);

    // Inform client it is now locked
    wlr_session_lock_v1_send_locked(session_lock);

    server->on_session_lock_cb(true, server->cb_data);
}

void qw_session_lock_init(struct qw_server *server) {
    server->lock_state = QW_SESSION_LOCK_UNLOCKED;
    server->lock_manager = wlr_session_lock_manager_v1_create(server->display);
    server->new_session_lock.notify = qw_session_lock_handle_new;
    wl_signal_add(&server->lock_manager->events.new_lock, &server->new_session_lock);
    wlr_scene_node_set_enabled(&server->scene_windows_layers[LAYER_LOCK]->node, false);
}
