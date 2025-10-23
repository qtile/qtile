#ifndef CURSOR_H
#define CURSOR_H

#include <wlr/types/wlr_cursor.h>
#include <wlr/types/wlr_xcursor_manager.h>

struct qw_server; // Forward declaration to avoid circular dependency

// Cursor structure that holds cursor state and event listeners
struct qw_cursor {
    struct wlr_cursor *cursor;
    struct qw_view *view;

    // private data
    struct qw_server *server;
    struct wl_listener request_set;
    struct wl_listener axis;
    struct wl_listener motion;
    struct wl_listener motion_absolute;
    struct wl_listener frame;
    struct wl_listener button;
    struct wlr_xcursor_manager *mgr;
    struct wlr_surface *saved_surface;
    uint32_t saved_hotspot_x;
    uint32_t saved_hotspot_y;
    bool hidden;
};

// Destroy the cursor and free its resources
void qw_cursor_destroy(struct qw_cursor *cursor);

// Create and initialize a new cursor associated with the server
struct qw_cursor *qw_server_cursor_create(struct qw_server *cursor);

void qw_cursor_warp_cursor(struct qw_cursor *cursor, double x, double y);

// Functions for hiding and showing the cursor
void qw_cursor_hide(struct qw_cursor *cursor);
void qw_cursor_show(struct qw_cursor *cursor);

#endif /* CURSOR_H */
