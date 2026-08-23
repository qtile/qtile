#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "client-base.h"
#include "keyboard-shortcuts-inhibit-unstable-v1-client-protocol.h"
#include "xdg-shell-client-protocol.h"

struct test_state {
    struct client_state base;
    struct zwp_keyboard_shortcuts_inhibit_manager_v1 *inhibit_mgr;
    struct zwp_keyboard_shortcuts_inhibitor_v1 *inhibitor;
    bool inhibitor_active;
    struct xdg_wm_base *xdg_wm_base;
    struct wl_surface *surface;
    struct xdg_surface *xdg_surface;
    struct xdg_toplevel *toplevel;
    struct buffer *buffer;
    struct wl_keyboard *keyboard;

    uint32_t mods_depressed;
    struct {
        uint32_t key;
        uint32_t mods;
    } keypress;
};

static void shortcut_inhibitor_active(
    void *data, struct zwp_keyboard_shortcuts_inhibitor_v1 *zwp_keyboard_shortcuts_inhibitor_v1) {
    struct test_state *state = data;
    state->inhibitor_active = true;
}

static void shortcut_inhibitor_inactive(
    void *data, struct zwp_keyboard_shortcuts_inhibitor_v1 *zwp_keyboard_shortcuts_inhibitor_v1) {
    struct test_state *state = data;
    state->inhibitor_active = false;
}

struct zwp_keyboard_shortcuts_inhibitor_v1_listener inhibitor_listener = {
    .active = shortcut_inhibitor_active, .inactive = shortcut_inhibitor_inactive};

static void toplevel_close(void *data, struct xdg_toplevel *t) { exit(0); }

static void toplevel_configure(void *data, struct xdg_toplevel *t, int32_t w, int32_t h,
                               struct wl_array *states) {
    (void)data;
    (void)t;
    (void)w;
    (void)h;
    (void)states;
}

static const struct xdg_toplevel_listener xdg_toplevel_listener = {
    .configure = toplevel_configure,
    .close = toplevel_close,
};

static void xdg_surface_configure(void *data, struct xdg_surface *surf, uint32_t serial) {
    struct test_state *state = data;
    xdg_surface_ack_configure(surf, serial);
    wl_surface_commit(state->surface);
}

static const struct xdg_surface_listener xdg_surface_listener = {
    .configure = xdg_surface_configure,
};

static void wm_ping(void *data, struct xdg_wm_base *wm, uint32_t serial) {
    xdg_wm_base_pong(wm, serial);
}

static const struct xdg_wm_base_listener xdg_wm_listener = {
    .ping = wm_ping,
};

static void keyboard_keymap(void *data, struct wl_keyboard *keyboard, uint32_t format, int fd,
                            uint32_t size) {
    close(fd); // Ignore the keymap
}

static void keyboard_enter(void *data, struct wl_keyboard *keyboard, uint32_t serial,
                           struct wl_surface *surface, struct wl_array *keys) {}

static void keyboard_leave(void *data, struct wl_keyboard *keyboard, uint32_t serial,
                           struct wl_surface *surface) {}

static void keyboard_key(void *data, struct wl_keyboard *keyboard, uint32_t serial, uint32_t time,
                         uint32_t key, uint32_t pressed_state) {
    struct test_state *state = data;
    if (pressed_state == WL_KEYBOARD_KEY_STATE_PRESSED) {
        state->keypress.key = key;
        state->keypress.mods = state->mods_depressed;
    }
}

static void keyboard_modifiers(void *data, struct wl_keyboard *keyboard, uint32_t serial,
                               uint32_t depressed, uint32_t latched, uint32_t locked,
                               uint32_t group) {
    struct test_state *state = data;
    state->mods_depressed = depressed;
}

static void keyboard_repeat_info(void *data, struct wl_keyboard *keyboard, int32_t rate,
                                 int32_t delay) {}

static const struct wl_keyboard_listener keyboard_listener = {
    .keymap = keyboard_keymap,
    .enter = keyboard_enter,
    .leave = keyboard_leave,
    .key = keyboard_key,
    .modifiers = keyboard_modifiers,
    .repeat_info = keyboard_repeat_info,
};

static void seat_capabilities(void *data, struct wl_seat *seat, uint32_t capabilities) {
    struct test_state *state = data;

    if ((capabilities & WL_SEAT_CAPABILITY_KEYBOARD) && !state->keyboard) {
        state->keyboard = wl_seat_get_keyboard(seat);
        wl_keyboard_add_listener(state->keyboard, &keyboard_listener, state);
    } else if (!(capabilities & WL_SEAT_CAPABILITY_KEYBOARD) && state->keyboard) {
        wl_keyboard_destroy(state->keyboard);
        state->keyboard = NULL;
    }
}

static void seat_name(void *data, struct wl_seat *seat, const char *name) {}

static const struct wl_seat_listener seat_listener = {
    .capabilities = seat_capabilities,
    .name = seat_name,
};

static void registry_handler(struct client_state *base, struct wl_registry *registry, uint32_t name,
                             const char *interface, uint32_t version) {
    struct test_state *state = (struct test_state *)base;

    if (strcmp(interface, xdg_wm_base_interface.name) == 0) {
        state->xdg_wm_base = wl_registry_bind(registry, name, &xdg_wm_base_interface, 1);
        xdg_wm_base_add_listener(state->xdg_wm_base, &xdg_wm_listener, state);
    } else if (strcmp(interface, zwp_keyboard_shortcuts_inhibit_manager_v1_interface.name) == 0) {
        state->inhibit_mgr = wl_registry_bind(
            registry, name, &zwp_keyboard_shortcuts_inhibit_manager_v1_interface, 1);
    } else if (strcmp(interface, wl_seat_interface.name) == 0) {
        // The seat is already bound but we want a listener for keyboard events
        wl_seat_add_listener(state->base.seat, &seat_listener, state);
    }
}

void cmd_create_window(struct test_state *state) {
    state->surface = wl_compositor_create_surface(state->base.compositor);

    state->xdg_surface = xdg_wm_base_get_xdg_surface(state->xdg_wm_base, state->surface);
    state->toplevel = xdg_surface_get_toplevel(state->xdg_surface);

    xdg_surface_add_listener(state->xdg_surface, &xdg_surface_listener, state);
    xdg_toplevel_add_listener(state->toplevel, &xdg_toplevel_listener, state);

    // Set fixed size so qtile will float window
    xdg_toplevel_set_min_size(state->toplevel, 300, 300);
    xdg_toplevel_set_max_size(state->toplevel, 300, 300);

    wl_surface_commit(state->surface);
    do_roundtrip(&state->base);

    // Create contents of window
    state->buffer = create_buffer(&state->base, 300, 300, 0xFF606060);

    wl_surface_attach(state->surface, state->buffer->wl_buffer, 0, 0);
    wl_surface_damage_buffer(state->surface, 0, 0, INT32_MAX, INT32_MAX);
    wl_surface_commit(state->surface);
    do_roundtrip(&state->base);

    test_ok();
}

static void cmd_inhibit(struct test_state *state) {
    if (state->surface == NULL) {
        test_error("inhibitor requires a surface.");
        return;
    }

    state->inhibitor = zwp_keyboard_shortcuts_inhibit_manager_v1_inhibit_shortcuts(
        state->inhibit_mgr, state->surface, state->base.seat);
    zwp_keyboard_shortcuts_inhibitor_v1_add_listener(state->inhibitor, &inhibitor_listener, state);
    do_roundtrip(&state->base);

    // Compositor will raise an error if we request an inhibitor more than once for the same
    // surface.
    if (!compositor_raised_error(&state->base)) {
        test_ok();
    }
}

static void cmd_uninhibit(struct test_state *state) {
    zwp_keyboard_shortcuts_inhibitor_v1_destroy(state->inhibitor);
    state->inhibitor == NULL;
    state->inhibitor_active = false;
    do_roundtrip(&state->base);
    test_ok();
}

static bool dispatch_command(struct client_state *base, const char *cmd, const char *arg) {
    struct test_state *state = (struct test_state *)base;

    if (strcmp(cmd, "show") == 0) {
        cmd_create_window(state);
    } else if (strcmp(cmd, "get_keypress") == 0) {
        test_message("key: %u mods: %u", state->keypress.key, state->keypress.mods);
        test_ok();
    } else if (strcmp(cmd, "clear_keypress") == 0) {
        state->keypress.key = 0;
        state->keypress.mods = 0;
        test_ok();
    } else if (strcmp(cmd, "inhibit") == 0) {
        cmd_inhibit(state);
    } else if (strcmp(cmd, "uninhibit") == 0) {
        cmd_uninhibit(state);
    } else if (strcmp(cmd, "quit") == 0) {
        return false;
    }
    return true;
}

void cleanup(struct client_state *base) {
    struct test_state *state = (struct test_state *)base;

    if (state->surface) {
        wl_surface_destroy(state->surface);
    }

    if (state->inhibitor != NULL) {
        zwp_keyboard_shortcuts_inhibitor_v1_destroy(state->inhibitor);
    }
}

int main(void) {
    struct test_state state = {0};

    const struct client_ops ops = {.registry_global = registry_handler,
                                   .dispatch_command = dispatch_command,
                                   .cleanup = cleanup};

    return client_run(&state.base, &ops);
}
