#ifndef XDG_VIEW_H
#define XDG_VIEW_H

#include "view.h"
#include <wayland-server-core.h>
#include <wlr/types/wlr_scene.h>
#include <wlr/types/wlr_xdg_shell.h>

struct qw_server;
struct wlr_xdg_toplevel_decoration_v1;

struct qw_xdg_view {
    struct qw_view base;
    struct qw_server *server;
    struct wlr_xdg_toplevel *xdg_toplevel;
    struct wlr_scene_tree *scene_tree;
    struct wl_listener map;
    struct wl_listener unmap;
    struct wl_listener commit;
    struct wl_listener destroy;
    // TODO: request_{move,resize,maximize,fullscreen}
    struct wl_listener decoration_request_mode;
    struct wl_listener decoration_destroy;
    struct wlr_xdg_toplevel_decoration_v1 *decoration;
    bool mapped;
};

void qw_xdg_view_decoration_new(struct qw_xdg_view *xdg_view,
                                struct wlr_xdg_toplevel_decoration_v1 *deco);

void qw_server_xdg_view_new(struct qw_server *server, struct wlr_xdg_toplevel *xdg_toplevel);

#endif /* XDG_VIEW_H */
