#ifndef LAYER_VIEW_H
#define LAYER_VIEW_H

// Include the generic view base struct and Wayland/WLRoots core and types
#include "view.h"
#include <wayland-server-core.h>
#include <wlr/types/wlr_compositor.h>
#include <wlr/types/wlr_layer_shell_v1.h>

// Forward declarations for server and decoration struct types
struct qw_server;

// Struct representing an layer shell view in the compositor
struct qw_layer_view {
    struct qw_view base;
    struct qw_server *server;
    struct qw_output *output;
    struct wlr_layer_surface_v1 *surface;
    struct wlr_layer_surface_v1_state state;
    bool mapped;

    struct wlr_scene_layer_surface_v1 *scene;
    struct wlr_scene_tree *popups;

    struct wl_list link;
    struct wl_listener commit;
    struct wl_listener destroy;
    struct wl_listener unmap;
    struct wl_listener new_popup;
};

struct qw_layer_popup {
    struct qw_layer_view *toplevel;
    struct wlr_xdg_popup *wlr_popup;
    struct wlr_scene_tree *xdg_surface_tree;

    struct wl_listener surface_commit;
    struct wl_listener new_popup;
    struct wl_listener destroy;
};

// Create and initialize a new qw_layer_view wrapping the given layer_surface
void qw_server_layer_view_new(struct qw_server *server, struct wlr_layer_surface_v1 *layer_surface);

void qw_layer_view_focus(struct qw_layer_view *layer_view);

#endif /* LAYER_VIEW_H */
