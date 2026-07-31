#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "client-base.h"
#include "xdg-shell-client-protocol.h"
#include "xdg-system-bell-v1-client-protocol.h"

struct test_state {
    struct client_state base;

    struct xdg_system_bell_v1 *system_bell;

    struct xdg_wm_base *xdg_wm_base;
    struct wl_surface *surface;
    struct xdg_surface *xdg_surface;
    struct xdg_toplevel *toplevel;
    struct buffer *buffer;
};

static void xdg_surface_configure(void *data, struct xdg_surface *surf, uint32_t serial) {
    struct test_state *state = data;
    xdg_surface_ack_configure(surf, serial);
    wl_surface_commit(state->surface);
}

static const struct xdg_surface_listener xdg_surface_listener = {
    .configure = xdg_surface_configure,
};

static void registry_handler(struct client_state *base, struct wl_registry *registry, uint32_t name,
                             const char *interface, uint32_t version) {
    struct test_state *state = (struct test_state *)base;

    if (strcmp(interface, xdg_system_bell_v1_interface.name) == 0) {
        uint32_t bind_version = (version < 1) ? version : 1;
        state->system_bell =
            wl_registry_bind(registry, name, &xdg_system_bell_v1_interface, bind_version);
    } else if (strcmp(interface, xdg_wm_base_interface.name) == 0) {
        state->xdg_wm_base = wl_registry_bind(registry, name, &xdg_wm_base_interface, 1);
        // xdg_wm_base_add_listener(state->xdg_wm_base, &xdg_wm_listener, state);
    }
}

static void cmd_ring(struct test_state *state) {
    xdg_system_bell_v1_ring(state->system_bell, state->surface);
    test_ok();
}

static void cmd_create_window(struct test_state *state) {
    state->surface = wl_compositor_create_surface(state->base.compositor);

    state->xdg_surface = xdg_wm_base_get_xdg_surface(state->xdg_wm_base, state->surface);
    state->toplevel = xdg_surface_get_toplevel(state->xdg_surface);

    xdg_surface_add_listener(state->xdg_surface, &xdg_surface_listener, state);

    xdg_toplevel_set_min_size(state->toplevel, 300, 300);
    xdg_toplevel_set_max_size(state->toplevel, 300, 300);

    wl_surface_commit(state->surface);
    do_roundtrip(&state->base);

    state->buffer = create_buffer(&state->base, 300, 300, 0xFF606060);

    wl_surface_attach(state->surface, state->buffer->wl_buffer, 0, 0);
    wl_surface_damage_buffer(state->surface, 0, 0, INT32_MAX, INT32_MAX);
    wl_surface_commit(state->surface);
    do_roundtrip(&state->base);

    test_ok();
}

static bool dispatch_command(struct client_state *base, const char *cmd, const char *arg) {
    struct test_state *state = (struct test_state *)base;

    if (strcmp(cmd, "ring") == 0) {
        cmd_ring(state);
    } else if (strcmp(cmd, "show") == 0) {
        cmd_create_window(state);
    } else if (strcmp(cmd, "quit") == 0) {
        return false;
    }

    return true;
}

void cleanup(struct client_state *base) {
    struct test_state *state = (struct test_state *)base;
    if (state->system_bell != NULL) {
        xdg_system_bell_v1_destroy(state->system_bell);
    }
    if (state->buffer) {
        wl_buffer_destroy(state->buffer->wl_buffer);
        free(state->buffer);
    }
    if (state->toplevel) {
        xdg_toplevel_destroy(state->toplevel);
    }
    if (state->xdg_surface) {
        xdg_surface_destroy(state->xdg_surface);
    }
    if (state->surface) {
        wl_surface_destroy(state->surface);
    }
    if (state->xdg_wm_base) {
        xdg_wm_base_destroy(state->xdg_wm_base);
    }
}

int main(void) {
    struct test_state state = {0};

    const struct client_ops ops = {.registry_global = registry_handler,
                                   .dispatch_command = dispatch_command,
                                   .cleanup = cleanup};

    return client_run(&state.base, &ops);
}
