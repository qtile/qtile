#include "xwayland.h"
#include "cursor.h"
#include "log.h"
#include "output.h"
#include "server.h"
#include "wlr/util/log.h"
#include "xwayland-view.h"
#include <stdbool.h>
#include <stdlib.h>
#include <wayland-server-core.h>
#include <wlr/types/wlr_output.h>
#include <wlr/types/wlr_output_layout.h>
#include <wlr/types/wlr_scene.h>
#include <wlr/xwayland.h>
#include <xcb/xcb_icccm.h>

/* Mapping enum values to their corresponding X11 atom string names.
 * These strings are used to fetch the actual atoms from the X server once conne */
static const char *atom_map[ATOM_LAST] = {
    [NET_WM_WINDOW_TYPE_NORMAL] = "_NET_WM_WINDOW_TYPE_NORMAL",
    [NET_WM_WINDOW_TYPE_DIALOG] = "_NET_WM_WINDOW_TYPE_DIALOG",
    [NET_WM_WINDOW_TYPE_UTILITY] = "_NET_WM_WINDOW_TYPE_UTILITY",
    [NET_WM_WINDOW_TYPE_TOOLBAR] = "_NET_WM_WINDOW_TYPE_TOOLBAR",
    [NET_WM_WINDOW_TYPE_SPLASH] = "_NET_WM_WINDOW_TYPE_SPLASH",
    [NET_WM_WINDOW_TYPE_MENU] = "_NET_WM_WINDOW_TYPE_MENU",
    [NET_WM_WINDOW_TYPE_DROPDOWN_MENU] = "_NET_WM_WINDOW_TYPE_DROPDOWN_MENU",
    [NET_WM_WINDOW_TYPE_POPUP_MENU] = "_NET_WM_WINDOW_TYPE_POPUP_MENU",
    [NET_WM_WINDOW_TYPE_TOOLTIP] = "_NET_WM_WINDOW_TYPE_TOOLTIP",
    [NET_WM_WINDOW_TYPE_NOTIFICATION] = "_NET_WM_WINDOW_TYPE_NOTIFICATION",
    [NET_WM_STATE_MODAL] = "_NET_WM_STATE_MODAL",
};

// static struct qw_xwayland_unmanaged *create_unmanaged(struct wlr_xwayland_surface *qw_xsurface) {
//     struct qw_xwayland_unmanaged *qw_surface = calloc(1, sizeof(struct qw_xwayland_unmanaged));
//
//     if (qw_surface == NULL) {
//         wlr_log(WLR_ERROR, "Allocation failed");
//         return NULL;
//     }
//
//     qw_surface->wlr_xwayland_surface = qw_xsurface;
//
//     wl_signal_add(&qw_xsurface->events.request_configure, &qw_surface->request_configure);
//     qw_surface->request_configure.notify = qw_xwayland_view_unmanaged_request_configure;
//     wl_signal_add(&qw_xsurface->events.associate, &qw_surface->associate);
//     qw_surface->associate.notify = qw_xwayland_view_unmanaged_associate;
//     wl_signal_add(&qw_xsurface->events.dissociate, &qw_surface->dissociate);
//     qw_surface->dissociate.notify = qw_xwayland_view_unmanaged_dissociate;
//     wl_signal_add(&qw_xsurface->events.destroy, &qw_surface->destroy);
//     qw_surface->destroy.notify = qw_xwayland_view_unmanaged_destroy;
//     wl_signal_add(&qw_xsurface->events.set_override_redirect, &qw_surface->override_redirect);
//     qw_surface->override_redirect.notify = qw_xwayland_view_unmanaged_override_redirect;
//     wl_signal_add(&qw_xsurface->events.request_activate, &qw_surface->request_activate);
//     qw_surface->request_activate.notify = qw_xwayland_view_unmanaged_request_activate;
//
//     return qw_surface;
// }
