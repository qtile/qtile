#ifndef CURSOR_H
#define CURSOR_H

#include <wlr/types/wlr_cursor.h>
#include <wlr/types/wlr_pointer_constraints_v1.h>
#include <wlr/types/wlr_xcursor_manager.h>

struct qw_server; // Forward declaration to avoid circular dependency

struct qw_implicit_grab {
    double start_dx;
    double start_dy;
    bool live;
};

// Cursor structure that holds cursor state and event listeners
struct qw_cursor {
    struct wlr_cursor *cursor;
    struct qw_view *view;
    struct qw_implicit_grab implicit_grab;

    // private data
    struct qw_server *server;
    struct wl_listener request_set;
    struct wl_listener axis;
    struct wl_listener motion;
    struct wl_listener motion_absolute;
    struct wl_listener frame;
    struct wl_listener button;
    struct wl_listener constraint_commit;
    struct wlr_xcursor_manager *mgr;
    struct wlr_surface *saved_surface;
    uint32_t saved_hotspot_x;
    uint32_t saved_hotspot_y;
    bool hidden;
    struct wlr_pointer_constraint_v1 *active_constraint;
    bool active_confine_requires_warp;
    pixman_region32_t confine;
};

struct qw_pointer_constraint {
    struct qw_cursor *cursor;
    // private data
    struct wlr_pointer_constraint_v1 *constraint;
    struct wl_listener set_region;
    struct wl_listener destroy;
};

// Destroy the cursor and free its resources
void qw_cursor_destroy(struct qw_cursor *cursor);

// Create and initialize a new cursor associated with the server
struct qw_cursor *qw_server_cursor_create(struct qw_server *cursor);

void qw_cursor_warp_cursor(struct qw_cursor *cursor, double x, double y);

void qw_cursor_update_pointer_focus(struct qw_cursor *cursor);

// Functions for hiding and showing the cursor
void qw_cursor_hide(struct qw_cursor *cursor);
void qw_cursor_show(struct qw_cursor *cursor);

void qw_cursor_release_implicit_grab(struct qw_cursor *cursor, uint32_t time);

void qw_cursor_pointer_constraint_new(struct qw_cursor *cursor,
                                      struct wlr_pointer_constraint_v1 *constraint);

#endif /* CURSOR_H */
