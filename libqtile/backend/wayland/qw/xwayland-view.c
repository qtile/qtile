#include "xwayland-view.h"
#include "server.h"
#include "session-lock.h"
#include "util.h"
#include "view.h"
#include "wayland-server-core.h"
#include "wayland-util.h"
#include "wlr/util/log.h"
#include "xdg-view.h"

#include <stdint.h>
#include <stdlib.h>
#include <wlr/xwayland.h>
#include <xcb/xcb_icccm.h>

// Change xwayland surface activate state
static void qw_xwayland_view_activate(struct qw_xwayland_view *xwayland_view, bool activate) {
    wlr_xwayland_surface_activate(xwayland_view->xwayland_surface, activate);
    if (xwayland_view->base.ftl_handle != NULL) {
        wlr_foreign_toplevel_handle_v1_set_activated(xwayland_view->base.ftl_handle, activate);
    }
}

static void qw_xwayland_view_do_focus(struct qw_xwayland_view *xwayland_view,
                                      struct wlr_surface *surface) {
    if (!xwayland_view) {
        return;
    }

    struct qw_server *server = xwayland_view->base.server;
    struct wlr_seat *seat = server->seat;
    struct wlr_surface *prev_surface = seat->keyboard_state.focused_surface;

    if (server->lock_state != QW_SESSION_LOCK_UNLOCKED) {
        return;
    }

    if (prev_surface == surface) {
        return;
    }

    wlr_scene_node_raise_to_top(&xwayland_view->base.content_tree->node);

    // Deactivate previous surface if any
    if (prev_surface != NULL) {
        qw_util_deactivate_surface(prev_surface);
    }

    qw_xwayland_view_activate(xwayland_view, true);

    // Notify keyboard about entering this surface (for keyboard input)
    struct wlr_keyboard *keyboard = wlr_seat_get_keyboard(seat);
    if (keyboard) {
        wlr_seat_keyboard_notify_enter(seat, xwayland_view->xwayland_surface->surface,
                                       keyboard->keycodes, keyboard->num_keycodes,
                                       &keyboard->modifiers);
    }
}

static void qw_xwayland_view_focus(void *self, int above) {
    UNUSED(above);
    struct qw_xwayland_view *xwayland_view = (struct qw_xwayland_view *)self;
    if (!xwayland_view->xwayland_surface->surface->mapped) {
        return; // Can't focus if not mapped
    }
    qw_xwayland_view_do_focus(xwayland_view, xwayland_view->xwayland_surface->surface);
}

static void static_view_handle_destroy(struct wl_listener *listener, void *data) {
    UNUSED(data);
    struct qw_xwayland_view *static_view = wl_container_of(listener, static_view, destroy);

    wl_list_remove(&static_view->destroy.link);
    wl_list_remove(&static_view->associate.link);
    wl_list_remove(&static_view->dissociate.link);
    wl_list_remove(&static_view->request_configure.link);
    wl_list_remove(&static_view->request_activate.link);
    wl_list_remove(&static_view->override_redirect.link);

    free(static_view);
}

static void static_view_handle_set_geometry(struct wl_listener *listener, void *data) {
    UNUSED(data);
    struct qw_xwayland_view *static_view = wl_container_of(listener, static_view, set_geometry);
    struct wlr_xwayland_surface *xwayland_surface = static_view->xwayland_surface;

    wlr_scene_node_set_position(&static_view->scene_tree->node, xwayland_surface->x,
                                xwayland_surface->y);
}

static void static_view_handle_map(struct wl_listener *listener, void *data) {
    UNUSED(data);
    struct qw_xwayland_view *static_view = wl_container_of(listener, static_view, map);
    struct wlr_xwayland_surface *xwayland_surface = static_view->xwayland_surface;

    // Create a subsurface tree for this view under the content tree.
    static_view->scene_tree =
        wlr_scene_subsurface_tree_create(static_view->base.content_tree, xwayland_surface->surface);

    if (static_view->scene_tree != NULL) {
        wlr_scene_node_set_position(&static_view->scene_tree->node, xwayland_surface->x,
                                    xwayland_surface->y);
        wl_signal_add(&xwayland_surface->events.set_geometry, &static_view->set_geometry);
        static_view->set_geometry.notify = static_view_handle_set_geometry;
    }

    if (wlr_xwayland_surface_override_redirect_wants_focus(xwayland_surface)) {
        qw_xwayland_view_focus(static_view, true);
    }
}

static void static_view_handle_unmap(struct wl_listener *listener, void *data) {
    UNUSED(data);
    struct qw_xwayland_view *static_view = wl_container_of(listener, static_view, unmap);
    struct wlr_xwayland_surface *xwayland_surface = static_view->xwayland_surface;

    if (static_view->scene_tree != NULL) {
        wl_list_remove(&static_view->set_geometry.link);
        wlr_scene_node_destroy(&static_view->scene_tree->node);
        static_view->scene_tree = NULL;
    }

    struct wlr_seat *seat = static_view->base.server->seat;
    if (seat->keyboard_state.focused_surface == xwayland_surface->surface) {
        // This simply returns focus to the parent surface if there's one available.
        // This seems to handle JetBrains issues.
        if (xwayland_surface->parent && xwayland_surface->parent->surface &&
            wlr_xwayland_surface_override_redirect_wants_focus(xwayland_surface->parent)) {
            qw_xwayland_view_focus(xwayland_surface->parent->data, true);
            return;
        }

        // Restore focus
        static_view->base.server->focus_current_window_cb(static_view->base.server->cb_data);
    }
}

static void static_view_handle_associate(struct wl_listener *listener, void *data) {
    UNUSED(data);
    struct qw_xwayland_view *static_view = wl_container_of(listener, static_view, associate);
    struct wlr_xwayland_surface *xwayland_surface = static_view->xwayland_surface;

    // Attach map and unmap listeners to the new surface events.
    wl_signal_add(&xwayland_surface->surface->events.unmap, &static_view->unmap);
    static_view->unmap.notify = static_view_handle_unmap;
    wl_signal_add(&xwayland_surface->surface->events.map, &static_view->map);
    static_view->map.notify = static_view_handle_map;
}

static void static_view_handle_dissociate(struct wl_listener *listener, void *data) {
    UNUSED(data);
    struct qw_xwayland_view *static_view = wl_container_of(listener, static_view, dissociate);
    wl_list_remove(&static_view->map.link);
    wl_list_remove(&static_view->unmap.link);
}

static void static_view_handle_request_configure(struct wl_listener *listener, void *data) {
    struct qw_xwayland_view *static_view =
        wl_container_of(listener, static_view, request_configure);
    struct wlr_xwayland_surface_configure_event *event = data;
    struct wlr_xwayland_surface *xwayland_surface = static_view->xwayland_surface;

    wlr_xwayland_surface_configure(xwayland_surface, event->x, event->y, event->width,
                                   event->height);
}

static void static_view_handle_request_activate(struct wl_listener *listener, void *data) {
    UNUSED(data);
    struct qw_xwayland_view *static_view = wl_container_of(listener, static_view, request_activate);

    qw_xwayland_view_activate(static_view, true);
}

// forward declarations
void qw_server_xwayland_view_new(struct qw_server *server,
                                 struct wlr_xwayland_surface *xwayland_surface);
static void qw_xwayland_view_handle_map(struct wl_listener *listener, void *data);
static void qw_xwayland_view_handle_associate(struct wl_listener *listener, void *data);

static void static_view_handle_override_redirect(struct wl_listener *listener, void *data) {
    UNUSED(data);
    struct qw_xwayland_view *static_view =
        wl_container_of(listener, static_view, override_redirect);
    struct wlr_xwayland_surface *xwayland_surface = static_view->xwayland_surface;
    struct qw_server *server = static_view->base.server;

    bool associated = xwayland_surface->surface != NULL;
    bool mapped = associated && xwayland_surface->surface->mapped;
    if (mapped) {
        static_view_handle_unmap(&static_view->unmap, NULL);
    }
    if (associated) {
        static_view_handle_dissociate(&static_view->dissociate, NULL);
    }

    static_view_handle_destroy(&static_view->destroy, NULL);
    xwayland_surface->data = NULL;

    qw_server_xwayland_view_new(server, xwayland_surface);
    struct qw_xwayland_view *xwayland_view = xwayland_surface->data;
    if (associated) {
        qw_xwayland_view_handle_associate(&xwayland_view->associate, NULL);
    }
    if (mapped) {
        qw_xwayland_view_handle_map(&xwayland_view->map, xwayland_surface);
    }
}

void qw_server_xwayland_static_view_new(struct qw_server *server,
                                        struct wlr_xwayland_surface *xwayland_surface) {
    struct qw_xwayland_view *static_view = calloc(1, sizeof(*static_view));
    if (!static_view) {
        wlr_log(WLR_ERROR, "failed to create qw_xwayland_static_view struct");
        return;
    }

    static_view->xwayland_surface = xwayland_surface;
    static_view->base.server = server;

    // Create a scene tree node for this view that brings it to front
    static_view->base.content_tree =
        wlr_scene_tree_create(server->scene_windows_layers[LAYER_BRINGTOFRONT]);

    wl_signal_add(&xwayland_surface->events.destroy, &static_view->destroy);
    static_view->destroy.notify = static_view_handle_destroy;

    wl_signal_add(&xwayland_surface->events.associate, &static_view->associate);
    static_view->associate.notify = static_view_handle_associate;

    wl_signal_add(&xwayland_surface->events.dissociate, &static_view->dissociate);
    static_view->dissociate.notify = static_view_handle_dissociate;

    wl_signal_add(&xwayland_surface->events.request_configure, &static_view->request_configure);
    static_view->request_configure.notify = static_view_handle_request_configure;

    wl_signal_add(&xwayland_surface->events.request_activate, &static_view->request_activate);
    static_view->request_activate.notify = static_view_handle_request_activate;

    wl_signal_add(&xwayland_surface->events.set_override_redirect, &static_view->override_redirect);
    static_view->override_redirect.notify = static_view_handle_override_redirect;

    xwayland_surface->data = static_view;
}

static struct wlr_scene_node *qw_xwayland_view_get_tree_node(void *self) {
    struct qw_xwayland_view *xwayland_view = (struct qw_xwayland_view *)self;

    if (xwayland_view->scene_tree == NULL) {
        return NULL;
    }

    return &xwayland_view->scene_tree->node;
}

// Bring the xwayland_view's content scene node to the front
static void qw_xwayland_view_bring_to_front(void *self) {
    struct qw_xwayland_view *xwayland_view = (struct qw_xwayland_view *)self;
    wlr_scene_node_raise_to_top(&xwayland_view->base.content_tree->node);
}

// Clip the xwayland_view's scene tree if needed
static void qw_xwayland_view_clip(struct qw_xwayland_view *xwayland_view) {
    // Only clip if scene_tree exists, node is disabled, and node is linked
    if (!xwayland_view->scene_tree) {
        return;
    }
    if (xwayland_view->scene_tree->node.enabled) {
        return;
    }
    if (!xwayland_view->scene_tree->node.link.next) {
        return;
    }

    // clang-format off
    struct wlr_box clip = {
        .x = xwayland_view->geom.x,
        .y = xwayland_view->geom.y,
        .width = xwayland_view->base.width,
        .height = xwayland_view->base.height
    };
    // clang-format on

    wlr_scene_subsurface_tree_set_clip(&xwayland_view->scene_tree->node, &clip);
}

// Place the xwayland_view at given position and size with border and stacking info
static void qw_xwayland_view_place(void *self, int x, int y, int width, int height,
                                   const struct qw_border *borders, int border_count, int above) {
    struct qw_xwayland_view *xwayland_view = (struct qw_xwayland_view *)self;
    struct wlr_xwayland_surface *qw_xsurface = xwayland_view->xwayland_surface;

    // Check if placement or geometry changed
    bool place_changed = xwayland_view->base.x != x || xwayland_view->base.y != y ||
                         xwayland_view->base.width != width || xwayland_view->base.height != height;

    // For XWayland, we need to check the surface geometry differently
    // clang-format off
    struct wlr_box geom = {
        .x = qw_xsurface->x, 
        .y = qw_xsurface->y, 
        .width = qw_xsurface->width, 
        .height = qw_xsurface->height
    };
    // clang-format on

    bool geom_changed = xwayland_view->geom.x != geom.x || xwayland_view->geom.y != geom.y ||
                        xwayland_view->geom.width != geom.width ||
                        xwayland_view->geom.height != geom.height;

    bool needs_repos = place_changed || geom_changed;

    // Update stored geometry and base view rectangle
    xwayland_view->geom = geom;
    xwayland_view->base.x = x;
    xwayland_view->base.y = y;
    xwayland_view->base.width = width;
    xwayland_view->base.height = height;

    // Set position of the content scene node
    wlr_scene_node_set_position(&xwayland_view->base.content_tree->node, x, y);

    // TODO: don't force repo
    if (needs_repos) {
        // For XWayland, we configure the surface position and size
        wlr_xwayland_surface_configure(qw_xsurface, x, y, width, height);
        qw_xwayland_view_clip(xwayland_view);

        // Resize the foreign toplevel output tracking buffer
        qw_view_resize_ftl_output_tracking_buffer(&xwayland_view->base, width, height);
    }

    // Paint borders around the view with given border colors and width
    qw_view_paint_borders((struct qw_view *)xwayland_view, borders, border_count);

    // Raise view to front if requested
    if (above != 0) {
        qw_xwayland_view_bring_to_front(self);
    }
}

// Send close event to the xwayland surface (kill the view)
static void qw_xwayland_view_kill(void *self) {
    struct qw_xwayland_view *xwayland_view = (struct qw_xwayland_view *)self;
    wlr_xwayland_surface_close(xwayland_view->xwayland_surface);
}

// Hide the xwayland_view (disable scene node and clear keyboard focus if needed)
static void qw_xwayland_view_hide(void *self) {
    struct qw_xwayland_view *xwayland_view = (struct qw_xwayland_view *)self;
    wlr_scene_node_set_enabled(&xwayland_view->base.content_tree->node, false);
    qw_xwayland_view_activate(xwayland_view, false);

    // Clear keyboard focus if this view was focused
    if (xwayland_view->xwayland_surface->surface ==
        xwayland_view->base.server->seat->keyboard_state.focused_surface) {
        wlr_seat_keyboard_clear_focus(xwayland_view->base.server->seat);
    }
}

// Unhide the xwayland_view by enabling its content_tree scene node if currently disabled
static void qw_xwayland_view_unhide(void *self) {
    struct qw_xwayland_view *xwayland_view = (struct qw_xwayland_view *)self;
    if (!xwayland_view->base.content_tree->node.enabled) {
        wlr_scene_node_set_enabled(&xwayland_view->base.content_tree->node, true);
    }
}

// Retrieve the PID of the client owning this xwayland_view
static int qw_xwayland_view_get_pid(void *self) {
    struct qw_xwayland_view *xwayland_view = (struct qw_xwayland_view *)self;
    return xwayland_view->xwayland_surface->pid;
}

// Returns a string containing the window type
// Uses the same string names as the x11 backend
static const char *qw_xwayland_view_get_window_type(void *self) {
    struct qw_xwayland_view *xwayland_view = (struct qw_xwayland_view *)self;
    struct qw_server *server = xwayland_view->base.server;
    xcb_atom_t *atoms = server->xwayland_atoms;
    struct wlr_xwayland_surface *xwayland_surface = xwayland_view->xwayland_surface;

    for (size_t i = 0; i < xwayland_surface->window_type_len; i++) {
        xcb_atom_t t = xwayland_surface->window_type[i];
        if (t == atoms[NET_WM_WINDOW_TYPE_DIALOG])
            return "dialog";
        else if (t == atoms[NET_WM_WINDOW_TYPE_UTILITY])
            return "utility";
        else if (t == atoms[NET_WM_WINDOW_TYPE_TOOLBAR])
            return "toolbar";
        else if (t == atoms[NET_WM_WINDOW_TYPE_MENU] || t == atoms[NET_WM_WINDOW_TYPE_POPUP_MENU])
            return "menu";
        else if (t == atoms[NET_WM_WINDOW_TYPE_SPLASH])
            return "splash";
        else if (t == atoms[NET_WM_WINDOW_TYPE_DOCK])
            return "dock";
        else if (t == atoms[NET_WM_WINDOW_TYPE_TOOLTIP])
            return "tooltip";
        else if (t == atoms[NET_WM_WINDOW_TYPE_NOTIFICATION])
            return "notification";
        else if (t == atoms[NET_WM_WINDOW_TYPE_DESKTOP])
            return "desktop";
        else if (t == atoms[NET_WM_WINDOW_TYPE_DROPDOWN_MENU])
            return "dropdown";
        else if (t == atoms[NET_WM_WINDOW_TYPE_COMBO])
            return "combo";
        else if (t == atoms[NET_WM_WINDOW_TYPE_DND])
            return "dnd";
        if (t == atoms[NET_WM_WINDOW_TYPE_NORMAL])
            return "normal";
    }

    // Fallback if no known type found
    return "normal";
}

// Retrieve the WID of the parent window (return 0 if none)
static int qw_xwayland_get_parent(void *self) {
    struct qw_xwayland_view *xwayland_view = (struct qw_xwayland_view *)self;
    if (xwayland_view == NULL || xwayland_view->xwayland_surface == NULL) {
        return 0;
    }

    struct wlr_xwayland_surface *parent_surface = xwayland_view->xwayland_surface->parent;
    if (parent_surface == NULL) {
        return 0;
    }

    struct qw_xwayland_view *parent_view = parent_surface->data;
    if (parent_view == NULL) {
        return 0;
    }

    return parent_view->base.wid;
}

// Handle commit event: called when XWayland surface commits state changes
static void qw_xwayland_view_handle_commit(struct wl_listener *listener, void *data) {
    UNUSED(data);
    struct qw_xwayland_view *xwayland_view = wl_container_of(listener, xwayland_view, commit);
    // For XWayland, we don't need to check for initial_commit or manage the view here
    // The view is already managed when it's mapped (see qw_xwayland_view_map)
    // This commit handler can be used for other purposes like updating geometry
    // or handling surface state changes after the view is already managed

    // Update clipping if geometry changed
    qw_xwayland_view_clip(xwayland_view);
}

static void qw_xwayland_view_handle_request_fullscreen(struct wl_listener *listener, void *data) {
    UNUSED(data);
    struct qw_xwayland_view *xwayland_view =
        wl_container_of(listener, xwayland_view, request_fullscreen);
    struct wlr_xwayland_surface *xwayland_surface = xwayland_view->xwayland_surface;

    if (xwayland_surface->surface == NULL || !xwayland_surface->surface->mapped) {
        return;
    }

    int handled = xwayland_view->base.request_fullscreen_cb(xwayland_surface->fullscreen,
                                                            xwayland_view->base.cb_data);

    if (!handled) {
        wlr_log(WLR_ERROR, "Couldn't toggle fullscreen for X window");
    }
}

static void qw_xwayland_view_handle_request_minimize(struct wl_listener *listener, void *data) {
    struct qw_xwayland_view *xwayland_view =
        wl_container_of(listener, xwayland_view, request_minimize);
    struct wlr_xwayland_surface *surface = xwayland_view->xwayland_surface;
    struct wlr_xwayland_minimize_event *event = data;

    wlr_xwayland_surface_set_minimized(surface, event->minimize);

    int handled =
        xwayland_view->base.request_minimize_cb(surface->minimized, xwayland_view->base.cb_data);
    if (!handled) {
        wlr_log(WLR_ERROR, "Could not minimize X window");
    }
}

static void qw_xwayland_view_handle_request_maximize(struct wl_listener *listener, void *data) {
    UNUSED(data);
    struct qw_xwayland_view *xwayland_view =
        wl_container_of(listener, xwayland_view, request_maximize);
    struct wlr_xwayland_surface *surface = xwayland_view->xwayland_surface;

    wlr_xwayland_surface_set_maximized(surface, true, true);

    bool maximized = surface->maximized_horz || surface->maximized_vert;
    int handled = xwayland_view->base.request_maximize_cb(maximized, xwayland_view->base.cb_data);
    if (!handled) {
        wlr_log(WLR_ERROR, "Could not maximize X window");
    }
}

static void qw_xwayland_view_handle_request_close(struct wl_listener *listener, void *data) {
    UNUSED(data);
    struct qw_xwayland_view *xwayland_view =
        wl_container_of(listener, xwayland_view, request_close);
    struct wlr_xwayland_surface *surface = xwayland_view->xwayland_surface;

    wlr_xwayland_surface_close(surface);

    int handled = xwayland_view->base.request_close_cb(xwayland_view->base.cb_data);
    if (!handled) {
        wlr_log(WLR_ERROR, "Could not close X window");
    }
}

static void qw_xwayland_view_handle_set_title(struct wl_listener *listener, void *data) {
    UNUSED(data);
    struct qw_xwayland_view *xwayland_view = wl_container_of(listener, xwayland_view, set_title);
    struct wlr_xwayland_surface *qw_xsurface = xwayland_view->xwayland_surface;
    xwayland_view->base.title = qw_xsurface->title;
    if (xwayland_view->base.ftl_handle != NULL && qw_xsurface->title != NULL) {
        wlr_foreign_toplevel_handle_v1_set_title(xwayland_view->base.ftl_handle,
                                                 xwayland_view->base.title);
    }
    if (xwayland_view->base.set_title_cb && xwayland_view->base.title) {
        xwayland_view->base.set_title_cb(xwayland_view->base.title, xwayland_view->base.cb_data);
    }
}

static void qw_xwayland_view_handle_set_class(struct wl_listener *listener, void *data) {
    UNUSED(data);
    struct qw_xwayland_view *xwayland_view = wl_container_of(listener, xwayland_view, set_class);
    struct wlr_xwayland_surface *qw_xsurface = xwayland_view->xwayland_surface;
    xwayland_view->base.app_id = qw_xsurface->class;
    if (xwayland_view->base.ftl_handle != NULL && qw_xsurface->title != NULL) {
        wlr_foreign_toplevel_handle_v1_set_app_id(xwayland_view->base.ftl_handle,
                                                  xwayland_view->base.app_id);
    }
    if (xwayland_view->base.set_app_id_cb && xwayland_view->base.app_id) {
        xwayland_view->base.set_app_id_cb(xwayland_view->base.app_id, xwayland_view->base.cb_data);
    }
}

// Called when the XWayland surface is mapped (i.e., ready to be shown).
static void qw_xwayland_view_handle_map(struct wl_listener *listener, void *data) {
    UNUSED(data);
    struct qw_xwayland_view *xwayland_view = wl_container_of(listener, xwayland_view, map);
    struct wlr_xwayland_surface *xwayland_surface = xwayland_view->xwayland_surface;

    // Create a subsurface tree for this view under the content tree.
    xwayland_view->scene_tree = wlr_scene_subsurface_tree_create(xwayland_view->base.content_tree,
                                                                 xwayland_surface->surface);

    // Reparent layer if view has keep_above or keep_below set
    if (xwayland_surface->above) {
        qw_view_reparent((struct qw_view *)xwayland_view, LAYER_KEEPABOVE);
    } else if (xwayland_surface->below) {
        qw_view_reparent((struct qw_view *)xwayland_view, LAYER_KEEPBELOW);
    }

    // Set the view's initial dimensions based on the surface.
    xwayland_view->base.width = xwayland_surface->width;
    xwayland_view->base.height = xwayland_surface->height;

    xwayland_view->base.title = xwayland_surface->title;
    xwayland_view->base.app_id = xwayland_surface->class;
    xwayland_view->base.instance = xwayland_surface->instance;
    xwayland_view->base.role = xwayland_surface->role;

    xwayland_view->base.skip_taskbar = xwayland_surface->skip_taskbar;

    // Set properties for foreign toplevel manager
    if (xwayland_view->base.ftl_handle != NULL) {
        if (xwayland_view->base.title != NULL) {
            wlr_foreign_toplevel_handle_v1_set_title(xwayland_view->base.ftl_handle,
                                                     xwayland_view->base.title);
        }
        if (xwayland_view->base.app_id != NULL) {
            wlr_foreign_toplevel_handle_v1_set_app_id(xwayland_view->base.ftl_handle,
                                                      xwayland_view->base.app_id);
        }
        if (xwayland_surface->parent != NULL) {
            struct qw_xwayland_view *parent_view = xwayland_surface->parent->data;
            if (parent_view != NULL && parent_view->base.ftl_handle != NULL) {
                wlr_foreign_toplevel_handle_v1_set_parent(xwayland_view->base.ftl_handle,
                                                          parent_view->base.ftl_handle);
            }
        }
    }

    // Notify the server that this view is ready to be managed (added to layout/focus system).
    xwayland_view->base.server->manage_view_cb((struct qw_view *)&xwayland_view->base,
                                               xwayland_view->base.server->cb_data);

    // TODO: move this up?
    //  Attach a listener to the surface's commit signal.
    wl_signal_add(&xwayland_surface->surface->events.commit, &xwayland_view->commit);
    xwayland_view->commit.notify = qw_xwayland_view_handle_commit;

    // Add listeners with Python callbacks after the view has been managed
    wl_signal_add(&xwayland_surface->events.request_fullscreen, &xwayland_view->request_fullscreen);
    xwayland_view->request_fullscreen.notify = qw_xwayland_view_handle_request_fullscreen;

    wl_signal_add(&xwayland_surface->events.request_minimize, &xwayland_view->request_minimize);
    xwayland_view->request_minimize.notify = qw_xwayland_view_handle_request_minimize;

    wl_signal_add(&xwayland_surface->events.request_maximize, &xwayland_view->request_maximize);
    xwayland_view->request_maximize.notify = qw_xwayland_view_handle_request_maximize;

    wl_signal_add(&xwayland_surface->events.request_close, &xwayland_view->request_close);
    xwayland_view->request_close.notify = qw_xwayland_view_handle_request_close;

    wl_signal_add(&xwayland_surface->events.set_title, &xwayland_view->set_title);
    xwayland_view->set_title.notify = qw_xwayland_view_handle_set_title;

    wl_signal_add(&xwayland_surface->events.set_class, &xwayland_view->set_class);
    xwayland_view->set_class.notify = qw_xwayland_view_handle_set_class;
}

// Called when the XWayland surface is unmapped (i.e., hidden or destroyed).
static void qw_xwayland_view_handle_unmap(struct wl_listener *listener, void *data) {
    UNUSED(data);
    struct qw_xwayland_view *xwayland_view = wl_container_of(listener, xwayland_view, unmap);
    qw_view_cleanup_borders((struct qw_view *)xwayland_view);
    xwayland_view->base.server->unmanage_view_cb((struct qw_view *)&xwayland_view->base,
                                                 xwayland_view->base.server->cb_data);
    wl_list_remove(&xwayland_view->commit.link);
    wl_list_remove(&xwayland_view->request_fullscreen.link);
    wl_list_remove(&xwayland_view->request_minimize.link);
    wl_list_remove(&xwayland_view->request_maximize.link);
    wl_list_remove(&xwayland_view->request_close.link);
    wl_list_remove(&xwayland_view->set_title.link);
    wl_list_remove(&xwayland_view->set_class.link);
}

// Called when an override-redirect surface is being converted to a managed view.
static void qw_xwayland_view_handle_associate(struct wl_listener *listener, void *data) {
    UNUSED(data);
    struct qw_xwayland_view *xwayland_view = wl_container_of(listener, xwayland_view, associate);
    struct wlr_xwayland_surface *xwayland_surface = xwayland_view->xwayland_surface;

    // Attach map and unmap listeners to the new surface events.
    wl_signal_add(&xwayland_surface->surface->events.unmap, &xwayland_view->unmap);
    xwayland_view->unmap.notify = qw_xwayland_view_handle_unmap;
    wl_signal_add(&xwayland_surface->surface->events.map, &xwayland_view->map);
    xwayland_view->map.notify = qw_xwayland_view_handle_map;
}

static struct qw_xwayland_view *qw_xwayland_view_from_view(struct qw_view *view) {
    if (view->view_type != QW_VIEW_XWAYLAND) {
        wlr_log(WLR_ERROR, "Expected xwayland view");
        return NULL;
    }

    return (struct qw_xwayland_view *)view;
}

static uint32_t qw_xwayland_view_configure(struct qw_view *view, double lx, double ly, int width,
                                           int height) {
    struct qw_xwayland_view *xwayland_view = qw_xwayland_view_from_view(view);
    if (xwayland_view == NULL) {
        return 0;
    }

    struct wlr_xwayland_surface *qw_xsurface = xwayland_view->xwayland_surface;

    wlr_xwayland_surface_configure(qw_xsurface, lx, ly, width, height);

    // xwayland doesn't give us a serial for the configure
    return 0;
}

static void qw_xwayland_view_handle_request_configure(struct wl_listener *listener, void *data) {
    struct qw_xwayland_view *xwayland_view =
        wl_container_of(listener, xwayland_view, request_configure);
    struct wlr_xwayland_surface_configure_event *event = data;
    struct wlr_xwayland_surface *xwayland_surface = xwayland_view->xwayland_surface;

    if (xwayland_surface->surface == NULL || !xwayland_surface->surface->mapped) {
        wlr_xwayland_surface_configure(xwayland_surface, event->x, event->y, event->width,
                                       event->height);
        return;
    }
    if (xwayland_view->base.state == FLOATING) {
        // Respect minimum and maximum sizes
        xwayland_view->base.width = event->width;
        xwayland_view->base.width = event->height;
        // TODO: request resize
        // TODO: request configuration with pending parameters
    } else {
        // TODO: call wlr_xwayland_surface_configure directly?
        qw_xwayland_view_configure(&xwayland_view->base, xwayland_view->base.x,
                                   xwayland_view->base.y, xwayland_view->base.width,
                                   xwayland_view->base.height);
    }
}

static void qw_xwayland_view_handle_request_above(struct wl_listener *listener, void *data) {
    UNUSED(data);
    struct qw_xwayland_view *xwayland_view =
        wl_container_of(listener, xwayland_view, request_above);

    if (xwayland_view->xwayland_surface->above) {
        qw_view_reparent((struct qw_view *)xwayland_view, LAYER_KEEPABOVE);
    } else {
        qw_view_reparent((struct qw_view *)xwayland_view, LAYER_LAYOUT);
    }
}

static void qw_xwayland_view_handle_request_below(struct wl_listener *listener, void *data) {
    UNUSED(data);
    struct qw_xwayland_view *xwayland_view =
        wl_container_of(listener, xwayland_view, request_below);

    if (xwayland_view->xwayland_surface->below) {
        qw_view_reparent((struct qw_view *)xwayland_view, LAYER_KEEPBELOW);
    } else {
        qw_view_reparent((struct qw_view *)xwayland_view, LAYER_LAYOUT);
    }
}

static void qw_xwayland_view_handle_request_activate(struct wl_listener *listener, void *data) {
    UNUSED(data);
    struct qw_xwayland_view *xwayland_view =
        wl_container_of(listener, xwayland_view, request_activate);

    qw_xwayland_view_activate(xwayland_view, true);
}

static void qw_xwayland_view_handle_set_hints(struct wl_listener *listener, void *data) {
    UNUSED(data);
    struct qw_xwayland_view *xwayland_view = wl_container_of(listener, xwayland_view, set_hints);
    struct wlr_xwayland_surface *xwayland_surface = xwayland_view->xwayland_surface;

    if (xwayland_surface->surface == NULL || !xwayland_surface->surface->mapped) {
        return;
    }
    const bool hints_urgency = xcb_icccm_wm_hints_get_urgency(xwayland_surface->hints);
    if (!hints_urgency) {
        return;
    }
    xwayland_view->base.server->view_activation_cb((struct qw_view *)&xwayland_view->base,
                                                   xwayland_view->base.server->cb_data);
}

static void qw_xwayland_view_handle_request_skip_taskbar(struct wl_listener *listener, void *data) {
    UNUSED(data);
    struct qw_xwayland_view *xwayland_view =
        wl_container_of(listener, xwayland_view, request_activate);
    xwayland_view->base.skip_taskbar = xwayland_view->xwayland_surface->skip_taskbar;
}

static void qw_xwayland_view_handle_dissociate(struct wl_listener *listener, void *data) {
    UNUSED(data);
    struct qw_xwayland_view *xwayland_view = wl_container_of(listener, xwayland_view, dissociate);
    wl_list_remove(&xwayland_view->map.link);
    wl_list_remove(&xwayland_view->unmap.link);
}

static void qw_xwayland_view_handle_destroy(struct wl_listener *listener, void *data) {
    UNUSED(data);
    struct qw_xwayland_view *xwayland_view = wl_container_of(listener, xwayland_view, destroy);

    wl_list_remove(&xwayland_view->destroy.link);
    wl_list_remove(&xwayland_view->associate.link);
    wl_list_remove(&xwayland_view->dissociate.link);
    wl_list_remove(&xwayland_view->request_configure.link);
    wl_list_remove(&xwayland_view->request_activate.link);
    wl_list_remove(&xwayland_view->set_hints.link);
    wl_list_remove(&xwayland_view->override_redirect.link);
    wl_list_remove(&xwayland_view->request_above.link);
    wl_list_remove(&xwayland_view->request_below.link);
    wl_list_remove(&xwayland_view->request_skip_taskbar.link);
    qw_view_ftl_manager_handle_destroy(&xwayland_view->base);
    wlr_scene_node_destroy(&xwayland_view->base.content_tree->node);

    free(xwayland_view);
}

static void qw_xwayland_view_handle_request_override_redirect(struct wl_listener *listener,
                                                              void *data) {
    UNUSED(data);
    struct qw_xwayland_view *xwayland_view =
        wl_container_of(listener, xwayland_view, override_redirect);
    struct wlr_xwayland_surface *xwayland_surface = xwayland_view->xwayland_surface;
    struct qw_server *server = xwayland_view->base.server;

    bool associated = xwayland_surface->surface != NULL;
    bool mapped = associated && xwayland_surface->surface->mapped;
    if (mapped) {
        qw_xwayland_view_handle_unmap(&xwayland_view->unmap, NULL);
    }
    if (associated) {
        qw_xwayland_view_handle_dissociate(&xwayland_view->dissociate, NULL);
    }

    qw_xwayland_view_handle_destroy(&xwayland_view->destroy, xwayland_view);
    xwayland_surface->data = NULL;

    qw_server_xwayland_static_view_new(server, xwayland_surface);
    struct qw_xwayland_view *static_view = xwayland_surface->data;
    if (associated) {
        static_view_handle_associate(&static_view->associate, NULL);
    }
    if (mapped) {
        static_view_handle_map(&static_view->map, xwayland_surface);
    }
}

static bool qw_xwayland_view_has_fixed_size(void *self) {
    struct qw_xwayland_view *xwayland_view = (struct qw_xwayland_view *)self;
    xcb_size_hints_t *size_hints = xwayland_view->xwayland_surface->size_hints;

    // TODO: Maybe consider these flags too:
    // "PMinSize" in size_hints->flags and "PMaxSize" in size_hints->flags
    if (size_hints != NULL) {
        return size_hints->min_width > 0 && size_hints->min_height > 0 &&
               size_hints->min_width == size_hints->max_width &&
               size_hints->min_height == size_hints->max_height;
    }

    return false;
}

static void qw_xwayland_view_update_fullscreen(void *self, bool fullscreen) {
    struct qw_xwayland_view *xwayland_view = (struct qw_xwayland_view *)self;
    wlr_xwayland_surface_set_fullscreen(xwayland_view->xwayland_surface, fullscreen);
    if (xwayland_view->base.ftl_handle != NULL) {
        wlr_foreign_toplevel_handle_v1_set_fullscreen(xwayland_view->base.ftl_handle, fullscreen);
    }
}

static void qw_xwayland_view_update_minimized(void *self, bool minimized) {
    struct qw_xwayland_view *xwayland_view = (struct qw_xwayland_view *)self;
    wlr_xwayland_surface_set_minimized(xwayland_view->xwayland_surface, minimized);
    if (xwayland_view->base.ftl_handle != NULL) {
        wlr_foreign_toplevel_handle_v1_set_minimized(xwayland_view->base.ftl_handle, minimized);
    }
}

static void qw_xwayland_view_update_maximized(void *self, bool maximized) {
    struct qw_xwayland_view *xwayland_view = (struct qw_xwayland_view *)self;
    wlr_xwayland_surface_set_maximized(xwayland_view->xwayland_surface, maximized, maximized);
    if (xwayland_view->base.ftl_handle != NULL) {
        wlr_foreign_toplevel_handle_v1_set_fullscreen(xwayland_view->base.ftl_handle, maximized);
    }
}

void qw_server_xwayland_view_new(struct qw_server *server,
                                 struct wlr_xwayland_surface *xwayland_surface) {
    struct qw_xwayland_view *xwayland_view = calloc(1, sizeof(*xwayland_view));
    if (!xwayland_view) {
        wlr_log(WLR_ERROR, "failed to create qw_xwayland_view struct");
        return;
    }

    struct wlr_box geom = {.x = 0, .y = 0, .width = 0, .height = 0};
    xwayland_view->geom = geom;
    xwayland_view->base.server = server;
    xwayland_view->xwayland_surface = xwayland_surface;

    xwayland_view->base.shell = "Xwayland";
    xwayland_view->base.view_type = QW_VIEW_XWAYLAND;
    // Create a scene tree node for this view inside the main layout tree
    xwayland_view->base.content_tree =
        wlr_scene_tree_create(server->scene_windows_layers[LAYER_LAYOUT]);
    xwayland_view->base.content_tree->node.data = xwayland_view;
    xwayland_view->base.layer = LAYER_LAYOUT;

    // Create foreign toplevel manager and listeners
    // Needs to be after content tree is created as we create an output tracking scene buffer
    qw_view_ftl_manager_handle_create(&xwayland_view->base);

    wl_signal_add(&xwayland_surface->events.destroy, &xwayland_view->destroy);
    xwayland_view->destroy.notify = qw_xwayland_view_handle_destroy;

    wl_signal_add(&xwayland_surface->events.associate, &xwayland_view->associate);
    xwayland_view->associate.notify = qw_xwayland_view_handle_associate;

    wl_signal_add(&xwayland_surface->events.dissociate, &xwayland_view->dissociate);
    xwayland_view->dissociate.notify = qw_xwayland_view_handle_dissociate;

    wl_signal_add(&xwayland_surface->events.request_configure, &xwayland_view->request_configure);
    xwayland_view->request_configure.notify = qw_xwayland_view_handle_request_configure;

    wl_signal_add(&xwayland_surface->events.request_activate, &xwayland_view->request_activate);
    xwayland_view->request_activate.notify = qw_xwayland_view_handle_request_activate;

    wl_signal_add(&xwayland_surface->events.set_hints, &xwayland_view->set_hints);
    xwayland_view->set_hints.notify = qw_xwayland_view_handle_set_hints;

    wl_signal_add(&xwayland_surface->events.set_override_redirect,
                  &xwayland_view->override_redirect);
    xwayland_view->override_redirect.notify = qw_xwayland_view_handle_request_override_redirect;

    wl_signal_add(&xwayland_surface->events.request_above, &xwayland_view->request_above);
    xwayland_view->request_above.notify = qw_xwayland_view_handle_request_above;

    wl_signal_add(&xwayland_surface->events.request_below, &xwayland_view->request_below);
    xwayland_view->request_below.notify = qw_xwayland_view_handle_request_below;

    wl_signal_add(&xwayland_surface->events.request_skip_taskbar,
                  &xwayland_view->request_skip_taskbar);
    xwayland_view->request_skip_taskbar.notify = qw_xwayland_view_handle_request_skip_taskbar;

    // Assign function pointers for base view operations
    xwayland_view->base.get_tree_node = qw_xwayland_view_get_tree_node;
    xwayland_view->base.place = qw_xwayland_view_place;
    xwayland_view->base.focus = qw_xwayland_view_focus;
    xwayland_view->base.kill = qw_xwayland_view_kill;
    xwayland_view->base.hide = qw_xwayland_view_hide;
    xwayland_view->base.unhide = qw_xwayland_view_unhide;
    xwayland_view->base.get_pid = qw_xwayland_view_get_pid;
    xwayland_view->base.get_wm_type = qw_xwayland_view_get_window_type;
    xwayland_view->base.get_parent = qw_xwayland_get_parent;
    xwayland_view->base.has_fixed_size = qw_xwayland_view_has_fixed_size;
    xwayland_view->base.update_minimized = qw_xwayland_view_update_minimized;
    xwayland_view->base.update_maximized = qw_xwayland_view_update_maximized;
    xwayland_view->base.update_fullscreen = qw_xwayland_view_update_fullscreen;

    xwayland_surface->data = xwayland_view;
}
