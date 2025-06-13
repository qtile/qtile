#ifndef CURSOR_H
#define CURSOR_H

#include <wlr/types/wlr_cursor.h>
#include <wlr/types/wlr_xcursor_manager.h>

struct qw_server; // Forward declaration to avoid circular dependency

// Cursor structure that holds cursor state and event listeners
struct qw_cursor {
    struct qw_server *server;
    struct wlr_cursor *cursor;
    struct wl_listener request_set;
    struct wl_listener axis;
    struct wl_listener motion;
    struct wl_listener motion_absolute;
    struct wl_listener frame;
    struct wl_listener button;
    struct wlr_xcursor_manager *mgr;
};

// Destroy the cursor and free its resources
void qw_cursor_destroy(struct qw_cursor *cursor);

// Create and initialize a new cursor associated with the server
struct qw_cursor *qw_server_cursor_create(struct qw_server *cursor);

#endif /* CURSOR_H */
