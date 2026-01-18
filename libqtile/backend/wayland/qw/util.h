#ifndef UTIL_H
#define UTIL_H

#include <stdint.h>
#include <wlr/types/wlr_compositor.h>
#include <xkbcommon/xkbcommon.h>

#define UNUSED(x) ((void)(x))

// Enum defining button codes for scroll events.
// These values start from 0x300 and correspond to Linux input-event-codes.h.
// They represent scroll wheel directions for mouse input.
enum BUTTON_SCROLL {
    BUTTON_SCROLL_UP = 0x300,
    BUTTON_SCROLL_DOWN = 0x301,
    BUTTON_SCROLL_LEFT = 0x302,
    BUTTON_SCROLL_RIGHT = 0x303,
};

// Function to convert a raw button code into a simplified button ID.
// Returns an int representing the button index (1-based), or 0 if unknown.
int qw_util_get_button_code(uint32_t button);

// Function to convert a modifier key string name into the corresponding
// wlr_keyboard_modifier enum value. Returns -1 if the modifier name is unknown.
int qw_util_get_modifier_code(const char *codestr);

// Function to get the keysym from a key name
// the search is case insensitive
xkb_keysym_t qwu_keysym_from_name(const char *name);

void qw_util_deactivate_surface(struct wlr_surface *surface);

bool qw_surfaces_on_same_output(struct wlr_surface *surface_a, struct wlr_surface *surface_b);

// Helper from returning a qw_view pointer from a given surface
// Also sets flags to identify if surface is a layer surface or a session lock surface
struct qw_view *qw_view_from_wlr_surface(struct wlr_surface *surface, bool *is_layer_surface,
                                         bool *is_session_lock_surface);

#endif /* UTIL_H */
