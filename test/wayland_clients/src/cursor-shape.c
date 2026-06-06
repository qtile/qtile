#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "client-base.h"

#include "cursor-shape-v1-client-protocol.h"
#include "xdg-shell-client-protocol.h"

struct test_state {
    struct client_state base;

    struct xdg_wm_base *xdg_wm_base;
    struct wl_surface *surface;
    struct xdg_surface *xdg_surface;
    struct xdg_toplevel *toplevel;
    struct wl_pointer *pointer;
    struct wp_cursor_shape_manager_v1 *cursor_manager;
    struct wp_cursor_shape_device_v1 *cursor_device;
    uint32_t requested_shape;
    uint32_t enter_serial;
    uint32_t configure_serial;
    struct buffer *buffer;
};

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

static void set_shape(struct test_state *state, uint32_t serial, uint32_t shape) {
    if (state->cursor_device == NULL)
        return;

    wp_cursor_shape_device_v1_set_shape(state->cursor_device, serial, shape);
}

static void pointer_enter(void *data, struct wl_pointer *p, uint32_t serial,
                          struct wl_surface *surf, wl_fixed_t x, wl_fixed_t y) {
    struct test_state *state = data;
    state->enter_serial = serial;

    if (state->cursor_device == NULL) {
        test_error("cursor_device is NULL at enter");
        return;
    }

    set_shape(state, serial, state->requested_shape);
    // pointer_entered = true;
}

static void pointer_leave(void *data, struct wl_pointer *p, uint32_t serial,
                          struct wl_surface *surf) {
    (void)data;
    (void)p;
    (void)serial;
    (void)surf;
}

static void pointer_motion(void *data, struct wl_pointer *p, uint32_t time, wl_fixed_t x,
                           wl_fixed_t y) {
    (void)data;
    (void)p;
    (void)time;
    (void)x;
    (void)y;
}

static void pointer_button(void *data, struct wl_pointer *pointer, uint32_t serial, uint32_t time,
                           uint32_t button, uint32_t state) {
    (void)data;
    (void)pointer;
    (void)serial;
    (void)time;
    (void)button;
    (void)state;
}

static void pointer_axis(void *data, struct wl_pointer *pointer, uint32_t time, uint32_t axis,
                         wl_fixed_t value) {
    (void)data;
    (void)pointer;
    (void)time;
    (void)axis;
    (void)value;
}

static void pointer_frame(void *data, struct wl_pointer *pointer) {
    (void)data;
    (void)pointer;
}

static void pointer_axis_source(void *data, struct wl_pointer *pointer, uint32_t axis_source) {
    (void)data;
    (void)pointer;
    (void)axis_source;
}

static void pointer_axis_stop(void *data, struct wl_pointer *pointer, uint32_t time,
                              uint32_t axis) {
    (void)data;
    (void)pointer;
    (void)time;
    (void)axis;
}

static void pointer_axis_discrete(void *data, struct wl_pointer *pointer, uint32_t axis,
                                  int32_t discrete) {
    (void)data;
    (void)pointer;
    (void)axis;
    (void)discrete;
}

static void pointer_axis_value120(void *data, struct wl_pointer *pointer, uint32_t axis,
                                  int32_t value120) {
    (void)data;
    (void)pointer;
    (void)axis;
    (void)value120;
}

static void pointer_axis_relative_direction(void *data, struct wl_pointer *pointer, uint32_t axis,
                                            uint32_t direction) {
    (void)data;
    (void)pointer;
    (void)axis;
    (void)direction;
}

static const struct wl_pointer_listener pointer_listener = {
    .enter = pointer_enter,
    .leave = pointer_leave,
    .motion = pointer_motion,
    .button = pointer_button,
    .axis = pointer_axis,
    .frame = pointer_frame,
    .axis_source = pointer_axis_source,
    .axis_stop = pointer_axis_stop,
    .axis_discrete = pointer_axis_discrete,
    .axis_value120 = pointer_axis_value120,
    .axis_relative_direction = pointer_axis_relative_direction,
};

static void seat_capabilities(void *data, struct wl_seat *seat, uint32_t caps) {
    struct test_state *state = data;
    if (caps & WL_SEAT_CAPABILITY_POINTER) {
        state->pointer = wl_seat_get_pointer(state->base.seat);

        wl_pointer_add_listener(state->pointer, &pointer_listener, state);
        state->cursor_device =
            wp_cursor_shape_manager_v1_get_pointer(state->cursor_manager, state->pointer);
    }
}

static void seat_name(void *data, struct wl_seat *seat, const char *name) {
    (void)data;
    (void)seat;
    (void)name;
}

static const struct wl_seat_listener seat_listener = {
    .capabilities = seat_capabilities,
    .name = seat_name,
};

static void wm_ping(void *data, struct xdg_wm_base *wm, uint32_t serial) {
    xdg_wm_base_pong(wm, serial);
}

static const struct xdg_wm_base_listener xdg_wm_listener = {
    .ping = wm_ping,
};

static void registry_handler(struct client_state *base, struct wl_registry *registry, uint32_t name,
                             const char *interface, uint32_t version) {
    struct test_state *state = (struct test_state *)base;

    if (strcmp(interface, xdg_wm_base_interface.name) == 0) {
        state->xdg_wm_base = wl_registry_bind(registry, name, &xdg_wm_base_interface, 1);
        xdg_wm_base_add_listener(state->xdg_wm_base, &xdg_wm_listener, state);

    } else if (strcmp(interface, wp_cursor_shape_manager_v1_interface.name) == 0) {
        state->cursor_manager =
            wl_registry_bind(registry, name, &wp_cursor_shape_manager_v1_interface, 1);

    } else if (strcmp(interface, wl_seat_interface.name) == 0) {
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

static bool dispatch_command(struct client_state *base, const char *cmd, const char *arg) {
    struct test_state *state = (struct test_state *)base;

    if (strcmp(cmd, "crosshair") == 0) {
        state->requested_shape = WP_CURSOR_SHAPE_DEVICE_V1_SHAPE_CROSSHAIR;
        cmd_create_window(state);
    } else if (strcmp(cmd, "text") == 0) {
        state->requested_shape = WP_CURSOR_SHAPE_DEVICE_V1_SHAPE_TEXT;
        cmd_create_window(state);
    } else if (strcmp(cmd, "wait") == 0) {
        state->requested_shape = WP_CURSOR_SHAPE_DEVICE_V1_SHAPE_WAIT;
        cmd_create_window(state);
    } else if (strcmp(cmd, "help") == 0) {
        state->requested_shape = WP_CURSOR_SHAPE_DEVICE_V1_SHAPE_HELP;
        cmd_create_window(state);
    } else if (strcmp(cmd, "grab") == 0) {
        state->requested_shape = WP_CURSOR_SHAPE_DEVICE_V1_SHAPE_GRAB;
        cmd_create_window(state);
    } else if (strcmp(cmd, "quit") == 0) {
        return false;
    }
    return true;
}

void setup(struct client_state *base) {
    struct test_state *state = (struct test_state *)base;
    state->requested_shape = WP_CURSOR_SHAPE_DEVICE_V1_SHAPE_CROSSHAIR;
}

void cleanup(struct client_state *base) {
    struct test_state *state = (struct test_state *)base;
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
