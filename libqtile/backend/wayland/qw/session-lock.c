/*
 * Session Lock Implementation (wlroots protocol: wlr_session_lock_v1)
 *
 * This file implements the wlroots session lock protocol, which allows a
 * compositor to "lock" the session (typically for login/lock screens).
 *
 * Acknowledgements:
 *   Portions of the logic and design were informed by dwl's implementation,
 *   which was used as a reference when structuring this code.
 *
 * Locking Flow (Detailed):
 *
 * 1. New lock request:
 *    - When a client requests a new session lock,
 *      qw_session_lock_handle_new() is called.
 *    - If the compositor is currently unlocked, a lock is created and the
 *      LAYER_LOCK scene is enabled to show blanking rects. Input to normal
 *      windows is blocked at this stage.
 *
 * 2. New lock surfaces:
 *    - For each output, the lock client will create a surface.
 *      qw_session_lock_handle_new_surface() sets up the lock surface:
 *        • Positions and resizes it to cover the output
 *        • Sets keyboard/pointer focus if appropriate
 *        • Hooks a destroy listener (qw_session_lock_surface_handle_destroy)
 *
 * 3. Maintaining lock surfaces:
 *    - If an output is resized/reconfigured:
 *        qw_session_lock_output_change() repositions and resizes lock surfaces
 *        and blanking rects to continue covering the outputs fully.
 *    - If an output is destroyed:
 *        qw_session_lock_output_destroy() cleans up its blanking rect.
 *
 * 4. Lock surface lifecycle:
 *    - If a lock surface is destroyed:
 *        qw_session_lock_surface_handle_destroy() checks if other lock surfaces
 *        remain. If not, and the session is still locked, the lock is considered
 *        crashed and qw_session_lock_crashed_update_rects() is called to show
 *        an error-colored blanking rect.
 *
 * 5. Unlocking:
 *    - If the client sends an unlock event:
 *        qw_session_lock_handle_unlock() destroys the lock via
 *        qw_session_lock_destroy(unlock = true).
 *        This hides the lock layer, restores input focus via
 *        qw_session_lock_restore_focus(), and marks the server unlocked.
 *
 * 6. Forced destroy:
 *    - If the lock is destroyed without a valid unlock (e.g. client exit):
 *        qw_session_lock_handle_destroy() calls qw_session_lock_destroy(unlock = false),
 *        keeping the compositor locked (crashed state).
 *
 * Key Functions:
 *    - qw_session_lock_handle_new()            : Entry point when a new lock is requested
 *    - qw_session_lock_handle_new_surface()    : Sets up lock surfaces per output
 *    - qw_session_lock_output_change()         : Keeps lock surfaces in sync with outputs
 *    - qw_session_lock_surface_handle_destroy(): Handles surface destruction
 *    - qw_session_lock_handle_unlock()         : Handles unlock events
 *    - qw_session_lock_destroy()               : Tears down lock state and resources
 *
 * Locking Flow:
 *
 *   Client requests lock
 *     → qw_session_lock_handle_new()
 *       → compositor enters QW_SESSION_LOCK_LOCKED state, blanking rects shown
 *       → client creates per-output surfaces
 *         → qw_session_lock_handle_new_surface() (setup + focus)
 *
 *   While locked:
 *     → qw_session_lock_output_change() keeps surfaces synced to outputs
 *
 *   Client requests unlock
 *     → qw_session_lock_handle_unlock()
 *       → qw_session_lock_destroy(unlock = true)
 *         → hides blanking rects, restores focus
 *         → compositor returns to QW_SESSION_LOCK_UNLOCKED state
 *
 *   Client exits without unlocking
 *     → qw_session_lock_destroy(unlock = false)
 *       → blanking rects changed to indicate error state
 *       → compositor set to QW_SESSION_LOCK_CRASHED state
 *
 * This flow ensures the compositor maintains a secure lock state until an
 * explicit unlock event is received, or a crash is detected.
 */
#include "session-lock.h"
#include "output.h"
#include "server.h"
#include <wayland-util.h>
#include <wlr/types/wlr_session_lock_v1.h>

void qw_session_lock_restore_focus(struct qw_server *server) {
    struct wlr_seat *seat = server->seat;
    struct qw_session_lock *lock = server->lock;

    if (lock->prev_keyboard_focus != NULL && seat->keyboard_state.keyboard != NULL) {
        struct wlr_keyboard *kbd = seat->keyboard_state.keyboard;

        wlr_seat_keyboard_notify_enter(seat, lock->prev_keyboard_focus, kbd->keycodes,
                                       kbd->num_keycodes, &kbd->modifiers);

        lock->prev_keyboard_focus = NULL;
    }

    if (lock->prev_pointer_focus != NULL) {
        wlr_seat_pointer_notify_enter(seat, lock->prev_pointer_focus, 0, 0);
        lock->prev_pointer_focus = NULL;
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

    // Create rects and set size and position
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
    struct qw_session_lock_surface *sls = wl_container_of(listener, sls, surface_destroy);
    struct qw_server *server = sls->server;

    // If the lock client itself is gone, nothing more to do
    if (!server->lock || !server->lock->lock) {
        goto cleanup;
    }

    // Remove reference to this surface
    struct wlr_session_lock_surface_v1 *lock_surface = sls->lock_surface;
    if (lock_surface->link.prev != NULL && lock_surface->link.next != NULL) {
        wl_list_remove(&lock_surface->link);
        wl_list_init(&lock_surface->link);
    }

    // Focus shifts if other surfaces remain
    if (!wl_list_empty(&server->lock->lock->surfaces)) {
        qw_session_lock_focus_first_lock_surface(server);
    } else {
        // No surfaces remain, but lock client still exists → do NOT mark as crashed
        // This situation arises when changing VT
    }

cleanup:
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

        qw_session_lock_restore_focus(server);

        server->lock_state = QW_SESSION_LOCK_UNLOCKED;
    } else if (server->lock_state == QW_SESSION_LOCK_LOCKED && !unlock) {
        wlr_log(WLR_ERROR, "Session lock client vanished without unlocking.");
        server->lock_state = QW_SESSION_LOCK_CRASHED;

        // Bring blanking rects to top so contents stay hidden
        qw_session_lock_crashed_update_rects(server);
    }

    // Remove event listeners for this lock
    wl_list_remove(&session_lock->new_surface.link);
    wl_list_remove(&session_lock->unlock.link);
    wl_list_remove(&session_lock->destroy.link);

    // Clean up lock scene subtree
    wlr_scene_node_destroy(&session_lock->scene->node);
    session_lock->server->lock = NULL;
    free(session_lock);
}

void qw_session_lock_handle_unlock(struct wl_listener *listener, void *data) {
    struct qw_session_lock *lock = wl_container_of(listener, lock, unlock);
    struct qw_server *server = lock->server;
    // Unlock event from client → destroy lock with unlock=true
    qw_session_lock_destroy(lock, true);
    wlr_log(WLR_ERROR, "Sending unlock to server");
    server->on_session_lock_cb(false, server->cb_data);
}

void qw_session_lock_handle_destroy(struct wl_listener *listener, void *data) {
    struct qw_session_lock *lock = wl_container_of(listener, lock, destroy);
    // Lock object destroyed without unlock → destroy lock with unlock=false
    // This leaves the compositor in a "crashed lock" state.
    qw_session_lock_destroy(lock, false);
}

void qw_session_lock_handle_new_surface(struct wl_listener *listener, void *data) {
    struct qw_session_lock *lock = wl_container_of(listener, lock, new_surface);
    struct wlr_session_lock_surface_v1 *lock_surface = data;
    struct qw_output *output = lock_surface->output->data;

    // Create a scene node tree for this lock surface
    struct wlr_scene_tree *scene_tree = lock_surface->surface->data =
        wlr_scene_subsurface_tree_create(lock->scene, lock_surface->surface);
    output->lock_surface = lock_surface;

    // Make sure lock surface is at the top.
    wlr_scene_node_raise_to_top(&scene_tree->node);

    // wlr_session_lock_v1_send_locked(lock->lock);
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
    if (keyboard && output->wlr_output == lock->server->current_output) {
        wlr_seat_keyboard_notify_enter(lock->server->seat, lock_surface->surface,
                                       keyboard->keycodes, keyboard->num_keycodes,
                                       &keyboard->modifiers);
        wlr_seat_pointer_notify_enter(lock->server->seat, lock_surface->surface, 0, 0);
    }

    // Listen for destroy events on this lock surface
    // Allocate a listener tied to this surface
    struct qw_session_lock_surface *sls = calloc(1, sizeof(*lock));
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

    // Enable the LOCK layer to show blanking rects
    wlr_scene_node_set_enabled(&server->scene_windows_layers[LAYER_LOCK]->node, true);

    // Allocate compositor-side lock tracking struct
    struct qw_session_lock *lock = calloc(1, sizeof(*lock));
    if (lock == NULL) {
        wlr_session_lock_v1_destroy(session_lock);
        return;
    }

    struct wlr_seat *seat = server->seat;
    lock->prev_keyboard_focus = seat->keyboard_state.focused_surface;
    lock->prev_pointer_focus = seat->pointer_state.focused_surface;

    lock->scene = wlr_scene_tree_create(server->scene_windows_layers[LAYER_LOCK]);
    lock->server = server;
    lock->lock = session_lock;
    server->lock = lock;
    server->lock_state = QW_SESSION_LOCK_LOCKED;

    // Hook up listeners for session lock lifecycle
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
    // Start unlocked
    server->lock_state = QW_SESSION_LOCK_UNLOCKED;

    // Create the wlroots session lock manager
    server->lock_manager = wlr_session_lock_manager_v1_create(server->display);

    // Listen for new lock requests
    server->new_session_lock.notify = qw_session_lock_handle_new;
    wl_signal_add(&server->lock_manager->events.new_lock, &server->new_session_lock);

    // Disable lock screen layer by default (only enabled on lock)
    wlr_scene_node_set_enabled(&server->scene_windows_layers[LAYER_LOCK]->node, false);
}
