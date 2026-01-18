#ifndef XDG_VIEW_H
#define XDG_VIEW_H

// Include the generic view base struct and Wayland/WLRoots core and types
#include "output.h"
#include "view.h"
#include <wayland-server-core.h>
#include <wlr/types/wlr_layer_shell_v1.h>
#include <wlr/types/wlr_scene.h>
#include <wlr/types/wlr_xdg_shell.h>

// Forward declarations for server and decoration struct types
struct qw_server;
struct wlr_xdg_toplevel_decoration_v1;

struct qw_xdg_activation_token {
    bool qw_valid_seat;
    struct wl_listener destroy;
};

// Struct representing an XDG toplevel view in the compositor
struct qw_xdg_view {
    struct qw_view base;
    struct wlr_xdg_toplevel *xdg_toplevel;
    struct wlr_scene_tree *scene_tree;
    struct wlr_box geom;

    // Listeners for Wayland events on the toplevel surface lifecycle and requests
    struct wl_listener map;
    struct wl_listener unmap;
    struct wl_listener commit;
    struct wl_listener destroy;
    struct wl_listener request_maximize;
    struct wl_listener request_fullscreen;
    struct wl_listener set_title;
    struct wl_listener set_app_id;
    struct wl_listener new_popup;
    // TODO: add listeners for move and resize requests

    // Listeners for client decoration protocol events
    struct wl_listener decoration_request_mode;
    struct wl_listener decoration_destroy;
    struct wlr_xdg_toplevel_decoration_v1 *decoration;

    bool mapped; // Is the view currently mapped (visible)?
};

struct qw_xdg_popup {
    struct qw_view base;
    // parent xdg-view
    struct qw_xdg_view *xdg_view;
    struct wlr_xdg_popup *wlr_popup;
    struct wlr_scene_tree *scene_tree;
    struct wlr_scene_tree *xdg_surface_tree;

    struct wl_listener surface_commit;
    struct wl_listener new_popup;
    struct wl_listener reposition;
    struct wl_listener destroy;
};

// Initialize decoration handling for a new decoration object associated with this view
void qw_xdg_view_decoration_new(struct qw_xdg_view *xdg_view,
                                struct wlr_xdg_toplevel_decoration_v1 *deco);

// Create and initialize a new qw_xdg_view wrapping the given wlr_xdg_toplevel
void qw_server_xdg_view_new(struct qw_server *server, struct wlr_xdg_toplevel *xdg_toplevel);

void qw_xdg_view_focus(void *self, int above);

void qw_xdg_activation_new_token(struct wl_listener *listener, void *data);

#endif /* XDG_VIEW_H */
