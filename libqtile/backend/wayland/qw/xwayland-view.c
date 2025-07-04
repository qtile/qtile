#include "xwayland-view.h"
#include "server.h"
#include "view.h"
#include "wayland-server-core.h"
#include "wayland-util.h"
#include "wlr/util/log.h"
#include "xdg-view.h"
#include "xwayland.h"
#include <stdlib.h>
#include <wlr/xwayland.h>

/* Handle configure requests from unmanaged XWayland surfaces (popups, override-redirect windows).
 * Forwards resize/move requests directly to wlroots since these surfaces bypass window management.
 */
void qw_xwayland_view_unmanaged_request_configure(struct wl_listener *listener, void *data) {
    struct qw_xwayland_unmanaged *qw_surface =
        wl_container_of(listener, qw_surface, request_configure);

    struct wlr_xwayland_surface *qw_xsurface = qw_surface->wlr_xwayland_surface;
    struct wlr_xwayland_surface_configure_event *event = data;

    // Apply the configure request to the surface using wlroots helper function
    wlr_xwayland_surface_configure(qw_xsurface, event->x, event->y, event->width, event->height);
}

/* Handle geometry updates for unmanaged XWayland surfaces.
 * Synchronizes the scene node position with the XWayland surface's new coordinates. */
void qw_xwayland_view_unmanaged_set_geometry(struct wl_listener *listener, void *data) {
    struct qw_xwayland_unmanaged *qw_surface = wl_container_of(listener, qw_surface, set_geometry);

    struct wlr_xwayland_surface *qw_xsurface = qw_surface->wlr_xwayland_surface;

    wlr_scene_node_set_position(&qw_surface->scene_surface->buffer->node, qw_xsurface->x,
                                qw_xsurface->y);
}

/* Handle mapping of unmanaged XWayland surfaces.
 * Creates scene surface and adds it to the appropriate layer for rendering. */
static void qw_xwayland_view_unmanaged_map(struct wl_listener *listener, void *data) {
    struct qw_server *server;
    struct qw_xwayland_unmanaged *qw_surface = wl_container_of(listener, qw_surface, map);
    struct wlr_xwayland_surface *qw_xsurface = qw_surface->wlr_xwayland_surface;

    qw_surface->scene_surface =
        wlr_scene_surface_create(POINT_TO_UNMANAGED_LAYER, qw_xsurface->surface);

    /* TODO: finish function after layer/zlayer is added
     * Reference:
     * https://github.com/swaywm/sway/blob/a1ac2a2e93ffb3341253af30603cf16483d766bb/sway/desktop/xwayland.c#L56
     */
}

/* Handle unmapping of unmanaged XWayland surfaces.
 * Should clean up scene nodes and restore keyboard focus to appropriate surface. */
static void qw_xwayland_view_unmanaged_unmap(struct wl_listener *listener, void *data) {
    /* TODO: Handle cleanup and focus restoration when an unmanaged XWayland window is unmapped,
     * ensuring it's removed from the scene graph and keyboard focus is correctly returned
     * to a valid surface (after layer/zlayer is added).
     *
     * Reference:
     * https://github.com/swaywm/sway/blob/94c819cc1f9328223509883e4b62939bdf85b760/sway/desktop/xwayland.c#L82
     */
}

/* Handle activation requests from unmanaged XWayland surfaces.
 * Called when X11 applications request keyboard focus via XSetInputFocus or similar. */
void qw_xwayland_view_unmanaged_request_activate(struct wl_listener *listener, void *data) {
    struct qw_xwayland_unmanaged *qw_surface =
        wl_container_of(listener, qw_surface, request_activate);
    struct wlr_xwayland_surface *qw_xsurface = qw_surface->wlr_xwayland_surface;

    if (qw_xsurface->surface == NULL || !qw_xsurface->surface->mapped) {
        return;
    }

    // TODO: finalize focusing surface, after seat implementation
}

/* Handle association of XWayland surface with wlr_surface.
 * Sets up map/unmap listeners when X11 window becomes ready for Wayland rendering. */
void qw_xwayland_view_unmanaged_associate(struct wl_listener *listener, void *data) {
    struct qw_xwayland_unmanaged *qw_surface = wl_container_of(listener, qw_surface, associate);
    struct wlr_xwayland_surface *qw_xsurface = qw_surface->wlr_xwayland_surface;

    wl_signal_add(&qw_xsurface->surface->events.map, &qw_surface->map);
    qw_surface->map.notify = qw_xwayland_view_unmanaged_map;
    wl_signal_add(&qw_xsurface->surface->events.unmap, &qw_surface->unmap);
    qw_surface->unmap.notify = qw_xwayland_view_unmanaged_unmap;
}

/* Handle dissociation of XWayland surface from wlr_surface.
 * Removes map/unmap listeners during surface destruction to prevent use-after-free. */
void qw_xwayland_view_unmanaged_dissociate(struct wl_listener *listener, void *data) {
    struct qw_xwayland_unmanaged *qw_surface = wl_container_of(listener, qw_surface, dissociate);

    wl_list_remove(&qw_surface->map.link);
    wl_list_remove(&qw_surface->unmap.link);
}

/* Handle destruction of unmanaged XWayland surfaces.
 * Removes all event listeners and cleans up associated resources. */
void qw_xwayland_view_unmanaged_destroy(struct wl_listener *listener, void *data) {
    struct qw_xwayland_unmanaged *qw_surface = wl_container_of(listener, qw_surface, destroy);

    // Remove listeners that are always present
    wl_list_remove(&qw_surface->request_configure.link);
    wl_list_remove(&qw_surface->associate.link);
    wl_list_remove(&qw_surface->dissociate.link);
    wl_list_remove(&qw_surface->destroy.link);
    wl_list_remove(&qw_surface->override_redirect.link);
    wl_list_remove(&qw_surface->request_activate.link);
    wl_list_remove(&qw_surface->set_geometry.link);

    // Remove listeners that might be added during associate
    if (!wl_list_empty(&qw_surface->map.link)) {
        wl_list_remove(&qw_surface->map.link);
    }
    if (!wl_list_empty(&qw_surface->unmap.link)) {
        wl_list_remove(&qw_surface->unmap.link);
    }

    // Clean up scene surface if it exists
    if (qw_surface->scene_surface) {
        wlr_scene_node_destroy(&qw_surface->scene_surface->buffer->node);
    }

    // Free the surface structure
    free(qw_surface);
}

// Called when the XWayland surface commits a new state.
static void qw_xwayland_view_handle_commit(struct wl_listener *listener, void *data) {
    struct qw_xwayland_view *xwayland_view = wl_container_of(listener, xwayland_view, commit);
    struct qw_view *view = &xwayland_view->base;
    struct wlr_xwayland_surface *qw_xsurface = xwayland_view->wlr_xwayland_surface;
    struct wlr_surface_state *state = &qw_xsurface->surface->current;

    // Create a geometry box representing the new surface dimensions
    // clang-format off
    struct wlr_box geo_box = {
        .x = 0, .y = 0,
        .width = state->width,
        .height = state->height
    };
    // clang-format on

    // Check if surface size has changed
    bool new_size = view->width != geo_box.width || view->height != geo_box.height;

    if (new_size) {
        // If the client has resized, update our geometry box.
        view->width = geo_box.width;
        view->height = geo_box.height;

        // TODO: resize the scene node or reposition it in the layout
        // placeholder: maybe re-center the surface or notify layout engine
    }
}

// Called when the scene tree associated with the XWayland view is destroyed.
static void qw_xwayland_view_handle_scene_tree_destroy(struct wl_listener *listener, void *data) {
    struct qw_xwayland_view *xwayland_view =
        wl_container_of(listener, xwayland_view, scene_tree_destroy);

    // Nullify the scene tree reference and remove its destroy listener.
    xwayland_view->scene_tree = NULL;
    wl_list_remove(&xwayland_view->scene_tree_destroy.link);
}

// Called when the XWayland surface is mapped (i.e., ready to be shown).
static void qw_xwayland_view_map(struct wl_listener *listener, void *data) {
    struct qw_xwayland_view *xwayland_view = wl_container_of(listener, xwayland_view, map);
    struct qw_view *view = &xwayland_view->base;
    struct wlr_xwayland_surface *qw_xsurface = xwayland_view->wlr_xwayland_surface;
    struct qw_server *server = xwayland_view->server; // Assuming server is stored in view

    // Set the view's initial dimensions based on the surface.
    view->width = qw_xsurface->width;
    view->height = qw_xsurface->height;

    // Attach a listener to the surface's commit signal.
    wl_signal_add(&qw_xsurface->surface->events.commit, &xwayland_view->commit);
    xwayland_view->commit.notify = qw_xwayland_view_handle_commit;

    // Create a subsurface tree for this view under the content tree.
    xwayland_view->scene_tree =
        wlr_scene_subsurface_tree_create(view->content_tree, qw_xsurface->surface);

    // Add destroy listener for scene tree to clean up on teardown.
    if (xwayland_view->scene_tree) {
        xwayland_view->scene_tree_destroy.notify = qw_xwayland_view_handle_scene_tree_destroy;
        wl_signal_add(&xwayland_view->scene_tree->node.events.destroy,
                      &xwayland_view->scene_tree_destroy);
    }

    // Notify the server that this view is ready to be managed (added to layout/focus system).
    server->manage_view_cb(view, server->cb_data);
}

// Called when the XWayland surface is unmapped (i.e., hidden or destroyed).
static void qw_xwayland_view_unmap(struct wl_listener *listener, void *data) {
    struct qw_xwayland_view *xwayland_view = wl_container_of(listener, xwayland_view, unmap);
    struct qw_view *view = &xwayland_view->base;
    struct wlr_xwayland_surface *qw_xsurface = xwayland_view->wlr_xwayland_surface;
    struct qw_server *server = xwayland_view->server;

    // Remove listeners to avoid dangling pointers.
    wl_list_remove(&xwayland_view->commit.link);
    wl_list_remove(&xwayland_view->scene_tree_destroy.link);

    // Destroy scene tree if it exists.
    if (xwayland_view->scene_tree) {
        wlr_scene_node_destroy(&xwayland_view->scene_tree->node);
        xwayland_view->scene_tree = NULL;
    }

    qw_view_cleanup_borders(view);

    // If this surface had keyboard focus, clear it.
    if (qw_xsurface->surface == server->seat->keyboard_state.focused_surface) {
        wlr_seat_keyboard_clear_focus(server->seat);
    }

    // Notify server that this view should no longer be managed.
    server->unmanage_view_cb(view, server->cb_data);
}

// Called when an override-redirect surface is being converted to a managed view.
static void qw_xwayland_view_associate(struct wl_listener *listener, void *data) {
    struct qw_xwayland_view *xwayland_view = wl_container_of(listener, xwayland_view, associate);
    struct wlr_xwayland_surface *qw_xsurface = xwayland_view->wlr_xwayland_surface;

    // Attach map and unmap listeners to the new surface events.
    wl_signal_add(&qw_xsurface->surface->events.unmap, &xwayland_view->unmap);
    xwayland_view->unmap.notify = qw_xwayland_view_unmap;
    wl_signal_add(&qw_xsurface->surface->events.map, &xwayland_view->map);
    xwayland_view->map.notify = qw_xwayland_view_map;
}

// External function to allocate and return a new managed XWayland view.
struct qw_xwayland_view *create_xwayland_view(struct wlr_xwayland_surface *qw_xsurface);

// Handles override-redirect hint being cleared, converting unmanaged to managed window.
void qw_xwayland_view_unmanaged_override_redirect(struct wl_listener *listener, void *data) {
    struct qw_xwayland_unmanaged *qw_surface =
        wl_container_of(listener, qw_surface, override_redirect);
    struct wlr_xwayland_surface *qw_xsurface = qw_surface->wlr_xwayland_surface;

    bool associated = qw_xsurface->surface != NULL;
    bool mapped = associated && qw_xsurface->surface->mapped;

    // If the surface was previously unmanaged and mapped, unmap and dissociate it first.
    if (mapped) {
        qw_xwayland_view_unmanaged_unmap(&qw_surface->unmap, NULL);
    }
    if (associated) {
        qw_xwayland_view_unmanaged_dissociate(&qw_surface->dissociate, NULL);
    }

    // Destroy unmanaged view object and clear the data pointer.
    qw_xwayland_view_unmanaged_destroy(&qw_surface->destroy, NULL);
    qw_xsurface->data = NULL;

    // Create a new managed view.
    struct qw_xwayland_view *qw_xwayland_view = create_xwayland_view(qw_xsurface);

    // Reattach lifecycle hooks and remap if necessary.
    if (associated) {
        qw_xwayland_view_associate(&qw_xwayland_view->associate, NULL);
    }
    if (mapped) {
        qw_xwayland_view_map(&qw_xwayland_view->map, qw_xsurface);
    }
}
