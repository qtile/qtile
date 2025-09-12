#include "xdg-view.h"
#include "server.h"
#include "util.h"
#include "view.h"
#include "wayland-server-core.h"
#include "wayland-util.h"
#include "wlr/types/wlr_xdg_decoration_v1.h"
#include "xdg-shell-protocol.h"
#include <stdlib.h>

// Focus the given xdg_view's surface, managing activation and keyboard focus
static void qw_xdg_view_do_focus(struct qw_xdg_view *xdg_view, struct wlr_surface *surface) {
    if (!xdg_view) {
        return;
    }

    struct qw_server *server = xdg_view->base.server;
    struct wlr_seat *seat = server->seat;
    struct wlr_surface *prev_surface = seat->keyboard_state.focused_surface;

    if (prev_surface == surface) {
        return;
    }

    // Deactivate previous surface if any
    if (prev_surface) {
        qw_util_deactivate_surface(prev_surface);
    }

    wlr_xdg_toplevel_set_activated(xdg_view->xdg_toplevel, true);
    wlr_foreign_toplevel_handle_v1_set_activated(xdg_view->base.ftl_handle, true);

    // Notify keyboard about entering this surface (for keyboard input)
    struct wlr_keyboard *keyboard = wlr_seat_get_keyboard(seat);
    if (keyboard) {
        wlr_seat_keyboard_notify_enter(seat, xdg_view->xdg_toplevel->base->surface,
                                       keyboard->keycodes, keyboard->num_keycodes,
                                       &keyboard->modifiers);
    }

    xdg_view->is_urgent = false;
}

// Handle the unmap event for the xdg_view (when it's hidden/unmapped)
static void qw_xdg_view_handle_unmap(struct wl_listener *listener, void *data) {
    struct qw_xdg_view *xdg_view = wl_container_of(listener, xdg_view, unmap);
    qw_view_cleanup_borders((struct qw_view *)xdg_view);
    xdg_view->base.server->unmanage_view_cb((struct qw_view *)&xdg_view->base,
                                            xdg_view->base.server->cb_data);
}

// Handle the destroy event of the xdg_view (cleanup and free memory)
static void qw_xdg_view_handle_destroy(struct wl_listener *listener, void *data) {
    struct qw_xdg_view *xdg_view = wl_container_of(listener, xdg_view, destroy);

    wl_list_remove(&xdg_view->map.link);
    wl_list_remove(&xdg_view->unmap.link);
    wl_list_remove(&xdg_view->commit.link);
    wl_list_remove(&xdg_view->destroy.link);
    wl_list_remove(&xdg_view->request_maximize.link);
    wl_list_remove(&xdg_view->request_fullscreen.link);
    wl_list_remove(&xdg_view->set_title.link);
    wl_list_remove(&xdg_view->set_app_id.link);
    // TODO: Remove request_move and request_resize listeners if added

    // Destroy the foreign toplevel manager and listeners
    qw_view_ftl_manager_handle_destroy(&xdg_view->base);

    wlr_scene_node_destroy(&xdg_view->base.content_tree->node);

    free(xdg_view);
}

// Handle map event: when the xdg_view becomes visible/mapped
static void qw_xdg_view_handle_map(struct wl_listener *listener, void *data) {
    struct qw_xdg_view *xdg_view = wl_container_of(listener, xdg_view, map);
    xdg_view->mapped = true;

    struct wlr_xdg_surface *surface = xdg_view->xdg_toplevel->base;
    struct wlr_box geom = surface->geometry;
    xdg_view->base.width = geom.width;
    xdg_view->base.height = geom.height;

    // Set foreign top level attributes
    if (xdg_view->base.ftl_handle != NULL) {
        if (xdg_view->base.title != NULL) {
            wlr_foreign_toplevel_handle_v1_set_title(xdg_view->base.ftl_handle,
                                                     xdg_view->base.title);
        }
        if (xdg_view->base.app_id != NULL) {
            wlr_foreign_toplevel_handle_v1_set_app_id(xdg_view->base.ftl_handle,
                                                      xdg_view->base.app_id);
        }
        struct wlr_xdg_toplevel *toplevel = xdg_view->xdg_toplevel;
        if (toplevel->parent != NULL) {
            struct qw_xdg_view *parent_view = toplevel->parent->base->data;
            if (parent_view->base.ftl_handle != NULL) {
                wlr_foreign_toplevel_handle_v1_set_parent(xdg_view->base.ftl_handle,
                                                          parent_view->base.ftl_handle);
            }
        }
    }

    xdg_view->base.server->manage_view_cb((struct qw_view *)&xdg_view->base,
                                          xdg_view->base.server->cb_data);

    // Focus the view upon mapping
    qw_xdg_view_do_focus(xdg_view, xdg_view->xdg_toplevel->base->surface);

    // If the protocol version supports tiled state, set tiled on all edges
    if (wl_resource_get_version(xdg_view->xdg_toplevel->resource) >=
        XDG_TOPLEVEL_STATE_TILED_RIGHT_SINCE_VERSION) {
        wlr_xdg_toplevel_set_tiled(xdg_view->xdg_toplevel,
                                   WLR_EDGE_TOP | WLR_EDGE_BOTTOM | WLR_EDGE_LEFT | WLR_EDGE_RIGHT);
    } else {
        // Otherwise maximize as fallback for older clients
        wlr_xdg_toplevel_set_maximized(xdg_view->xdg_toplevel, true);
    }
}

// Handle commit event: called when surface commits state changes
static void qw_xdg_view_handle_commit(struct wl_listener *listener, void *data) {
    struct qw_xdg_view *xdg_view = wl_container_of(listener, xdg_view, commit);

    // On initial commit, set size and notify server to manage this view
    if (xdg_view->xdg_toplevel->base->initial_commit) {
        wlr_xdg_toplevel_set_size(xdg_view->xdg_toplevel, 0, 0);
        xdg_view->base.title = xdg_view->xdg_toplevel->title;
        xdg_view->base.app_id = xdg_view->xdg_toplevel->app_id;
    }
}

// Clip the xdg_view's scene tree if needed
static void qw_xdg_view_clip(struct qw_xdg_view *xdg_view) {
    // Only clip if scene_tree exists, node is disabled, and node is linked
    if (!xdg_view->scene_tree) {
        return;
    }
    if (xdg_view->scene_tree->node.enabled) {
        return;
    }
    if (!xdg_view->scene_tree->node.link.next) {
        return;
    }

    // clang-format off
    struct wlr_box clip = {
        .x = xdg_view->geom.x,
        .y = xdg_view->geom.y,
        .width = xdg_view->base.width,
        .height = xdg_view->base.height
    };
    // clang-format on

    // Apply clipping to subsurface tree
    wlr_scene_subsurface_tree_set_clip(&xdg_view->scene_tree->node, &clip);
}

// Place the xdg_view at given position and size with border and stacking info
static void qw_xdg_view_place(void *self, int x, int y, int width, int height,
                              const struct qw_border *borders, int border_count, int above) {
    struct qw_xdg_view *xdg_view = (struct qw_xdg_view *)self;
    struct wlr_xdg_surface *surface = xdg_view->xdg_toplevel->base;
    struct wlr_xdg_toplevel_state state = xdg_view->xdg_toplevel->current;

    // Check if placement or geometry changed
    bool place_changed = xdg_view->base.x != x || xdg_view->base.y != y ||
                         xdg_view->base.width != width || xdg_view->base.height != height ||
                         state.width != width || state.height != height;

    struct wlr_box geom = surface->geometry;
    bool geom_changed = xdg_view->geom.x != geom.x || xdg_view->geom.y != geom.y ||
                        xdg_view->geom.width != geom.width || xdg_view->geom.height != geom.height;

    bool needs_repos = place_changed || geom_changed;

    // Update stored geometry and base view rectangle
    xdg_view->geom = geom;
    xdg_view->base.x = x;
    xdg_view->base.y = y;
    xdg_view->base.width = width;
    xdg_view->base.height = height;

    // Set position of the content scene node
    wlr_scene_node_set_position(&xdg_view->base.content_tree->node, x, y);

    if (needs_repos) {
        // Resize the toplevel surface and apply clipping if needed
        wlr_xdg_toplevel_set_size(xdg_view->xdg_toplevel, width, height);
        qw_xdg_view_clip(xdg_view);

        // Resize the foreign toplevel output tracking buffer
        qw_view_resize_ftl_output_tracking_buffer(&xdg_view->base, width, height);
    }

    // Paint borders around the view with given border colors and width
    qw_view_paint_borders((struct qw_view *)xdg_view, borders, border_count);

    // Raise view to front if requested
    if (above != 0) {
        qw_view_reparent(&xdg_view->base, LAYER_BRINGTOFRONT);
    }
}

// Send close event to the xdg_toplevel surface (kill the view)
static void qw_xdg_view_kill(void *self) {
    struct qw_xdg_view *xdg_view = (struct qw_xdg_view *)self;
    wlr_xdg_toplevel_send_close(xdg_view->xdg_toplevel);
}

// Hide the xdg_view (disable scene node and clear keyboard focus if needed)
static void qw_xdg_view_hide(void *self) {
    struct qw_xdg_view *xdg_view = (struct qw_xdg_view *)self;
    wlr_scene_node_set_enabled(&xdg_view->base.content_tree->node, false);

    // Clear keyboard focus if this view was focused
    if (xdg_view->xdg_toplevel->base->surface ==
        xdg_view->base.server->seat->keyboard_state.focused_surface) {
        wlr_seat_keyboard_clear_focus(xdg_view->base.server->seat);
    }
}

// Unhide the xdg_view by enabling its content_tree scene node if currently disabled
static void qw_xdg_view_unhide(void *self) {
    struct qw_xdg_view *xdg_view = (struct qw_xdg_view *)self;
    if (!xdg_view->base.content_tree->node.enabled) {
        wlr_scene_node_set_enabled(&xdg_view->base.content_tree->node, true);
    }
}

// Focus the xdg_view if it is mapped (visible), calling internal focus helper
void qw_xdg_view_focus(void *self, int above) {
    struct qw_xdg_view *xdg_view = (struct qw_xdg_view *)self;
    if (!xdg_view->mapped) {
        return; // Can't focus if not mapped
    }
    qw_xdg_view_do_focus(xdg_view, xdg_view->xdg_toplevel->base->surface);
    if (xdg_view->is_urgent) {
        xdg_view->is_urgent = false;
    }
}

// Retrieve the PID of the client owning this xdg_view
static int qw_xdg_view_get_pid(void *self) {
    struct qw_xdg_view *xdg_view = (struct qw_xdg_view *)self;
    int pid;
    wl_client_get_credentials(xdg_view->xdg_toplevel->base->client->client, &pid, NULL, NULL);
    return pid;
}

// Handle a request from the client to maximize the window
static void qw_xdg_view_handle_request_maximize(struct wl_listener *listener, void *data) {
    struct qw_xdg_view *xdg_view = wl_container_of(listener, xdg_view, request_maximize);
    int handled = xdg_view->base.request_maximize_cb(xdg_view->xdg_toplevel->requested.maximized,
                                                     xdg_view->base.cb_data);
    if (!handled) {
        // If not handled, fallback to scheduling configure to apply maximize
        wlr_xdg_surface_schedule_configure(xdg_view->xdg_toplevel->base);
    }
}

// Handle a request from the client to fullscreen the window
static void qw_xdg_view_handle_request_fullscreen(struct wl_listener *listener, void *data) {
    struct qw_xdg_view *xdg_view = wl_container_of(listener, xdg_view, request_fullscreen);
    int handled = xdg_view->base.request_fullscreen_cb(xdg_view->xdg_toplevel->requested.fullscreen,
                                                       xdg_view->base.cb_data);
    if (!handled) {
        // Fallback configure if request not handled
        wlr_xdg_surface_schedule_configure(xdg_view->xdg_toplevel->base);
    }
}

static void qw_xdg_view_handle_set_title(struct wl_listener *listener, void *data) {
    struct qw_xdg_view *xdg_view = wl_container_of(listener, xdg_view, set_title);
    xdg_view->base.title = xdg_view->xdg_toplevel->title;
    if (xdg_view->base.ftl_handle != NULL && xdg_view->base.title != NULL) {
        wlr_foreign_toplevel_handle_v1_set_title(xdg_view->base.ftl_handle, xdg_view->base.title);
    }
    // callback is not intialised until qtile window is initialised
    if (xdg_view->base.set_title_cb && xdg_view->base.title) {
        xdg_view->base.set_title_cb(xdg_view->base.title, xdg_view->base.cb_data);
    }
}

static void qw_xdg_view_handle_set_app_id(struct wl_listener *listener, void *data) {
    struct qw_xdg_view *xdg_view = wl_container_of(listener, xdg_view, set_app_id);
    xdg_view->base.app_id = xdg_view->xdg_toplevel->app_id;
    if (xdg_view->base.ftl_handle != NULL && xdg_view->base.app_id != NULL) {
        wlr_foreign_toplevel_handle_v1_set_app_id(xdg_view->base.ftl_handle, xdg_view->base.app_id);
    }
    // callback is not intialised until qtile window is initialised
    if (xdg_view->base.set_app_id_cb && xdg_view->base.app_id) {
        xdg_view->base.set_app_id_cb(xdg_view->base.app_id, xdg_view->base.cb_data);
    }
}

// Handle client decoration mode requests, enforce server-side decorations
static void qw_xdg_view_handle_decoration_request_mode(struct wl_listener *listener, void *data) {
    struct qw_xdg_view *xdg_view = wl_container_of(listener, xdg_view, decoration_request_mode);
    if (xdg_view->xdg_toplevel->base->initialized)
        wlr_xdg_toplevel_decoration_v1_set_mode(xdg_view->decoration,
                                                WLR_XDG_TOPLEVEL_DECORATION_V1_MODE_SERVER_SIDE);
}

// Cleanup listeners when decoration is destroyed to avoid dangling pointers
static void qw_xdg_view_handle_decoration_destroy(struct wl_listener *listener, void *data) {
    struct qw_xdg_view *xdg_view = wl_container_of(listener, xdg_view, decoration_destroy);

    wl_list_remove(&xdg_view->decoration_destroy.link);
    wl_list_remove(&xdg_view->decoration_request_mode.link);
}

// Initialize decoration handling for a new decoration object
void qw_xdg_view_decoration_new(struct qw_xdg_view *xdg_view,
                                struct wlr_xdg_toplevel_decoration_v1 *decoration) {
    xdg_view->decoration = decoration;
    xdg_view->decoration_request_mode.notify = qw_xdg_view_handle_decoration_request_mode;
    wl_signal_add(&decoration->events.request_mode, &xdg_view->decoration_request_mode);
    xdg_view->decoration_destroy.notify = qw_xdg_view_handle_decoration_destroy;
    wl_signal_add(&decoration->events.destroy, &xdg_view->decoration_destroy);

    // Immediately set decoration mode upon creation
    qw_xdg_view_handle_decoration_request_mode(&xdg_view->decoration_request_mode, decoration);
}

// Return the scene node for this view's scene tree, or NULL if none exists
static struct wlr_scene_node *qw_xdg_view_get_tree_node(void *self) {
    struct qw_xdg_view *xdg_view = (struct qw_xdg_view *)self;
    if (!xdg_view->scene_tree) {
        return NULL;
    }
    return &xdg_view->scene_tree->node;
}

// Update fullscreen state of the toplevel surface
static void qw_xdg_view_update_fullscreen(void *self, bool fullscreen) {
    struct qw_xdg_view *xdg_view = (struct qw_xdg_view *)self;
    wlr_xdg_toplevel_set_fullscreen(xdg_view->xdg_toplevel, fullscreen);
    wlr_foreign_toplevel_handle_v1_set_fullscreen(xdg_view->base.ftl_handle, fullscreen);
}

// Update maximized state of the toplevel surface
static void qw_xdg_view_update_maximized(void *self, bool maximized) {
    struct qw_xdg_view *xdg_view = (struct qw_xdg_view *)self;
    wlr_xdg_toplevel_set_maximized(xdg_view->xdg_toplevel, maximized);
    wlr_foreign_toplevel_handle_v1_set_maximized(xdg_view->base.ftl_handle, maximized);
}

static void qw_xdg_view_update_minimized(void *self, bool minimized) {
    struct qw_xdg_view *xdg_view = (struct qw_xdg_view *)self;
    wlr_foreign_toplevel_handle_v1_set_minimized(xdg_view->base.ftl_handle, minimized);
}

static void qw_xdg_activation_token_destroy(struct wl_listener *listener, void *data) {
    struct qw_xdg_activation_token *token_data = wl_container_of(listener, token_data, destroy);
    wl_list_remove(&token_data->destroy.link);
    free(token_data);
}

void qw_xdg_activation_new_token(struct wl_listener *listener, void *data) {
    struct wlr_xdg_activation_token_v1 *token = data;
    struct qw_xdg_activation_token *token_data = calloc(1, sizeof(struct qw_xdg_activation_token));

    if (token_data == NULL) {
        wlr_log(WLR_ERROR, "Failed to allocate token data");
        return;
    }

    // Assign boolean values
    token_data->qw_valid_surface = token->surface != NULL;
    token_data->qw_valid_seat = token->seat != NULL;

    token->data = token_data;

    token_data->destroy.notify = qw_xdg_activation_token_destroy;
    wl_signal_add(&token->events.destroy, &token_data->destroy);
}

// Create a new qw_xdg_view for a given wlr_xdg_toplevel, setting up scene tree, listeners, and
// callbacks
void qw_server_xdg_view_new(struct qw_server *server, struct wlr_xdg_toplevel *xdg_toplevel) {
    struct qw_xdg_view *xdg_view = calloc(1, sizeof(*xdg_view));
    if (!xdg_view) {
        wlr_log(WLR_ERROR, "failed to create qw_xdg_view struct");
        return;
    }

    struct wlr_box geom = {.x = 0, .y = 0, .width = 0, .height = 0};
    xdg_view->geom = geom;
    xdg_view->base.server = server;
    xdg_view->xdg_toplevel = xdg_toplevel;

    xdg_view->base.shell = "XDG";
    xdg_view->base.view_type = QW_VIEW_XDG;
    // Create a scene tree node for this view inside the main layout tree
    xdg_view->base.content_tree = wlr_scene_tree_create(server->scene_windows_layers[LAYER_LAYOUT]);
    xdg_view->base.content_tree->node.data = xdg_view;
    xdg_view->base.layer = LAYER_LAYOUT;

    // If the protocol version supports WM capabilities, set maximize/fullscreen/minimize
    if (wl_resource_get_version(xdg_view->xdg_toplevel->resource) >=
        XDG_TOPLEVEL_WM_CAPABILITIES_SINCE_VERSION) {

        // clang-format off
        wlr_xdg_toplevel_set_wm_capabilities(
            xdg_toplevel,
            XDG_TOPLEVEL_WM_CAPABILITIES_MAXIMIZE |
            XDG_TOPLEVEL_WM_CAPABILITIES_FULLSCREEN |
            XDG_TOPLEVEL_WM_CAPABILITIES_MINIMIZE
        );
        // clang-format on
    }

    // Create scene node for the toplevel surface under the content tree
    xdg_view->scene_tree =
        wlr_scene_xdg_surface_create(xdg_view->base.content_tree, xdg_toplevel->base);
    xdg_toplevel->base->data = xdg_view;

    // Assign function pointers for base view operations
    xdg_view->base.get_tree_node = qw_xdg_view_get_tree_node;
    xdg_view->base.update_fullscreen = qw_xdg_view_update_fullscreen;
    xdg_view->base.update_maximized = qw_xdg_view_update_maximized;
    xdg_view->base.update_minimized = qw_xdg_view_update_minimized;
    xdg_view->base.place = qw_xdg_view_place;
    xdg_view->base.focus = qw_xdg_view_focus;
    xdg_view->base.get_pid = qw_xdg_view_get_pid;
    xdg_view->base.kill = qw_xdg_view_kill;
    xdg_view->base.hide = qw_xdg_view_hide;
    xdg_view->base.unhide = qw_xdg_view_unhide;

    // Add listeners for surface lifecycle events (map, unmap, commit)
    xdg_view->map.notify = qw_xdg_view_handle_map;
    wl_signal_add(&xdg_toplevel->base->surface->events.map, &xdg_view->map);
    xdg_view->unmap.notify = qw_xdg_view_handle_unmap;
    wl_signal_add(&xdg_toplevel->base->surface->events.unmap, &xdg_view->unmap);
    xdg_view->commit.notify = qw_xdg_view_handle_commit;
    wl_signal_add(&xdg_toplevel->base->surface->events.commit, &xdg_view->commit);

    // Add listener for toplevel destroy event
    xdg_view->destroy.notify = qw_xdg_view_handle_destroy;
    wl_signal_add(&xdg_toplevel->events.destroy, &xdg_view->destroy);

    // Add listeners for maximize and fullscreen requests
    xdg_view->request_maximize.notify = qw_xdg_view_handle_request_maximize;
    wl_signal_add(&xdg_toplevel->events.request_maximize, &xdg_view->request_maximize);
    xdg_view->request_fullscreen.notify = qw_xdg_view_handle_request_fullscreen;
    wl_signal_add(&xdg_toplevel->events.request_fullscreen, &xdg_view->request_fullscreen);

    xdg_view->set_title.notify = qw_xdg_view_handle_set_title;
    wl_signal_add(&xdg_toplevel->events.set_title, &xdg_view->set_title);

    xdg_view->set_app_id.notify = qw_xdg_view_handle_set_app_id;
    wl_signal_add(&xdg_toplevel->events.set_app_id, &xdg_view->set_app_id);

    // Create foreign toplevel manager and listeners
    qw_view_ftl_manager_handle_create(&xdg_view->base);
}
