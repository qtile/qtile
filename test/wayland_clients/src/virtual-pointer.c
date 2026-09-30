/* vpointer.c - virtual pointer test client */

#define _POSIX_C_SOURCE 200809L

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "client-base.h"
#include "wlr-virtual-pointer-unstable-v1-client-protocol.h"

struct test_state {
    struct client_state base;
    struct zwlr_virtual_pointer_manager_v1 *vpointer_mgr;
    struct zwlr_virtual_pointer_v1 *vpointer;
    // Size of the layout that absolute coordinates are scaled against.
    // Must be set with the "extent" command before any "move".
    uint32_t extent_w;
    uint32_t extent_h;
};

static uint32_t now_ms(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint32_t)(ts.tv_sec * 1000 + ts.tv_nsec / 1000000);
}

static void registry_handler(struct client_state *base, struct wl_registry *registry, uint32_t name,
                             const char *interface, uint32_t version) {
    struct test_state *state = (struct test_state *)base;

    if (strcmp(interface, zwlr_virtual_pointer_manager_v1_interface.name) == 0) {
        state->vpointer_mgr =
            wl_registry_bind(registry, name, &zwlr_virtual_pointer_manager_v1_interface, 1);
    }

    // Globals can arrive in either order, so retry on every callback.
    if (state->vpointer == NULL && state->vpointer_mgr != NULL && state->base.seat != NULL) {
        state->vpointer = zwlr_virtual_pointer_manager_v1_create_virtual_pointer(
            state->vpointer_mgr, state->base.seat);
    }
}

static void cmd_extent(struct test_state *state, const char *arg) {
    unsigned w, h;
    if (arg == NULL || sscanf(arg, "%u %u", &w, &h) != 2 || w == 0 || h == 0) {
        test_error("extent requires a positive width and height.");
        return;
    }
    state->extent_w = w;
    state->extent_h = h;
    test_ok();
}

static void cmd_move(struct test_state *state, const char *arg) {
    unsigned x, y;
    if (arg == NULL || sscanf(arg, "%u %u", &x, &y) != 2) {
        test_error("move requires x and y.");
        return;
    }
    if (state->extent_w == 0 || state->extent_h == 0) {
        test_error("extent must be set before move.");
        return;
    }
    zwlr_virtual_pointer_v1_motion_absolute(state->vpointer, now_ms(), x, y, state->extent_w,
                                            state->extent_h);
    zwlr_virtual_pointer_v1_frame(state->vpointer);
    do_roundtrip(&state->base);
    test_ok();
}

static void cmd_button(struct test_state *state, const char *arg, uint32_t button_state) {
    if (arg == NULL) {
        test_error("button commands require an evdev button code.");
        return;
    }
    char *end = NULL;
    unsigned long code = strtoul(arg, &end, 0); // accepts 273 or 0x111
    if (end == arg || *end != '\0') {
        test_error("invalid button code: %s", arg);
        return;
    }
    zwlr_virtual_pointer_v1_button(state->vpointer, now_ms(), (uint32_t)code, button_state);
    zwlr_virtual_pointer_v1_frame(state->vpointer);
    do_roundtrip(&state->base);
    test_ok();
}

static bool dispatch_command(struct client_state *base, const char *cmd, const char *arg) {
    struct test_state *state = (struct test_state *)base;

    if (strcmp(cmd, "quit") == 0) {
        return false;
    }

    if (state->vpointer == NULL) {
        test_error("no virtual pointer.");
        return true;
    }

    if (strcmp(cmd, "extent") == 0) {
        cmd_extent(state, arg);
    } else if (strcmp(cmd, "move") == 0) {
        cmd_move(state, arg);
    } else if (strcmp(cmd, "button_press") == 0) {
        cmd_button(state, arg, WL_POINTER_BUTTON_STATE_PRESSED);
    } else if (strcmp(cmd, "button_release") == 0) {
        cmd_button(state, arg, WL_POINTER_BUTTON_STATE_RELEASED);
    } else {
        test_error("unknown command: %s", cmd);
    }
    return true;
}

static void cleanup(struct client_state *base) {
    struct test_state *state = (struct test_state *)base;

    if (state->vpointer) {
        zwlr_virtual_pointer_v1_destroy(state->vpointer);
    }
    if (state->vpointer_mgr) {
        zwlr_virtual_pointer_manager_v1_destroy(state->vpointer_mgr);
    }
}

int main(void) {
    struct test_state state = {0};

    const struct client_ops ops = {.registry_global = registry_handler,
                                   .dispatch_command = dispatch_command,
                                   .cleanup = cleanup};

    return client_run(&state.base, &ops);
}
