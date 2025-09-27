#ifndef SESSIONLOCK_H
#define SESSIONLOCK_H

#include <wayland-server-core.h>
#include <wlr/types/wlr_session_lock_v1.h>

struct qw_server;
struct qw_output;

// Set colors for blanking rects
// Dark blue for normal locked state
static const float QW_SESSION_LOCK_BLANKING_RECT_LOCKED[4] = {0, 0, 0.1f, 1};
// Dark red for crashed state
static const float QW_SESSION_LOCK_BLANKING_RECT_CRASHED[4] = {0.1f, 0, 0, 1};

enum qw_session_lock_state {
    QW_SESSION_LOCK_LOCKED,
    QW_SESSION_LOCK_UNLOCKED,
    QW_SESSION_LOCK_CRASHED
};

struct qw_session_lock_surface {
    struct qw_server *server;
    struct wlr_session_lock_surface_v1 *lock_surface;

    // Private data
    struct wl_listener surface_destroy;
};

// Session lock
struct qw_session_lock {
    struct qw_server *server;
    struct wlr_scene_tree *scene;
    struct wlr_session_lock_v1 *lock;

    // Private data
    struct wl_listener new_surface;
    struct wl_listener unlock;
    struct wl_listener destroy;
};

void qw_session_lock_init(struct qw_server *server);
void qw_session_lock_output_create_blanking_rects(struct qw_output *output);
void qw_session_lock_output_change(struct qw_output *output);
void qw_session_lock_focus_first_lock_surface(struct qw_server *server);

#endif // SESSIONLOCK_H
