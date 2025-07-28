#ifndef VIEW_H
#define VIEW_H

#include <wayland-server-core.h>
#include <wlr/types/wlr_scene.h>

// TODO: avoid this duplication
// View states representing window states, similar to backend/base/window.py
enum qw_view_state {
    NOT_FLOATING = 1,
    FLOATING = 2,
    MAXIMIZED = 3,
    FULLSCREEN = 4,
    TOP = 5,
    MINIMIZED = 6,
};

// Callback type for fullscreen request (true = enter fullscreen, false = exit)
typedef int (*request_fullscreen_cb_t)(bool fullscreen, void *userdata);

// Callback type for maximize request (true = maximize, false = unmaximize)
typedef int (*request_maximize_cb_t)(bool maximize, void *userdata);

// Callback type for title updated
typedef void (*set_title_cb_t)(char *title, void *userdata);

// Callback type for app_id updated
typedef void (*set_app_id_cb_t)(char *app_id, void *userdata);

struct qw_server;

struct qw_view {
    struct qw_server *server;
    int layer;
    int x;
    int y;
    int width;
    int height;
    int bn; // Number of border layers
    enum qw_view_state state;
    char *shell; // e.g. "XdgWindow" or "XWayland"
    int wid;     // Window identifier (e.g. X11 window id or similar)
    char *title;
    char *app_id;
    struct wlr_scene_tree *content_tree; // Scene tree holding the view's content

    request_maximize_cb_t request_maximize_cb;
    request_fullscreen_cb_t request_fullscreen_cb;
    set_title_cb_t set_title_cb;
    set_app_id_cb_t set_app_id_cb;
    void *cb_data; // User data passed to callbacks

    // Methods, implemented as function pointers
    struct wlr_scene_node *(*get_tree_node)(void *self);
    void (*update_fullscreen)(void *self, bool fullscreen);
    void (*update_maximized)(void *self, bool maximize);
    void (*place)(void *self, int x, int y, int width, int height, int bw, float (*bc)[4], int bn,
                  int above);
    void (*focus)(void *self, int warp);
    void (*kill)(void *self);
    void (*hide)(void *self);
    void (*unhide)(void *self);
    int (*get_pid)(void *self);

    // Private data: pointer to an array of 4 pointers to wlr_scene_rect for borders
    struct wlr_scene_rect *(*borders)[4];
};

void qw_view_reparent(struct qw_view *view, int layer);
void qw_view_move_up(struct qw_view *view);
void qw_view_move_down(struct qw_view *view);
void qw_view_raise_to_top(struct qw_view *view);
void qw_view_lower_to_bottom(struct qw_view *view);

bool qw_view_is_visible(struct qw_view *view);

// Free all border rectangles and clear border data
void qw_view_cleanup_borders(struct qw_view *xdg_view);

// Create and paint borders with specified colors, border width, and number of layers
void qw_view_paint_borders(struct qw_view *xdg_view, float (*colors)[4], int width, int n);

#endif /* VIEW_H */
