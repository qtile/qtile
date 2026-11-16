#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "client-base.h"

#include "xdg-shell-client-protocol.h"

/*
Drag-and-drop source client.

Creates an xdg-toplevel which can start a client-side drag and test that the
drag has ended
*/

struct test_state {
    struct client_state base;

    struct xdg_wm_base *xdg_wm_base;
    struct wl_data_device_manager *data_device_manager;
    struct wl_data_device *data_device;

    struct wl_surface *surface;
    struct xdg_surface *xdg_surface;
    struct xdg_toplevel *toplevel;
    struct buffer *buffer;

    struct wl_pointer *pointer;
    struct wl_data_source *source;
    struct wl_data_offer *pending_offer;
    struct wl_data_offer *drag_offer;

    uint32_t button_serial;
    bool drag_ended;
};

static void toplevel_close(void *data, struct xdg_toplevel *toplevel) {
    (void)data;
    (void)toplevel;
    exit(0);
}

static void toplevel_configure(void *data, struct xdg_toplevel *toplevel, int32_t width,
                               int32_t height, struct wl_array *states) {
    (void)data;
    (void)toplevel;
    (void)width;
    (void)height;
    (void)states;
}

static const struct xdg_toplevel_listener xdg_toplevel_listener = {
    .configure = toplevel_configure,
    .close = toplevel_close,
};

static void xdg_surface_configure(void *data, struct xdg_surface *xdg_surface, uint32_t serial) {
    struct test_state *state = data;
    xdg_surface_ack_configure(xdg_surface, serial);
    wl_surface_commit(state->surface);
}

static const struct xdg_surface_listener xdg_surface_listener = {
    .configure = xdg_surface_configure,
};

static void pointer_enter(void *data, struct wl_pointer *pointer, uint32_t serial,
                          struct wl_surface *surface, wl_fixed_t sx, wl_fixed_t sy) {
    (void)data;
    (void)pointer;
    (void)serial;
    (void)surface;
    (void)sx;
    (void)sy;
}

static void pointer_leave(void *data, struct wl_pointer *pointer, uint32_t serial,
                          struct wl_surface *surface) {
    (void)data;
    (void)pointer;
    (void)serial;
    (void)surface;
}

static void pointer_motion(void *data, struct wl_pointer *pointer, uint32_t time, wl_fixed_t sx,
                           wl_fixed_t sy) {
    (void)data;
    (void)pointer;
    (void)time;
    (void)sx;
    (void)sy;
}

static void pointer_button(void *data, struct wl_pointer *pointer, uint32_t serial, uint32_t time,
                           uint32_t button, uint32_t state) {
    struct test_state *test_state = data;
    (void)pointer;
    (void)time;
    (void)button;

    if (state == WL_POINTER_BUTTON_STATE_PRESSED) {
        // The serial is needed to start the drag and is only valid while the
        // button is held down.
        test_state->button_serial = serial;
    }
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

static void source_target(void *data, struct wl_data_source *source, const char *mime_type) {
    (void)data;
    (void)source;
    (void)mime_type;
}

static void source_send(void *data, struct wl_data_source *source, const char *mime_type,
                        int32_t fd) {
    (void)data;
    (void)source;
    (void)mime_type;
    close(fd);
}

static void source_cancelled(void *data, struct wl_data_source *source) {
    struct test_state *state = data;
    (void)source;
    state->drag_ended = true;
}

static void source_dnd_drop_performed(void *data, struct wl_data_source *source) {
    (void)data;
    (void)source;
}

static void source_dnd_finished(void *data, struct wl_data_source *source) {
    struct test_state *state = data;
    (void)source;
    state->drag_ended = true;
}

static void source_action(void *data, struct wl_data_source *source, uint32_t dnd_action) {
    (void)data;
    (void)source;
    (void)dnd_action;
}

static const struct wl_data_source_listener data_source_listener = {
    .target = source_target,
    .send = source_send,
    .cancelled = source_cancelled,
    .dnd_drop_performed = source_dnd_drop_performed,
    .dnd_finished = source_dnd_finished,
    .action = source_action,
};

static void data_device_data_offer(void *data, struct wl_data_device *data_device,
                                   struct wl_data_offer *offer) {
    struct test_state *state = data;
    (void)data_device;

    if (state->pending_offer != NULL && state->pending_offer != offer) {
        wl_data_offer_destroy(state->pending_offer);
    }
    state->pending_offer = offer;
}

static void data_device_enter(void *data, struct wl_data_device *data_device, uint32_t serial,
                              struct wl_surface *surface, wl_fixed_t x, wl_fixed_t y,
                              struct wl_data_offer *offer) {
    struct test_state *state = data;
    (void)data_device;
    (void)serial;
    (void)surface;
    (void)x;
    (void)y;

    if (state->drag_offer != NULL && state->drag_offer != offer) {
        wl_data_offer_destroy(state->drag_offer);
    }
    state->drag_offer = offer;
    if (state->pending_offer == offer) {
        state->pending_offer = NULL;
    }
}

static void data_device_leave(void *data, struct wl_data_device *data_device) {
    struct test_state *state = data;
    (void)data_device;

    if (state->drag_offer != NULL) {
        wl_data_offer_destroy(state->drag_offer);
        state->drag_offer = NULL;
    }
}

static void data_device_motion(void *data, struct wl_data_device *data_device, uint32_t time,
                               wl_fixed_t x, wl_fixed_t y) {
    (void)data;
    (void)data_device;
    (void)time;
    (void)x;
    (void)y;
}

static void data_device_drop(void *data, struct wl_data_device *data_device) {
    // No data transfer is performed in this test, so the offer can go away.
    data_device_leave(data, data_device);
}

static void data_device_selection(void *data, struct wl_data_device *data_device,
                                  struct wl_data_offer *offer) {
    struct test_state *state = data;
    (void)data_device;

    // Selections are unused in this test, but the offer still has to be
    // destroyed or it leaks when the display is disconnected.
    if (offer != NULL && offer != state->pending_offer) {
        wl_data_offer_destroy(offer);
    }
    if (state->pending_offer != NULL) {
        wl_data_offer_destroy(state->pending_offer);
        state->pending_offer = NULL;
    }
}

static const struct wl_data_device_listener data_device_listener = {
    .data_offer = data_device_data_offer,
    .enter = data_device_enter,
    .leave = data_device_leave,
    .motion = data_device_motion,
    .drop = data_device_drop,
    .selection = data_device_selection,
};

static void seat_capabilities(void *data, struct wl_seat *seat, uint32_t capabilities) {
    struct test_state *state = data;

    if ((capabilities & WL_SEAT_CAPABILITY_POINTER) && state->pointer == NULL) {
        state->pointer = wl_seat_get_pointer(seat);
        wl_pointer_add_listener(state->pointer, &pointer_listener, state);
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

static void wm_ping(void *data, struct xdg_wm_base *xdg_wm_base, uint32_t serial) {
    (void)data;
    xdg_wm_base_pong(xdg_wm_base, serial);
}

static const struct xdg_wm_base_listener xdg_wm_base_listener = {
    .ping = wm_ping,
};

static void registry_global(struct client_state *base, struct wl_registry *registry, uint32_t name,
                            const char *interface, uint32_t version) {
    struct test_state *state = (struct test_state *)base;

    if (strcmp(interface, xdg_wm_base_interface.name) == 0) {
        state->xdg_wm_base = wl_registry_bind(registry, name, &xdg_wm_base_interface, 1);
        xdg_wm_base_add_listener(state->xdg_wm_base, &xdg_wm_base_listener, state);

    } else if (strcmp(interface, wl_data_device_manager_interface.name) == 0) {
        state->data_device_manager = wl_registry_bind(
            registry, name, &wl_data_device_manager_interface, version < 3 ? version : 3);

    } else if (strcmp(interface, wl_seat_interface.name) == 0) {
        wl_seat_add_listener(state->base.seat, &seat_listener, state);
    }
}

static void registry_global_remove(struct client_state *base, struct wl_registry *registry,
                                   uint32_t name) {
    (void)base;
    (void)registry;
    (void)name;
}

static void cmd_create_window(struct test_state *state) {
    if (state->surface != NULL) {
        test_error("window already created");
        return;
    }

    state->surface = wl_compositor_create_surface(state->base.compositor);
    state->xdg_surface = xdg_wm_base_get_xdg_surface(state->xdg_wm_base, state->surface);
    state->toplevel = xdg_surface_get_toplevel(state->xdg_surface);

    xdg_surface_add_listener(state->xdg_surface, &xdg_surface_listener, state);
    xdg_toplevel_add_listener(state->toplevel, &xdg_toplevel_listener, state);

    // A fixed size keeps the layout from stretching the window, making it easy
    // for the tests to know where to put the pointer.
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

static void cmd_start_drag(struct test_state *state) {
    if (state->surface == NULL) {
        test_error("window has not been created");
        return;
    }

    // Dispatch any pending events so a pointer press sent just before this
    // command has been processed and its serial recorded.
    do_roundtrip(&state->base);

    if (!state->button_serial) {
        test_error("no pointer button press received");
        return;
    }

    if (state->data_device_manager == NULL) {
        test_error("wl_data_device_manager not available");
        return;
    }

    if (state->data_device == NULL) {
        state->data_device =
            wl_data_device_manager_get_data_device(state->data_device_manager, state->base.seat);
        wl_data_device_add_listener(state->data_device, &data_device_listener, state);
    }

    state->source = wl_data_device_manager_create_data_source(state->data_device_manager);
    wl_data_source_add_listener(state->source, &data_source_listener, state);
    wl_data_source_offer(state->source, "text/plain;charset=utf-8");

    wl_data_device_start_drag(state->data_device, state->source, state->surface, NULL,
                              state->button_serial);
    do_roundtrip(&state->base);

    test_ok();
}

static void cmd_unmap(struct test_state *state) {
    if (state->surface == NULL) {
        test_error("window has not been created");
        return;
    }

    wl_surface_attach(state->surface, NULL, 0, 0);
    wl_surface_commit(state->surface);
    do_roundtrip(&state->base);

    test_ok();
}

static void cmd_wait_drag_end(struct test_state *state) {
    // The button release is generated by another client, so allow the
    // compositor a moment to process it and deliver the drag's terminal event.
    for (int i = 0; i < 100 && !state->drag_ended; i++) {
        wl_display_roundtrip(state->base.display);
        usleep(10000);
    }

    if (state->drag_ended) {
        test_true();
    } else {
        test_false();
    }
}

static bool dispatch_command(struct client_state *base, const char *cmd, const char *arg) {
    struct test_state *state = (struct test_state *)base;
    (void)arg;

    if (strcmp(cmd, "create") == 0) {
        cmd_create_window(state);
    } else if (strcmp(cmd, "start_drag") == 0) {
        cmd_start_drag(state);
    } else if (strcmp(cmd, "unmap") == 0) {
        cmd_unmap(state);
    } else if (strcmp(cmd, "wait_drag_end") == 0) {
        cmd_wait_drag_end(state);
    } else if (strcmp(cmd, "quit") == 0) {
        return false;
    } else {
        test_error("unknown command: %s", cmd);
    }
    return true;
}

void setup(struct client_state *base) { (void)base; }

void cleanup(struct client_state *base) {
    struct test_state *state = (struct test_state *)base;

    if (state->source != NULL) {
        wl_data_source_destroy(state->source);
    }
    if (state->pending_offer != NULL) {
        wl_data_offer_destroy(state->pending_offer);
    }
    if (state->drag_offer != NULL) {
        wl_data_offer_destroy(state->drag_offer);
    }
    if (state->data_device != NULL) {
        wl_data_device_release(state->data_device);
    }
    if (state->buffer != NULL) {
        wl_buffer_destroy(state->buffer->wl_buffer);
        free(state->buffer);
    }
    if (state->toplevel != NULL) {
        xdg_toplevel_destroy(state->toplevel);
    }
    if (state->xdg_surface != NULL) {
        xdg_surface_destroy(state->xdg_surface);
    }
    if (state->surface != NULL) {
        wl_surface_destroy(state->surface);
    }
    if (state->pointer != NULL) {
        wl_pointer_destroy(state->pointer);
    }
    if (state->data_device_manager != NULL) {
        wl_data_device_manager_destroy(state->data_device_manager);
    }
    if (state->xdg_wm_base != NULL) {
        xdg_wm_base_destroy(state->xdg_wm_base);
    }
}

int main(void) {
    struct test_state state = {0};

    const struct client_ops ops = {.setup = setup,
                                   .registry_global = registry_global,
                                   .registry_global_remove = registry_global_remove,
                                   .dispatch_command = dispatch_command,
                                   .cleanup = cleanup};

    return client_run(&state.base, &ops);
}
