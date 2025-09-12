#ifndef VIEW_H
#define VIEW_H

#include <cairo/cairo.h>
#include <wayland-server-core.h>
#include <wlr/types/wlr_buffer.h>
#include <wlr/types/wlr_foreign_toplevel_management_v1.h>
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

// Callback type for focus request
typedef int (*request_focus_cb_t)(void *userdata);

// Callback type for close request
typedef int (*request_close_cb_t)(void *userdata);

// Callback type for fullscreen request (true = enter fullscreen, false = exit)
typedef int (*request_fullscreen_cb_t)(bool fullscreen, void *userdata);

// Callback type for maximize request (true = maximize, false = unmaximize)
typedef int (*request_maximize_cb_t)(bool maximize, void *userdata);

// Callback type for minimize request (true = minimize, false = unminimize)
typedef int (*request_minimize_cb_t)(bool minimize, void *userdata);

// Callback type for title updated
typedef void (*set_title_cb_t)(char *title, void *userdata);

// Callback type for app_id updated
typedef void (*set_app_id_cb_t)(char *app_id, void *userdata);

struct qw_server;

enum qw_view_type {
    QW_VIEW_XDG,
    QW_VIEW_XWAYLAND,
    QW_VIEW_INTERNAL,
};

enum qw_border_type {
    QW_BORDER_RECT,
    QW_BORDER_BUFFER,
};

struct qw_border {
    enum qw_border_type type;
    uint32_t width; // border thickness (for all sides)

    union {
        struct {
            float color[4][4]; // RGBA per side (NESW)
        } rect;

        struct {
            cairo_surface_t *surface; // Full border ring image
        } buffer;
    };
};

struct qw_view {
    struct qw_server *server;
    int layer;
    int x;
    int y;
    int width;
    int height;
    int bn; // Number of border layers
    enum qw_view_state state;
    enum qw_view_type view_type;
    char *shell; // e.g. "XdgWindow" or "XWayland"
    int wid;     // Window identifier (e.g. X11 window id or similar)
    char *title;
    char *app_id;
    struct wlr_scene_tree *content_tree; // Scene tree holding the view's content
    struct wlr_foreign_toplevel_handle_v1 *ftl_handle;

    request_focus_cb_t request_focus_cb;
    request_close_cb_t request_close_cb;
    request_maximize_cb_t request_maximize_cb;
    request_minimize_cb_t request_minimize_cb;
    request_fullscreen_cb_t request_fullscreen_cb;
    set_title_cb_t set_title_cb;
    set_app_id_cb_t set_app_id_cb;
    void *cb_data; // User data passed to callbacks

    // Methods, implemented as function pointers
    struct wlr_scene_node *(*get_tree_node)(void *self);
    void (*update_fullscreen)(void *self, bool fullscreen);
    void (*update_maximized)(void *self, bool maximize);
    void (*update_minimized)(void *self, bool minimize);
    void (*place)(void *self, int x, int y, int width, int height, const struct qw_border *borders,
                  int border_count, int above);
    void (*focus)(void *self, int warp);
    void (*kill)(void *self);
    void (*hide)(void *self);
    void (*unhide)(void *self);
    int (*get_pid)(void *self);

    // Private data: pointer to an array of 4 pointers to wlr_scene_rect for borders
    struct {
        enum qw_border_type type;
        union {
            struct wlr_scene_rect *rects[4];
            struct wlr_scene_buffer *scene_bufs[4];
        };
    } *borders;
    struct wl_listener ftl_request_activate;
    struct wl_listener ftl_request_close;
    struct wl_listener ftl_request_maximize;
    struct wl_listener ftl_request_minimize;
    struct wl_listener ftl_request_fullscreen;
    // ftl output tracking
    struct wlr_scene_buffer *ftl_output_tracking_buffer;
    struct wl_listener ftl_output_enter;
    struct wl_listener ftl_output_leave;
};

void qw_view_reparent(struct qw_view *view, int layer);
void qw_view_move_up(struct qw_view *view);
void qw_view_move_down(struct qw_view *view);
void qw_view_raise_to_top(struct qw_view *view);
void qw_view_lower_to_bottom(struct qw_view *view);

bool qw_view_is_visible(struct qw_view *view);

// Free all border rectangles and clear border data
void qw_view_cleanup_borders(struct qw_view *xdg_view);

// Create and paint borders with specified colors
void qw_view_paint_borders(struct qw_view *view, const struct qw_border *borders, int border_count);

// Create/destroy a foreign toplevel manager handle and listeners
void qw_view_ftl_manager_handle_create(struct qw_view *view);
void qw_view_ftl_manager_handle_destroy(struct qw_view *view);
void qw_view_resize_ftl_output_tracking_buffer(struct qw_view *view, int width, int height);

#endif /* VIEW_H */
