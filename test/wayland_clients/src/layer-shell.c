#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "client-base.h"

#include "wlr-layer-shell-unstable-v1-client-protocol.h"

struct output_entry {
    struct wl_output *wl_output;
    int32_t width, height;
    struct wl_list link;
};

struct test_state {
    struct client_state base;

    struct zwlr_layer_shell_v1 *layer_shell;

    struct wl_surface *surface;
    struct zwlr_layer_surface_v1 *layer_surface;

    struct wl_list outputs; // output_entry
    struct wl_output *layer_output;

    uint32_t anchors;
    uint32_t layer;

    struct wl_keyboard *keyboard;
    uint32_t keyboard_mode;
    bool has_keyboard;

    struct buffer *buffer;

    uint32_t width;
    uint32_t height;

    bool configured;
};

const int EXCLUSIVE_ZONE_SIZE = 40;

static void set_size(struct test_state *state) {
    uint32_t width = 0;
    uint32_t height = 0;

    bool horiz_constrained = (state->anchors & ZWLR_LAYER_SURFACE_V1_ANCHOR_LEFT) &&
                             (state->anchors & ZWLR_LAYER_SURFACE_V1_ANCHOR_RIGHT);

    bool vert_constrained = (state->anchors & ZWLR_LAYER_SURFACE_V1_ANCHOR_TOP) &&
                            (state->anchors & ZWLR_LAYER_SURFACE_V1_ANCHOR_BOTTOM);

    if (vert_constrained && !horiz_constrained) {
        width = EXCLUSIVE_ZONE_SIZE; // vertical bar
    } else if (horiz_constrained && !vert_constrained) {
        height = EXCLUSIVE_ZONE_SIZE; // horizontal bar
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

static void set_keyboard(struct test_state *state, const char *arg) {
    uint32_t keyboard = 0;
    if (strcmp(arg, "none") == 0) {
        keyboard = ZWLR_LAYER_SURFACE_V1_KEYBOARD_INTERACTIVITY_NONE;
    } else if (strcmp(arg, "exclusive") == 0) {
        keyboard = ZWLR_LAYER_SURFACE_V1_KEYBOARD_INTERACTIVITY_EXCLUSIVE;
    } else if (strcmp(arg, "ondemand") == 0) {
        keyboard = ZWLR_LAYER_SURFACE_V1_KEYBOARD_INTERACTIVITY_ON_DEMAND;
    } else {
        test_error("unknown keyboard mode '%s'", arg);
        state->keyboard_mode = 0;
    }
    state->keyboard_mode = keyboard;
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

static void set_output(struct test_state *state, const char *arg) {
    struct output_entry *oe;
    int index = 0;
    int target = atoi(arg);

    wl_list_for_each(oe, &state->outputs, link) {
        if (index == target) {
            state->layer_output = oe->wl_output;
            test_ok();
            return;
        }
        index++;
    }
    test_error("no output at index %d.", target);
}

// Function is for checking that compositor does not crash after an output has been
// killed.
static void send_commit(struct test_state *state) {
    if (state->layer_surface == NULL) {
        test_error("no layer surface.");
        return;
    }

    zwlr_layer_surface_v1_set_margin(state->layer_surface, 15, 0, 0, 0);
    zwlr_layer_surface_v1_set_exclusive_zone(state->layer_surface, EXCLUSIVE_ZONE_SIZE + 15);
    wl_surface_commit(state->surface);

    do_roundtrip(&state->base);

    int err = wl_display_get_error(state->base.display);
    if (err != 0) {
        test_error("display error after commit");
        return;
    }

    test_ok();
}

static void output_geometry(void *data, struct wl_output *wl_output, int32_t x, int32_t y,
                            int32_t physical_width, int32_t physical_height, int32_t subpixel,
                            const char *make, const char *model, int32_t transform) {
    struct output_entry *oe = data;
    (void)x;
    (void)y;
    (void)wl_output;
    (void)physical_width;
    (void)physical_height;
    (void)subpixel;
    (void)make;
    (void)model;
    (void)transform;
}

static void output_mode(void *data, struct wl_output *wl_output, uint32_t flags, int32_t width,
                        int32_t height, int32_t refresh) {
    struct output_entry *oe = data;
    if (flags & WL_OUTPUT_MODE_CURRENT) {
        oe->width = width;
        oe->height = height;
    }
    (void)wl_output;
    (void)refresh;
}

static void output_done(void *data, struct wl_output *wl_output) {
    (void)data;
    (void)wl_output;
}
static void output_scale(void *data, struct wl_output *wl_output, int32_t factor) {
    (void)data;
    (void)wl_output;
    (void)factor;
}
static void output_name(void *data, struct wl_output *wl_output, const char *name) {
    (void)data;
    (void)wl_output;
    (void)name;
}
static void output_description(void *data, struct wl_output *wl_output, const char *desc) {
    (void)data;
    (void)wl_output;
    (void)desc;
}

static const struct wl_output_listener output_listener = {
    .geometry = output_geometry,
    .mode = output_mode,
    .done = output_done,
    .scale = output_scale,
    .name = output_name,
    .description = output_description,
};

static void handle_configure(void *data, struct zwlr_layer_surface_v1 *surface, uint32_t serial,
                             uint32_t width, uint32_t height) {
    struct test_state *state = data;

    state->width = width ?: 300;
    state->height = height ?: EXCLUSIVE_ZONE_SIZE;

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

    state->layer_surface = zwlr_layer_shell_v1_get_layer_surface(
        state->layer_shell, state->surface, state->layer_output, state->layer, "test");

    zwlr_layer_surface_v1_add_listener(state->layer_surface, &layer_shell_listener, state);

    zwlr_layer_surface_v1_set_anchor(state->layer_surface, state->anchors);

    zwlr_layer_surface_v1_set_keyboard_interactivity(state->layer_surface, state->keyboard_mode);

    set_size(state);

    zwlr_layer_surface_v1_set_exclusive_zone(state->layer_surface, EXCLUSIVE_ZONE_SIZE);

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

static void keyboard_keymap(void *data, struct wl_keyboard *keyboard, uint32_t format, int fd,
                            uint32_t size) {
    close(fd); // Ignore the keymap
}

static void keyboard_enter(void *data, struct wl_keyboard *keyboard, uint32_t serial,
                           struct wl_surface *surface, struct wl_array *keys) {
    struct test_state *state = data;
    state->has_keyboard = true;
}

static void keyboard_leave(void *data, struct wl_keyboard *keyboard, uint32_t serial,
                           struct wl_surface *surface) {
    struct test_state *state = data;
    state->has_keyboard = false;
}

static void keyboard_key(void *data, struct wl_keyboard *keyboard, uint32_t serial, uint32_t time,
                         uint32_t key, uint32_t pressed_state) {}

static void keyboard_modifiers(void *data, struct wl_keyboard *keyboard, uint32_t serial,
                               uint32_t depressed, uint32_t latched, uint32_t locked,
                               uint32_t group) {}

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

static void setup_keyboard_listener(struct test_state *state) {
    state->keyboard = wl_seat_get_keyboard(state->base.seat);

    wl_keyboard_add_listener(state->keyboard, &keyboard_listener, state);
}

static void registry_handler(struct client_state *base, struct wl_registry *registry, uint32_t name,
                             const char *interface, uint32_t version) {
    struct test_state *state = (struct test_state *)base;

    if (strcmp(interface, zwlr_layer_shell_v1_interface.name) == 0) {
        state->layer_shell = wl_registry_bind(registry, name, &zwlr_layer_shell_v1_interface,
                                              version < 4 ? version : 4);
    } else if (strcmp(interface, wl_output_interface.name) == 0) {
        struct output_entry *oe = calloc(1, sizeof(*oe));
        oe->wl_output = wl_registry_bind(registry, name, &wl_output_interface, 4);
        wl_output_add_listener(oe->wl_output, &output_listener, oe);
        wl_list_insert(&state->outputs, &oe->link);
    }

    if (state->keyboard == NULL && state->base.seat != NULL) {
        setup_keyboard_listener(state);
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
    } else if (strcmp(cmd, "keyboard") == 0) {
        set_keyboard(state, arg);
    } else if (strcmp(cmd, "output") == 0) {
        set_output(state, arg);
    } else if (strcmp(cmd, "send_commit") == 0) {
        send_commit(state);
    } else if (strcmp(cmd, "status") == 0) {
        test_ok();
    } else if (strcmp(cmd, "has_keyboard") == 0) {
        if (state->has_keyboard) {
            test_true();
        } else {
            test_false();
        }
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

    wl_list_init(&state->outputs);
    state->layer_output = NULL;
}

void cleanup(struct client_state *base) {
    struct test_state *state = (struct test_state *)base;

    if (state->layer_surface) {
        zwlr_layer_surface_v1_destroy(state->layer_surface);
    }
    if (state->surface) {
        wl_surface_destroy(state->surface);
    }
}

int main(void) {
    struct test_state state = {0};

    const struct client_ops ops = {.setup = setup,
                                   .registry_global = registry_handler,
                                   .dispatch_command = dispatch_command,
                                   .cleanup = cleanup};

    return client_run(&state.base, &ops);
}
