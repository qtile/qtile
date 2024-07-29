#include "xdg-view.h"
#include "server.h"
#include <stdlib.h>

static void qw_xdg_view_do_focus(struct qw_xdg_view *xdg_view, struct wlr_surface *surface) {
    if (!xdg_view) {
        return;
    }
    struct qw_server *server = xdg_view->server;
    struct wlr_seat *seat = server->seat;
    struct wlr_surface *prev_surface = seat->keyboard_state.focused_surface;
    if (prev_surface == surface) {
        return;
    }
    if (prev_surface) {
        struct wlr_xdg_toplevel *prev_toplevel =
            wlr_xdg_toplevel_try_from_wlr_surface(prev_surface);
        if (prev_toplevel) {
            wlr_xdg_toplevel_set_activated(prev_toplevel, false);
        }
    }
    struct wlr_keyboard *keyboard = wlr_seat_get_keyboard(seat);
    wlr_scene_node_raise_to_top(&xdg_view->base.content_tree->node);
    wlr_xdg_toplevel_set_activated(xdg_view->xdg_toplevel, true);
    if (keyboard) {
        wlr_seat_keyboard_notify_enter(seat, xdg_view->xdg_toplevel->base->surface,
                                       keyboard->keycodes, keyboard->num_keycodes,
                                       &keyboard->modifiers);
    }
}

static void qw_xdg_view_handle_unmap(struct wl_listener *listener, void *data) {
    struct qw_xdg_view *xdg_view = wl_container_of(listener, xdg_view, unmap);
    qw_view_cleanup_borders((struct qw_view *)xdg_view);
    xdg_view->server->unmanage_view_cb((struct qw_view *)&xdg_view->base,
                                       xdg_view->server->cb_data);
}

static void qw_xdg_view_handle_destroy(struct wl_listener *listener, void *data) {
    struct qw_xdg_view *xdg_view = wl_container_of(listener, xdg_view, destroy);

    wl_list_remove(&xdg_view->map.link);
    wl_list_remove(&xdg_view->unmap.link);
    wl_list_remove(&xdg_view->commit.link);
    wl_list_remove(&xdg_view->destroy.link);

    // TODO wl_list_remove request_{move,resize,maximize,fullscreen}
    free(xdg_view);
}

static void qw_xdg_view_handle_map(struct wl_listener *listener, void *data) {
    struct qw_xdg_view *xdg_view = wl_container_of(listener, xdg_view, map);
    xdg_view->mapped = true;

    qw_xdg_view_do_focus(xdg_view, xdg_view->xdg_toplevel->base->surface);

    // TODO: do this managed on the first map instead
    if (wl_resource_get_version(xdg_view->xdg_toplevel->resource) >=
        XDG_TOPLEVEL_STATE_TILED_RIGHT_SINCE_VERSION) {
        wlr_xdg_toplevel_set_tiled(xdg_view->xdg_toplevel,
                                   WLR_EDGE_TOP | WLR_EDGE_BOTTOM | WLR_EDGE_LEFT | WLR_EDGE_RIGHT);
    } else {
        wlr_xdg_toplevel_set_maximized(xdg_view->xdg_toplevel, true);
    }
}

static void qw_xdg_view_handle_commit(struct wl_listener *listener, void *data) {
    struct qw_xdg_view *xdg_view = wl_container_of(listener, xdg_view, commit);

    if (xdg_view->xdg_toplevel->base->initial_commit) {
        wlr_xdg_toplevel_set_size(xdg_view->xdg_toplevel, 0, 0);
        // TODO: manage on first map
        xdg_view->server->manage_view_cb((struct qw_view *)&xdg_view->base,
                                         xdg_view->server->cb_data);
    }
}

static void qw_xdg_view_place(void *self, int x, int y, int width, int height, int bw,
                              float (*bc)[4], int bn, int above) {
    struct qw_xdg_view *xdg_view = (struct qw_xdg_view *)self;
    xdg_view->base.x = x;
    xdg_view->base.y = y;
    xdg_view->base.width = width;
    xdg_view->base.height = height;

    wlr_scene_node_set_position(&xdg_view->base.content_tree->node, x, y);
    // TODO: needs_repos
    wlr_xdg_toplevel_set_size(xdg_view->xdg_toplevel, width, height);
    qw_view_paint_borders((struct qw_view *)xdg_view, bc, bw, bn);
}

static void qw_xdg_view_bring_to_front(void *self) {
    struct qw_xdg_view *xdg_view = (struct qw_xdg_view *)self;
    wlr_scene_node_raise_to_top(&xdg_view->base.content_tree->node);
}

static void qw_xdg_view_kill(void *self) {
    struct qw_xdg_view *xdg_view = (struct qw_xdg_view *)self;
    wlr_xdg_toplevel_send_close(xdg_view->xdg_toplevel);
}

static void qw_xdg_view_hide(void *self) {
    struct qw_xdg_view *xdg_view = (struct qw_xdg_view *)self;
    wlr_scene_node_set_enabled(&xdg_view->base.content_tree->node, false);
    if (xdg_view->xdg_toplevel->base->surface ==
        xdg_view->server->seat->keyboard_state.focused_surface) {
        wlr_seat_keyboard_clear_focus(xdg_view->server->seat);
    }
}

static void qw_xdg_view_unhide(void *self) {
    struct qw_xdg_view *xdg_view = (struct qw_xdg_view *)self;
    if (!xdg_view->base.content_tree->node.enabled) {
        wlr_scene_node_set_enabled(&xdg_view->base.content_tree->node, true);
    }
}

void qw_xdg_view_focus(void *self, int above) {
    struct qw_xdg_view *xdg_view = (struct qw_xdg_view *)self;
    if (!xdg_view->mapped) {
        return;
    }
    qw_xdg_view_do_focus(xdg_view, xdg_view->xdg_toplevel->base->surface);
}

static int qw_xdg_view_get_pid(void *self) {
    struct qw_xdg_view *xdg_view = (struct qw_xdg_view *)self;
    int pid;
    wl_client_get_credentials(xdg_view->xdg_toplevel->base->client->client, &pid, NULL, NULL);
    return pid;
}

static void qw_xdg_view_handle_decoration_request_mode(struct wl_listener *listener, void *data) {
    struct qw_xdg_view *xdg_view = wl_container_of(listener, xdg_view, decoration_request_mode);
    if (xdg_view->xdg_toplevel->base->initialized)
        wlr_xdg_toplevel_decoration_v1_set_mode(xdg_view->decoration,
                                                WLR_XDG_TOPLEVEL_DECORATION_V1_MODE_SERVER_SIDE);
}

static void qw_xdg_view_handle_decoration_destroy(struct wl_listener *listener, void *data) {
    struct qw_xdg_view *xdg_view = wl_container_of(listener, xdg_view, decoration_destroy);

    wl_list_remove(&xdg_view->decoration_destroy.link);
    wl_list_remove(&xdg_view->decoration_request_mode.link);
}

void qw_xdg_view_decoration_new(struct qw_xdg_view *xdg_view,
                                struct wlr_xdg_toplevel_decoration_v1 *decoration) {
    xdg_view->decoration = decoration;
    xdg_view->decoration_request_mode.notify = qw_xdg_view_handle_decoration_request_mode;
    wl_signal_add(&decoration->events.request_mode, &xdg_view->decoration_request_mode);
    xdg_view->decoration_destroy.notify = qw_xdg_view_handle_decoration_destroy;
    wl_signal_add(&decoration->events.destroy, &xdg_view->decoration_destroy);

    qw_xdg_view_handle_decoration_request_mode(&xdg_view->decoration_request_mode, decoration);
}

static struct wlr_scene_node *qw_xdg_view_get_tree_node(void *self) {
    struct qw_xdg_view *xdg_view = (struct qw_xdg_view *)self;
    if (!xdg_view->scene_tree) {
        return NULL;
    }
    return &xdg_view->scene_tree->node;
}

void qw_server_xdg_view_new(struct qw_server *server, struct wlr_xdg_toplevel *xdg_toplevel) {
    struct qw_xdg_view *xdg_view = calloc(1, sizeof(*xdg_view));
    if (!xdg_view) {
        wlr_log(WLR_ERROR, "failed to create qw_xdg_view struct");
        return;
    }
    xdg_view->server = server;
    xdg_view->xdg_toplevel = xdg_toplevel;
    xdg_view->base.content_tree = wlr_scene_tree_create(&server->scene->tree);
    xdg_view->scene_tree =
        wlr_scene_xdg_surface_create(xdg_view->base.content_tree, xdg_toplevel->base);
    xdg_view->scene_tree->node.data = xdg_view;
    xdg_toplevel->base->data = xdg_view;

    xdg_view->base.get_tree_node = qw_xdg_view_get_tree_node;
    xdg_view->base.place = qw_xdg_view_place;
    xdg_view->base.focus = qw_xdg_view_focus;
    xdg_view->base.get_pid = qw_xdg_view_get_pid;
    xdg_view->base.bring_to_front = qw_xdg_view_bring_to_front;
    xdg_view->base.kill = qw_xdg_view_kill;
    xdg_view->base.hide = qw_xdg_view_hide;
    xdg_view->base.unhide = qw_xdg_view_unhide;

    xdg_view->map.notify = qw_xdg_view_handle_map;
    wl_signal_add(&xdg_toplevel->base->surface->events.map, &xdg_view->map);
    xdg_view->unmap.notify = qw_xdg_view_handle_unmap;
    wl_signal_add(&xdg_toplevel->base->surface->events.unmap, &xdg_view->unmap);
    xdg_view->commit.notify = qw_xdg_view_handle_commit;
    wl_signal_add(&xdg_toplevel->base->surface->events.commit, &xdg_view->commit);

    xdg_view->destroy.notify = qw_xdg_view_handle_destroy;
    wl_signal_add(&xdg_toplevel->events.destroy, &xdg_view->destroy);
}
