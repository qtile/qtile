#include "xwayland-view.h"

/* Listener callback for XWayland unmanaged surface configuration requests.
 * When an unmanaged XWayland surface (like a popup or override-redirect window) asks
 * to be resized or moved, this function forwards the request to wlroots. */
void qw_unmanaged_handle_request_configure(struct wl_listener *listener, void *data) {
    struct qw_xwayland_unmanaged *qw_surface =
        wl_container_of(listener, qw_surface, request_configure);

    struct wlr_xwayland_surface *qw_xsurface = qw_surface->wlr_xwayland_surface;
    struct wlr_xwayland_surface_configure_event *event = data;

    // Apply the configure request to the surface using wlroots helper function
    wlr_xwayland_surface_configure(qw_xsurface, event->x, event->y, event->width, event->height);
}
