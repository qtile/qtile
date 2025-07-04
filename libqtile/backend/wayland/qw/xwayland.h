#ifndef QW_XWAYLAND_H
#define QW_XWAYLAND_H

#include <wlr/xwayland.h>
#include <xcb/xproto.h>

/* Enum for X11 window type atoms and modal state atom
 * These are used to identify the type of XWayland window (normal, dialog, tooltip, etc.)
 * and window states (like modal) */
enum atom_name {
    NET_WM_WINDOW_TYPE_NORMAL,
    NET_WM_WINDOW_TYPE_DIALOG,
    NET_WM_WINDOW_TYPE_UTILITY,
    NET_WM_WINDOW_TYPE_TOOLBAR,
    NET_WM_WINDOW_TYPE_SPLASH,
    NET_WM_WINDOW_TYPE_MENU,
    NET_WM_WINDOW_TYPE_DROPDOWN_MENU,
    NET_WM_WINDOW_TYPE_POPUP_MENU,
    NET_WM_WINDOW_TYPE_TOOLTIP,
    NET_WM_WINDOW_TYPE_NOTIFICATION,
    NET_WM_STATE_MODAL,
    ATOM_LAST,
};

// Main struct holding XWayland instance and related data
struct qw_xwayland {
    struct wlr_xwayland *qw_xwayland;
    struct wlr_xcursor_manager *xcursor_manager;

    xcb_atom_t atoms[ATOM_LAST]; // Cached X11 atoms for quick lookup
};

// Callback for when the XWayland server is ready to accept connections
void qw_handle_xwayland_ready(struct wl_listener *listener, void *data);

#endif /* QW_XWAYLAND_H */
