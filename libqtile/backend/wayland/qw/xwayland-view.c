#include "xwayland-view.h"
#include "qw/util.h"
#include "server.h"
#include "view.h"
#include "wayland-server-core.h"
#include "wayland-util.h"
#include "wlr/types/wlr_xdg_decoration_v1.h"
#include "wlr/util/log.h"
#include "xdg-view.h"
#include <stdint.h>
#include <stdlib.h>
#include <wlr/xwayland.h>

static void qw_xwayland_view_do_focus(struct qw_xwayland_view *xwayland_view,
                                      struct wlr_surface *surface) {
    if (!xwayland_view) {
        return;
    }

    struct qw_server *server = xwayland_view->base.server;
    struct wlr_seat *seat = server->seat;
    struct wlr_surface *prev_surface = seat->keyboard_state.focused_surface;

    if (prev_surface == surface) {
        return;
    }

    wlr_scene_node_raise_to_top(&xwayland_view->base.content_tree->node);
    wlr_foreign_toplevel_handle_v1_set_activated(xwayland_view->base.ftl_handle, true);

    // Deactivate previous surface if any
    if (prev_surface != NULL) {
        qw_util_deactivate_surface(prev_surface);
    }

    wlr_xwayland_surface_activate(xwayland_view->xwayland_surface, true);

    // Notify keyboard about entering this surface (for keyboard input)
    struct wlr_keyboard *keyboard = wlr_seat_get_keyboard(seat);
    if (keyboard) {
        wlr_seat_keyboard_notify_enter(seat, xwayland_view->xwayland_surface->surface,
                                       keyboard->keycodes, keyboard->num_keycodes,
                                       &keyboard->modifiers);
    }
}

/* Handle configure requests from unmanaged XWayland surfaces (popups, override-redirect windows).
 * Forwards resize/move requests directly to wlroots since these surfaces bypass window management.
 */
// void qw_xwayland_view_unmanaged_request_configure(struct wl_listener *listener, void *data) {
//     struct qw_xwayland_unmanaged *qw_surface =
//         wl_container_of(listener, qw_surface, request_configure);
//
//     struct wlr_xwayland_surface *qw_xsurface = qw_surface->wlr_xwayland_surface;
//     struct wlr_xwayland_surface_configure_event *event = data;
//
//     // Apply the configure request to the surface using wlroots helper function
//     wlr_xwayland_surface_configure(qw_xsurface, event->x, event->y, event->width, event->height);
// }

/* Handle geometry updates for unmanaged XWayland surfaces.
 * Synchronizes the scene node position with the XWayland surface's new coordinates. */
// void qw_xwayland_view_unmanaged_set_geometry(struct wl_listener *listener, void *data) {
//     struct qw_xwayland_unmanaged *qw_surface = wl_container_of(listener, qw_surface,
//     set_geometry);
//
//     struct wlr_xwayland_surface *qw_xsurface = qw_surface->wlr_xwayland_surface;
//
//     wlr_scene_node_set_position(&qw_surface->scene_surface->buffer->node, qw_xsurface->x,
//                                 qw_xsurface->y);
// }

/* Handle mapping of unmanaged XWayland surfaces.
 * Creates scene surface and adds it to the appropriate layer for rendering. */
// static void qw_xwayland_view_unmanaged_map(struct wl_listener *listener, void *data) {
//     struct qw_server *server;
//     struct qw_xwayland_unmanaged *qw_surface = wl_container_of(listener, qw_surface, map);
//     struct wlr_xwayland_surface *qw_xsurface = qw_surface->wlr_xwayland_surface;
//
//     qw_surface->scene_surface =
//         wlr_scene_surface_create(POINT_TO_UNMANAGED_LAYER, qw_xsurface->surface);
//
//     /* TODO: finish function after layer/zlayer is added
//      * Reference:
//      * https://github.com/swaywm/sway/blob/a1ac2a2e93ffb3341253af30603cf16483d766bb/sway/desktop/xwayland.c#L56
//      */
// }

/* Handle unmapping of unmanaged XWayland surfaces.
 * Should clean up scene nodes and restore keyboard focus to appropriate surface. */
// static void qw_xwayland_view_unmanaged_unmap(struct wl_listener *listener, void *data) {
// /* TODO: Handle cleanup and focus restoration when an unmanaged XWayland window is unmapped,
//  * ensuring it's removed from the scene graph and keyboard focus is correctly returned
//  * to a valid surface (after layer/zlayer is added).
//  *
//  * Reference:
//  * https://github.com/swaywm/sway/blob/94c819cc1f9328223509883e4b62939bdf85b760/sway/desktop/xwayland.c#L82
//  */
// }

/* Handle activation requests from unmanaged XWayland surfaces.
 * Called when X11 applications request keyboard focus via XSetInputFocus or similar. */
// void qw_xwayland_view_unmanaged_request_activate(struct wl_listener *listener, void *data) {
//     struct qw_xwayland_unmanaged *qw_surface =
//         wl_container_of(listener, qw_surface, request_activate);
//     struct wlr_xwayland_surface *qw_xsurface = qw_surface->wlr_xwayland_surface;
//     struct qw_xwayland_view *xwayland_view =
//         wl_container_of(listener, xwayland_view, request_activate);
//
//     if (qw_xsurface->surface == NULL || !qw_xsurface->surface->mapped) {
//         wlr_log(WLR_INFO, "Activation request for uknown surface");
//         return;
//     }
//
//     struct wlr_surface *focused = xwayland_view->server->seat->keyboard_state.focused_surface;
//
//     if (focused == NULL) {
//         wlr_log(WLR_INFO, "No surface found");
//     }
//
//     // TODO: finalize focusing surface
// }

/* Handle association of XWayland surface with wlr_surface.
 * Sets up map/unmap listeners when X11 window becomes ready for Wayland rendering. */
// void qw_xwayland_view_unmanaged_associate(struct wl_listener *listener, void *data) {
//     struct qw_xwayland_unmanaged *qw_surface = wl_container_of(listener, qw_surface, associate);
//     struct wlr_xwayland_surface *qw_xsurface = qw_surface->wlr_xwayland_surface;
//
//     wl_signal_add(&qw_xsurface->surface->events.map, &qw_surface->map);
//     // qw_surface->map.notify = qw_xwayland_view_unmanaged_map;
//     wl_signal_add(&qw_xsurface->surface->events.unmap, &qw_surface->unmap);
//     qw_surface->unmap.notify = qw_xwayland_view_unmanaged_unmap;
// }

/* Handle dissociation of XWayland surface from wlr_surface.
 * Removes map/unmap listeners during surface destruction to prevent use-after-free. */
// void qw_xwayland_view_unmanaged_dissociate(struct wl_listener *listener, void *data) {
//     struct qw_xwayland_unmanaged *qw_surface = wl_container_of(listener, qw_surface, dissociate);
//
//     wl_list_remove(&qw_surface->map.link);
//     wl_list_remove(&qw_surface->unmap.link);
// }

/* Handle destruction of unmanaged XWayland surfaces.
 * Removes all event listeners and cleans up associated resources. */
// void qw_xwayland_view_unmanaged_destroy(struct wl_listener *listener, void *data) {
//     struct qw_xwayland_unmanaged *qw_surface = wl_container_of(listener, qw_surface, destroy);
//
//     // Remove listeners that are always present
//     wl_list_remove(&qw_surface->request_configure.link);
//     wl_list_remove(&qw_surface->associate.link);
//     wl_list_remove(&qw_surface->dissociate.link);
//     wl_list_remove(&qw_surface->destroy.link);
//     wl_list_remove(&qw_surface->override_redirect.link);
//     wl_list_remove(&qw_surface->request_activate.link);
//     wl_list_remove(&qw_surface->set_geometry.link);
//
//     // Remove listeners that might be added during associate
//     if (!wl_list_empty(&qw_surface->map.link)) {
//         wl_list_remove(&qw_surface->map.link);
//     }
//     if (!wl_list_empty(&qw_surface->unmap.link)) {
//         wl_list_remove(&qw_surface->unmap.link);
//     }
//
//     // Clean up scene surface if it exists
//     if (qw_surface->scene_surface) {
//         wlr_scene_node_destroy(&qw_surface->scene_surface->buffer->node);
//     }
//
//     // Free the surface structure
//     free(qw_surface);
// }

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
                                   const struct qw_border *borders, int bn, int above) {
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
    qw_view_paint_borders((struct qw_view *)xwayland_view, borders, bn);

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

    // Clear keyboard focus if this view was focused
    // TODO:
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

// Handle commit event: called when XWayland surface commits state changes
static void qw_xwayland_view_handle_commit(struct wl_listener *listener, void *data) {
    struct qw_xwayland_view *xwayland_view = wl_container_of(listener, xwayland_view, commit);
    // For XWayland, we don't need to check for initial_commit or manage the view here
    // The view is already managed when it's mapped (see qw_xwayland_view_map)
    // This commit handler can be used for other purposes like updating geometry
    // or handling surface state changes after the view is already managed

    // Update clipping if geometry changed
    // qw_xwayland_view_clip(xwayland_view);
}

// Called when the XWayland surface is mapped (i.e., ready to be shown).
static void qw_xwayland_view_handle_map(struct wl_listener *listener, void *data) {
    struct qw_xwayland_view *xwayland_view = wl_container_of(listener, xwayland_view, map);
    struct wlr_xwayland_surface *xwayland_surface = xwayland_view->xwayland_surface;

    // Create a subsurface tree for this view under the content tree.
    xwayland_view->scene_tree = wlr_scene_subsurface_tree_create(xwayland_view->base.content_tree,
                                                                 xwayland_surface->surface);

    // Set the view's initial dimensions based on the surface.
    xwayland_view->base.width = xwayland_surface->width;
    xwayland_view->base.height = xwayland_surface->height;

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
            if (parent_view->base.ftl_handle != NULL) {
                wlr_foreign_toplevel_handle_v1_set_parent(xwayland_view->base.ftl_handle,
                                                          parent_view->base.ftl_handle);
            }
        }
    } else {
        wlr_log(WLR_ERROR, "Could not create foreign toplevel handle.");
    }

    // Notify the server that this view is ready to be managed (added to layout/focus system).
    xwayland_view->base.server->manage_view_cb((struct qw_view *)&xwayland_view->base,
                                               xwayland_view->base.server->cb_data);

    // TODO: move this up?
    //  Attach a listener to the surface's commit signal.
    wl_signal_add(&xwayland_surface->surface->events.commit, &xwayland_view->commit);
    xwayland_view->commit.notify = qw_xwayland_view_handle_commit;
}

// Called when the XWayland surface is unmapped (i.e., hidden or destroyed).
static void qw_xwayland_view_handle_unmap(struct wl_listener *listener, void *data) {
    struct qw_xwayland_view *xwayland_view = wl_container_of(listener, xwayland_view, unmap);
    qw_view_cleanup_borders((struct qw_view *)xwayland_view);
    xwayland_view->base.server->unmanage_view_cb((struct qw_view *)&xwayland_view->base,
                                                 xwayland_view->base.server->cb_data);
}

// Called when an override-redirect surface is being converted to a managed view.
static void qw_xwayland_view_handle_associate(struct wl_listener *listener, void *data) {
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

static void qw_xwayland_view_handle_request_fullscreen(struct wl_listener *listener, void *data) {
    struct qw_xwayland_view *xwayland_view =
        wl_container_of(listener, xwayland_view, request_fullscreen);
    struct wlr_xwayland_surface *qw_xsurface = xwayland_view->xwayland_surface;

    if (qw_xsurface->surface == NULL || !qw_xsurface->surface->mapped) {
        return;
    }

    int handled = xwayland_view->base.request_fullscreen_cb(qw_xsurface->fullscreen,
                                                            xwayland_view->base.cb_data);

    if (!handled) {
        wlr_log(WLR_ERROR, "Couldn't toggle fullscreen for X window");
    }
}

static void qw_xwayland_view_handle_request_minimize(struct wl_listener *listener, void *data) {
    // TODO: implement
    // reference:
    // https://github.com/swaywm/sway/blob/357d341f8fd68cd6902ea029a46baf5ce3411336/sway/desktop/xwayland.c#L622C37-L622C77
}

static void qw_xwayland_view_handle_request_activate(struct wl_listener *listener, void *data) {
    // TODO: implement after Activation PR is merged:
    // https://github.com/qtile/qtile/pull/5329
    // Reference:
    // https://github.com/swaywm/sway/blob/357d341f8fd68cd6902ea029a46baf5ce3411336/sway/desktop/xwayland.c#L669C37-L669C77
}

static void qw_xwayland_view_handle_request_move(struct wl_listener *listener, void *data) {
    // TODO: implement
    // reference:
    // https://github.com/swaywm/sway/blob/357d341f8fd68cd6902ea029a46baf5ce3411336/sway/desktop/xwayland.c#L637
}

static void qw_xwayland_view_handle_request_resize(struct wl_listener *listener, void *data) {
    // TODO: implement
    // reference:
    // https://github.com/swaywm/sway/blob/357d341f8fd68cd6902ea029a46baf5ce3411336/sway/desktop/xwayland.c#L653
}

static void qw_xwayland_view_handle_set_title(struct wl_listener *listener, void *data) {
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
    struct qw_xwayland_view *xwayland_view = wl_container_of(listener, xwayland_view, set_class);
    struct wlr_xwayland_surface *qw_xsurface = xwayland_view->xwayland_surface;
    xwayland_view->base.app_id = qw_xsurface->class;
    if (xwayland_view->base.ftl_handle != NULL && qw_xsurface->title != NULL) {
        wlr_foreign_toplevel_handle_v1_set_app_id(xwayland_view->base.ftl_handle,
                                                  xwayland_view->base.app_id);
    }
    if (xwayland_view->base.set_title_cb && xwayland_view->base.app_id) {
        xwayland_view->base.set_app_id_cb(xwayland_view->base.app_id, xwayland_view->base.cb_data);
    }
}

static void qw_xwayland_view_handle_set_role(struct wl_listener *listener, void *data) {
    // TODO: implement
    // reference:
    // https://github.com/swaywm/sway/blob/357d341f8fd68cd6902ea029a46baf5ce3411336/sway/desktop/xwayland.c#L705
}

static void qw_xwayland_view_handle_set_startup_id(struct wl_listener *listener, void *data) {
    // TODO: implement
    // reference:
    // https://github.com/swaywm/sway/blob/357d341f8fd68cd6902ea029a46baf5ce3411336/sway/desktop/xwayland.c#L716
}

static void qw_xwayland_view_handle_set_window_type(struct wl_listener *listener, void *data) {
    // TODO: implement
    // reference:
    // https://github.com/swaywm/sway/blob/357d341f8fd68cd6902ea029a46baf5ce3411336/sway/desktop/xwayland.c#L741
}

static void qw_xwayland_view_handle_set_hints(struct wl_listener *listener, void *data) {
    // TODO: implement
    // reference:
    // https://github.com/swaywm/sway/blob/357d341f8fd68cd6902ea029a46baf5ce3411336/sway/desktop/xwayland.c#L752
}

static void qw_xwayland_view_handle_set_decorations(struct wl_listener *listener, void *data) {
    // TODO: implement
    // reference:
    // https://github.com/swaywm/sway/blob/357d341f8fd68cd6902ea029a46baf5ce3411336/sway/desktop/xwayland.c#L342
}

static void qw_xwayland_view_handle_dissociate(struct wl_listener *listener, void *data) {
    // TODO: implement
    // reference:
    // https://github.com/swaywm/sway/blob/357d341f8fd68cd6902ea029a46baf5ce3411336/sway/desktop/xwayland.c#L783
}

static void qw_xwayland_view_handle_override_redirect(struct wl_listener *listener, void *data) {
    // TODO: implement
    // reference:
    // https://github.com/swaywm/sway/blob/357d341f8fd68cd6902ea029a46baf5ce3411336/sway/desktop/xwayland.c#L551
}

static void qw_xwayland_view_handle_destroy(struct wl_listener *listener, void *data) {
    struct qw_xwayland_view *xwayland_view = wl_container_of(listener, xwayland_view, destroy);

    // wl_list_remove(&xwayland_view->commit.link);
    // xwayland_view->xwayland_surface = NULL;

    wl_list_remove(&xwayland_view->map.link);
    wl_list_remove(&xwayland_view->unmap.link);
    wl_list_remove(&xwayland_view->commit.link);
    wl_list_remove(&xwayland_view->destroy.link);
    wl_list_remove(&xwayland_view->request_configure.link);
    // wl_list_remove(&xwayland_view->request_fullscreen.link);
    // wl_list_remove(&xwayland_view->request_move.link);
    // wl_list_remove(&xwayland_view->request_resize.link);
    // wl_list_remove(&xwayland_view->request_activate.link);
    wl_list_remove(&xwayland_view->set_title.link);
    wl_list_remove(&xwayland_view->set_class.link);
    // wl_list_remove(&xwayland_view->set_role.link);
    // wl_list_remove(&xwayland_view->set_startup_id.link);
    // wl_list_remove(&xwayland_view->set_window_type.link);
    // wl_list_remove(&xwayland_view->set_hints.link);
    // wl_list_remove(&xwayland_view->set_decorations.link);
    wl_list_remove(&xwayland_view->associate.link);
    // wl_list_remove(&xwayland_view->dissociate.link);
    // wl_list_remove(&xwayland_view->override_redirect.link);

    // Destroy the foreign toplevel manager and listeners
    qw_view_ftl_manager_handle_destroy(&xwayland_view->base);

    free(xwayland_view);
}

static void qw_xwayland_view_focus(void *self, int above) {
    struct qw_xwayland_view *xwayland_view = (struct qw_xwayland_view *)self;
    if (!xwayland_view->xwayland_surface->surface->mapped) {
        return; // Can't focus if not mapped
    }
    qw_xwayland_view_do_focus(xwayland_view, xwayland_view->xwayland_surface->surface);
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

    wl_signal_add(&xwayland_surface->events.associate, &xwayland_view->associate);
    xwayland_view->associate.notify = qw_xwayland_view_handle_associate;

    wl_signal_add(&xwayland_surface->events.set_title, &xwayland_view->set_title);
    xwayland_view->set_title.notify = qw_xwayland_view_handle_set_title;

    wl_signal_add(&xwayland_surface->events.set_class, &xwayland_view->set_class);
    xwayland_view->set_class.notify = qw_xwayland_view_handle_set_class;

    wl_signal_add(&xwayland_surface->events.request_configure, &xwayland_view->request_configure);
    xwayland_view->request_configure.notify = qw_xwayland_view_handle_request_configure;

    // Assign function pointers for base view operations
    xwayland_view->base.get_tree_node = qw_xwayland_view_get_tree_node;
    xwayland_view->base.place = qw_xwayland_view_place;
    xwayland_view->base.focus = qw_xwayland_view_focus;
    xwayland_view->base.kill = qw_xwayland_view_kill;
    xwayland_view->base.hide = qw_xwayland_view_hide;
    xwayland_view->base.unhide = qw_xwayland_view_unhide;
    xwayland_view->base.get_pid = qw_xwayland_view_get_pid;

    // Add listener for toplevel destroy event
    wl_signal_add(&xwayland_surface->events.destroy, &xwayland_view->destroy);
    xwayland_view->destroy.notify = qw_xwayland_view_handle_destroy;

    xwayland_surface->data = xwayland_view;

    // Create foreign toplevel manager and listeners
    qw_view_ftl_manager_handle_create(&xwayland_view->base);
}

struct qw_xwayland_view *create_xwayland_view(struct wlr_xwayland_surface *qw_xsurface) {
    wlr_log(WLR_DEBUG, "New xwayland surface title='%s' class='%s'", qw_xsurface->title,
            qw_xsurface->class);

    struct qw_xwayland_view *xwayland_view = calloc(1, sizeof(*xwayland_view));

    if (!xwayland_view) {
        wlr_log(WLR_INFO, "Failed to allocate memory to xwayland_view");
    }

    // Check if we can initilaze xwayland view
    // if (!view_init(&xwayland_view->base)) { // TODO: implement view_init
    //     free(xwayland_view);
    //     return NULL;
    // }

    xwayland_view->xwayland_surface = qw_xsurface;

    wl_signal_add(&qw_xsurface->events.destroy, &xwayland_view->destroy);
    xwayland_view->destroy.notify = qw_xwayland_view_handle_destroy;

    wl_signal_add(&qw_xsurface->events.request_configure, &xwayland_view->request_configure);
    xwayland_view->request_configure.notify = qw_xwayland_view_handle_request_configure;

    wl_signal_add(&qw_xsurface->events.request_fullscreen, &xwayland_view->request_fullscreen);
    xwayland_view->request_fullscreen.notify = qw_xwayland_view_handle_request_fullscreen;

    wl_signal_add(&qw_xsurface->events.request_minimize, &xwayland_view->request_minimize);
    xwayland_view->request_minimize.notify = qw_xwayland_view_handle_request_minimize;

    wl_signal_add(&qw_xsurface->events.request_activate, &xwayland_view->request_activate);
    xwayland_view->request_activate.notify = qw_xwayland_view_handle_request_activate;

    wl_signal_add(&qw_xsurface->events.request_move, &xwayland_view->request_move);
    xwayland_view->request_move.notify = qw_xwayland_view_handle_request_move;

    wl_signal_add(&qw_xsurface->events.request_resize, &xwayland_view->request_resize);
    xwayland_view->request_resize.notify = qw_xwayland_view_handle_request_resize;

    wl_signal_add(&qw_xsurface->events.set_title, &xwayland_view->set_title);
    xwayland_view->set_title.notify = qw_xwayland_view_handle_set_title;

    wl_signal_add(&qw_xsurface->events.set_class, &xwayland_view->set_class);
    xwayland_view->set_class.notify = qw_xwayland_view_handle_set_class;

    wl_signal_add(&qw_xsurface->events.set_role, &xwayland_view->set_role);
    xwayland_view->set_role.notify = qw_xwayland_view_handle_set_role;

    wl_signal_add(&qw_xsurface->events.set_startup_id, &xwayland_view->set_startup_id);
    xwayland_view->set_startup_id.notify = qw_xwayland_view_handle_set_startup_id;

    wl_signal_add(&qw_xsurface->events.set_window_type, &xwayland_view->set_window_type);
    xwayland_view->set_window_type.notify = qw_xwayland_view_handle_set_window_type;

    wl_signal_add(&qw_xsurface->events.set_hints, &xwayland_view->set_hints);
    xwayland_view->set_hints.notify = qw_xwayland_view_handle_set_hints;

    wl_signal_add(&qw_xsurface->events.set_decorations, &xwayland_view->set_decorations);
    xwayland_view->set_decorations.notify = qw_xwayland_view_handle_set_decorations;

    wl_signal_add(&qw_xsurface->events.associate, &xwayland_view->associate);
    xwayland_view->associate.notify = qw_xwayland_view_handle_associate;

    wl_signal_add(&qw_xsurface->events.dissociate, &xwayland_view->dissociate);
    xwayland_view->dissociate.notify = qw_xwayland_view_handle_dissociate;

    wl_signal_add(&qw_xsurface->events.set_override_redirect, &xwayland_view->override_redirect);
    xwayland_view->override_redirect.notify = qw_xwayland_view_handle_override_redirect;

    qw_xsurface->data = xwayland_view;

    return xwayland_view;
}

// Handles override-redirect hint being cleared, converting unmanaged to managed window.
// void qw_xwayland_view_unmanaged_override_redirect(struct wl_listener *listener, void *data) {
//     struct qw_xwayland_unmanaged *qw_surface =
//         wl_container_of(listener, qw_surface, override_redirect);
//     struct wlr_xwayland_surface *qw_xsurface = qw_surface->wlr_xwayland_surface;
//
//     bool associated = qw_xsurface->surface != NULL;
//     bool mapped = associated && qw_xsurface->surface->mapped;
//
//     // If the surface was previously unmanaged and mapped, unmap and dissociate it first.
//     if (mapped) {
//         qw_xwayland_view_unmanaged_unmap(&qw_surface->unmap, NULL);
//     }
//     if (associated) {
//         qw_xwayland_view_unmanaged_dissociate(&qw_surface->dissociate, NULL);
//     }
//
//     // Destroy unmanaged view object and clear the data pointer.
//     qw_xwayland_view_unmanaged_destroy(&qw_surface->destroy, NULL);
//     qw_xsurface->data = NULL;
//
//     // Create a new managed view.
//     struct qw_xwayland_view *qw_xwayland_view = create_xwayland_view(qw_xsurface);
//
//     // Reattach lifecycle hooks and remap if necessary.
//     if (associated) {
//         qw_xwayland_view_associate(&qw_xwayland_view->associate, NULL);
//     }
//     if (mapped) {
//         qw_xwayland_view_map(&qw_xwayland_view->map, qw_xsurface);
//     }
// }
