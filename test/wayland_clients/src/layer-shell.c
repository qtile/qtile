#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "client-base.h"

#include "wlr-layer-shell-unstable-v1-client-protocol.h"

struct test_state {
    struct client_state base;

    struct zwlr_layer_shell_v1 *layer_shell;

    struct wl_surface *surface;
    struct zwlr_layer_surface_v1 *layer_surface;

    uint32_t anchors;
    uint32_t layer;

    struct buffer *buffer;

    uint32_t width;
    uint32_t height;

    bool configured;
};

static void set_size(struct test_state *state) {
    uint32_t width = 0;
    uint32_t height = 0;

    bool horiz_constrained = (state->anchors & ZWLR_LAYER_SURFACE_V1_ANCHOR_LEFT) &&
                             (state->anchors & ZWLR_LAYER_SURFACE_V1_ANCHOR_RIGHT);

    bool vert_constrained = (state->anchors & ZWLR_LAYER_SURFACE_V1_ANCHOR_TOP) &&
                            (state->anchors & ZWLR_LAYER_SURFACE_V1_ANCHOR_BOTTOM);

    if (vert_constrained && !horiz_constrained) {
        width = 40; // vertical bar
    } else if (horiz_constrained && !vert_constrained) {
        height = 40; // horizontal bar
    } else if (!horiz_constrained && !vert_constrained) {
        width = 300;
        height = 300;
    }

    zwlr_layer_surface_v1_set_size(state->layer_surface, width, height);
}

static void set_layer(struct test_state *state, const char *arg) {
    uint32_t layer = 0;
    if (strcmp(arg, "top") == 0) {
        layer = ZWLR_LAYER_SHELL_V1_LAYER_TOP;
    } else if (strcmp(arg, "bottom") == 0) {
        layer = ZWLR_LAYER_SHELL_V1_LAYER_BOTTOM;
    } else if (strcmp(arg, "overlay") == 0) {
        layer = ZWLR_LAYER_SHELL_V1_LAYER_OVERLAY;
    } else if (strcmp(arg, "background") == 0) {
        layer = ZWLR_LAYER_SHELL_V1_LAYER_BACKGROUND;
    } else {
        test_error("unknown layer '%s'", arg);
        state->layer = 0;
        return;
    }
    state->layer = layer;
    test_ok();
}

static void set_anchor(struct test_state *state, const char *arg) {
    uint32_t anchors = 0;

    if (arg == NULL) {
        state->anchors = anchors;
        return;
    }

    for (const char *c = arg; *c; c++) {
        switch (*c) {
        case 'T':
            anchors |= ZWLR_LAYER_SURFACE_V1_ANCHOR_TOP;
            break;

        case 'B':
            anchors |= ZWLR_LAYER_SURFACE_V1_ANCHOR_BOTTOM;
            break;

        case 'L':
            anchors |= ZWLR_LAYER_SURFACE_V1_ANCHOR_LEFT;
            break;

        case 'R':
            anchors |= ZWLR_LAYER_SURFACE_V1_ANCHOR_RIGHT;
            break;

        default:
            test_error("unknown anchor '%c'", *c);
            state->anchors = 0;
            return;
        }
    }

    state->anchors = anchors;
    test_ok();
}

static void handle_configure(void *data, struct zwlr_layer_surface_v1 *surface, uint32_t serial,
                             uint32_t width, uint32_t height) {
    struct test_state *state = data;

    state->width = width ?: 300;
    state->height = height ?: 40;

    zwlr_layer_surface_v1_ack_configure(surface, serial);

    if (!state->buffer) {
        state->buffer = create_buffer(&state->base, state->width, state->height, 0xff00ff00);
    }

    wl_surface_attach(state->surface, state->buffer->wl_buffer, 0, 0);

    wl_surface_damage_buffer(state->surface, 0, 0, state->width, state->height);

    wl_surface_commit(state->surface);

    state->configured = true;
}

static void handle_closed(void *data, struct zwlr_layer_surface_v1 *surface) {
    test_message("closed");
}

static const struct zwlr_layer_surface_v1_listener layer_shell_listener = {
    .configure = handle_configure,
    .closed = handle_closed,
};

static void create_layer_surface(struct test_state *state) {
    state->surface = wl_compositor_create_surface(state->base.compositor);

    state->layer_surface = zwlr_layer_shell_v1_get_layer_surface(state->layer_shell, state->surface,
                                                                 NULL, state->layer, "test");

    zwlr_layer_surface_v1_add_listener(state->layer_surface, &layer_shell_listener, state);

    zwlr_layer_surface_v1_set_anchor(state->layer_surface, state->anchors);

    set_size(state);

    zwlr_layer_surface_v1_set_exclusive_zone(state->layer_surface, 40);

    wl_surface_commit(state->surface);
    do_roundtrip(&state->base);
    if (state->configured) {
        test_ok();
    } else {
        test_error("layer not configured.");
    }
}

static void destroy_layer_surface(struct test_state *state) {
    if (state->buffer) {
        destroy_buffer(state->buffer);
        state->buffer = NULL;
    }

    if (state->layer_surface) {
        zwlr_layer_surface_v1_destroy(state->layer_surface);
        state->layer_surface = NULL;
    }

    if (state->surface) {
        wl_surface_destroy(state->surface);
        state->surface = NULL;
    }

    state->configured = false;
    test_ok();
}

static void registry_handler(struct client_state *base, struct wl_registry *registry, uint32_t name,
                             const char *interface, uint32_t version) {
    struct test_state *state = (struct test_state *)base;

    if (strcmp(interface, zwlr_layer_shell_v1_interface.name) == 0) {
        state->layer_shell = wl_registry_bind(registry, name, &zwlr_layer_shell_v1_interface,
                                              version < 4 ? version : 4);
    }
}

static bool dispatch_command(struct client_state *base, const char *cmd, const char *arg) {
    struct test_state *state = (struct test_state *)base;

    if (strcmp(cmd, "show") == 0) {
        create_layer_surface(state);
    } else if (strcmp(cmd, "close") == 0) {
        destroy_layer_surface(state);
    } else if (strcmp(cmd, "anchor") == 0) {
        set_anchor(state, arg);
    } else if (strcmp(cmd, "layer") == 0) {
        set_layer(state, arg);
    } else if (strcmp(cmd, "quit") == 0) {
        return false;
    }
    return true;
}

void setup(struct client_state *base) {
    struct test_state *state = (struct test_state *)base;

    state->anchors = ZWLR_LAYER_SURFACE_V1_ANCHOR_TOP | ZWLR_LAYER_SURFACE_V1_ANCHOR_LEFT |
                     ZWLR_LAYER_SURFACE_V1_ANCHOR_RIGHT;
    state->layer = ZWLR_LAYER_SHELL_V1_LAYER_TOP;
}

int main(void) {
    struct test_state state = {0};

    const struct client_ops ops = {
        .setup = setup, .registry_global = registry_handler, .dispatch_command = dispatch_command};

    return client_run(&state.base, &ops);
}
