#include "util.h"
#include <string.h>
#include <wlr/types/wlr_keyboard.h>

int qw_util_get_button_code(uint32_t button) {
    // Array of Linux input event button codes (from linux/input-event-codes.h)
    // These codes represent mouse buttons and scroll events
    uint32_t mappings[] = {
        // BTN_LEFT (left mouse button)
        0x110,
        // BTN_MIDDLE (middle mouse button)
        0x112,
        // BTN_RIGHT (right mouse button)
        0x111,
        BUTTON_SCROLL_UP,
        BUTTON_SCROLL_DOWN,
        BUTTON_SCROLL_LEFT,
        BUTTON_SCROLL_RIGHT,
        // BTN_SIDE (side mouse button)
        0x113,
        // BTN_EXTRA (extra mouse button)
        0x114,
    };

    // Calculate the number of elements in the mappings array
    int n = sizeof(mappings) / sizeof(mappings[0]);

    for (int i = 0; i < n; ++i) {
        if (button == mappings[i]) {
            // Return the 1-based index of the button mapping
            return i + 1;
        }
    }

    return 0;
}

int qw_util_get_modifier_code(const char *codestr) {
    struct code_mapping {
        const char *name;
        enum wlr_keyboard_modifier mod;
    };

    // Mapping from modifier key names to Wayland keyboard modifier enums
    // clang-format off
    struct code_mapping mappings[] = {
        {"shift", WLR_MODIFIER_SHIFT},
        {"lock", WLR_MODIFIER_CAPS},
        {"control", WLR_MODIFIER_CTRL},
        {"mod1", WLR_MODIFIER_ALT},
        {"mod2", WLR_MODIFIER_MOD2},
        {"mod3", WLR_MODIFIER_MOD3},
        {"mod4", WLR_MODIFIER_LOGO},
        {"mod5", WLR_MODIFIER_MOD5}
    };
    //clang-format on

    size_t n = sizeof(mappings) / sizeof(mappings[0]);

    // Search for the modifier name matching the input string
    for (size_t i = 0; i < n; ++i) {
        if (strcmp(codestr, mappings[i].name) == 0) {
            return mappings[i].mod;
        }
    }

    return -1;
}

xkb_keysym_t qwu_keysym_from_name(const char *name) {
	return xkb_keysym_from_name(name, XKB_KEYSYM_CASE_INSENSITIVE);
}

void qw_util_deactivate_surface(struct wlr_surface *surface) {
    struct wlr_xdg_toplevel *xdg_toplevel = wlr_xdg_toplevel_try_from_wlr_surface(surface);
    if (xdg_toplevel) {
        wlr_xdg_toplevel_set_activated(xdg_toplevel, false);

        // Handle foreign toplevel messaging
        struct qw_xdg_view *xdg_view = xdg_toplevel->base->data;
        if (xdg_view->base.ftl_handle != NULL) {
            wlr_foreign_toplevel_handle_v1_set_activated(xdg_view->base.ftl_handle, false);
        }
        return;
    }

    #if WLR_HAS_XWAYLAND
    struct wlr_xwayland_surface *xwayland_surface = wlr_xwayland_surface_try_from_wlr_surface(surface);
    if (xwayland_surface) {
        wlr_xwayland_surface_activate(xwayland_surface, false);

        // Handle foreign toplevel messaging
        struct qw_xwayland_view *xwayland_view = xwayland_surface->data;
        if (xwayland_view->base.ftl_handle != NULL) {
            wlr_foreign_toplevel_handle_v1_set_activated(xwayland_view->base.ftl_handle, false);
        }
        return;
    }
    #endif
}
