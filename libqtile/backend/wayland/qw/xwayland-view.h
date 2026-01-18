#ifndef QW_XWAYLAND_VIEW
#define QW_XWAYLAND_VIEW

#include <stdbool.h>
#include <view.h>
#include <wayland-server-core.h>
#include <wlr/types/wlr_scene.h>
#include <wlr/xwayland.h>
#include <wlr/xwayland/shell.h>

struct qw_xwayland_view {
    struct qw_view base;

    struct wlr_scene_tree *scene_tree;
    struct wlr_scene_surface *scene_surface;
    struct wlr_box geom;
    struct wlr_xwayland_surface *xwayland_surface;

    // Listeners for various XWayland surface events and requests
    // Private data
    struct wl_listener commit;
    struct wl_listener request_maximize;
    struct wl_listener request_minimize;
    struct wl_listener request_configure;
    struct wl_listener request_fullscreen;
    struct wl_listener request_activate;
    struct wl_listener request_close;
    struct wl_listener request_above;
    struct wl_listener request_below;
    struct wl_listener request_skip_taskbar;
    struct wl_listener set_title;
    struct wl_listener set_class;
    struct wl_listener set_hints;
    struct wl_listener associate;
    struct wl_listener dissociate;
    struct wl_listener map;
    struct wl_listener unmap;
    struct wl_listener destroy;
    struct wl_listener set_geometry;
    struct wl_listener override_redirect;

    struct wl_listener scene_tree_destroy;
};

void qw_server_xwayland_static_view_new(struct qw_server *server,
                                        struct wlr_xwayland_surface *xwayland_surface);
void qw_server_xwayland_view_new(struct qw_server *server,
                                 struct wlr_xwayland_surface *xwayland_surface);

#endif /* QW_XWAYLAND_VIEW */
