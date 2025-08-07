#ifndef QW_XWAYLAND_VIEW
#define QW_XWAYLAND_VIEW

#include <stdbool.h>
#include <view.h>
#include <wayland-server-core.h>
#include <wlr/types/wlr_scene.h>
#include <wlr/xwayland.h>
#include <wlr/xwayland/shell.h>

// Represents an XWayland-managed view
struct qw_xwayland_view {
    struct qw_view base;
    struct qw_server *server;

    struct wlr_scene_tree *scene_tree;
    struct wlr_scene_surface *scene_surface;
    struct wlr_box geom;
    struct wlr_xwayland_surface *qw_xwayland_surface;

    // Listeners for various XWayland surface events and requests
    // Private data
    struct wl_listener commit;
    struct wl_listener request_move;
    struct wl_listener request_resize;
    struct wl_listener request_maximize;
    struct wl_listener request_minimize;
    struct wl_listener request_configure;
    struct wl_listener request_fullscreen;
    struct wl_listener request_activate;
    struct wl_listener set_title;
    struct wl_listener set_class;
    struct wl_listener set_role;
    struct wl_listener set_startup_id;
    struct wl_listener set_window_type;
    struct wl_listener set_hints;
    struct wl_listener set_decorations;
    struct wl_listener associate;
    struct wl_listener dissociate;
    struct wl_listener map;
    struct wl_listener unmap;
    struct wl_listener destroy;
    struct wl_listener override_redirect;

    struct wl_listener scene_tree_destroy;
};

// Represents an unmanaged XWayland surface (like popup, override redirect windows)
struct qw_xwayland_unmanaged {
    struct wlr_xwayland_surface *wlr_xwayland_surface; // The underlying wlroots surface

    struct wlr_scene_surface *scene_surface; // Scene surface for rendering

    // Listeners for unmanaged surface events
    // Private data
    struct wl_listener request_activate;
    struct wl_listener request_configure;
    struct wl_listener request_fullscreen;
    struct wl_listener set_geometry;
    struct wl_listener associate;
    struct wl_listener dissociate;
    struct wl_listener map;
    struct wl_listener unmap;
    struct wl_listener destroy;
    struct wl_listener override_redirect;
};

// Listener callback for XWayland unmanaged surface configuration requests.
// void qw_xwayland_view_unmanaged_request_configure(struct wl_listener *listener, void *data);
// void qw_xwayland_view_unmanaged_associate(struct wl_listener *listener, void *data);
// void qw_xwayland_view_unmanaged_dissociate(struct wl_listener *listener, void *data);
// void qw_xwayland_view_unmanaged_destroy(struct wl_listener *listener, void *data);
// void qw_xwayland_view_unmanaged_override_redirect(struct wl_listener *listener, void *data);
// void qw_xwayland_view_unmanaged_request_activate(struct wl_listener *listener, void *data);
struct qw_xwayland_view *create_xwayland_view(struct wlr_xwayland_surface *qw_xsurface);
void qw_server_xwayland_view_new(struct qw_server *server, struct wlr_xwayland_surface *xwayland_surface);

#endif /* QW_XWAYLAND_VIEW */
