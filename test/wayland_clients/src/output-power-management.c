#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "client-base.h"

#include "wlr-output-power-management-unstable-v1-client-protocol.h"

struct test_state {
    struct client_state base;

    struct zwlr_output_power_manager_v1 *power_manager;

    struct wl_list outputs; // output_entry
};

struct output_entry {
    struct wl_output *wl_output;
    struct zwlr_output_power_v1 *power;
    enum zwlr_output_power_v1_mode mode;
    char *name;
    bool failed;
    struct wl_list link;
};

static void handle_output_power_mode(void *data, struct zwlr_output_power_v1 *zwlr_output_power_v1,
                                     uint32_t mode) {
    (void)zwlr_output_power_v1;
    struct output_entry *oe = data;
    oe->mode = (enum zwlr_output_power_v1_mode)mode;
}

static void handle_output_power_failed(void *data,
                                       struct zwlr_output_power_v1 *zwlr_output_power_v1) {

    (void)zwlr_output_power_v1;
    struct output_entry *oe = data;
    oe->failed = true;
}

static const struct zwlr_output_power_v1_listener output_power_listener = {
    .mode = handle_output_power_mode, .failed = handle_output_power_failed};

static void output_geometry(void *data, struct wl_output *wl_output, int32_t x, int32_t y,
                            int32_t physical_width, int32_t physical_height, int32_t subpixel,
                            const char *make, const char *model, int32_t transform) {

    (void)data;
    (void)wl_output;
    (void)x;
    (void)y;
    (void)physical_width;
    (void)physical_height;
    (void)subpixel;
    (void)make;
    (void)model;
    (void)transform;
}

static void output_mode(void *data, struct wl_output *wl_output, uint32_t flags, int32_t width,
                        int32_t height, int32_t refresh) {

    (void)data;
    (void)wl_output;
    (void)flags;
    (void)width;
    (void)height;
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
    (void)wl_output;
    struct output_entry *oe = data;
    oe->name = strdup(name);
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

static void registry_handler(struct client_state *base, struct wl_registry *registry, uint32_t name,
                             const char *interface, uint32_t version) {
    struct test_state *state = (struct test_state *)base;

    if (strcmp(interface, zwlr_output_power_manager_v1_interface.name) == 0) {
        state->power_manager =
            wl_registry_bind(registry, name, &zwlr_output_power_manager_v1_interface, 1);

    } else if (strcmp(interface, wl_output_interface.name) == 0) {
        struct output_entry *oe = calloc(1, sizeof(*oe));
        oe->wl_output = wl_registry_bind(registry, name, &wl_output_interface, 4);
        oe->name = NULL;
        wl_output_add_listener(oe->wl_output, &output_listener, oe);
        oe->power =
            zwlr_output_power_manager_v1_get_output_power(state->power_manager, oe->wl_output);
        zwlr_output_power_v1_add_listener(oe->power, &output_power_listener, oe);
        wl_list_insert(&state->outputs, &oe->link);
    }
}

// Count number of outputs with given power state
static void cmd_count_power_mode(struct test_state *state, const char *arg,
                                 enum zwlr_output_power_v1_mode mode) {
    struct output_entry *oe;
    int target = atoi(arg);
    int count = 0;

    wl_list_for_each(oe, &state->outputs, link) {
        if (oe->mode == mode) {
            count++;
        }
    }
    if (target == count) {
        test_ok();
    } else {
        test_error("expected %d got %d", target, count);
    }
}

/*
Set power state. Can pass an output name to set individual output or
NULL to change all outputs.
*/
static void cmd_set_power(struct test_state *state, const char *name,
                          enum zwlr_output_power_v1_mode mode) {
    struct output_entry *oe;
    bool success = true;

    wl_list_for_each(oe, &state->outputs, link) {
        if (name == NULL || strcmp(name, oe->name) == 0) {
            if (oe->mode != mode) {
                zwlr_output_power_v1_set_mode(oe->power, mode);
                do_roundtrip(&state->base);
                if (oe->mode != mode) {
                    success = false;
                }
            }
        }
    }

    if (success) {
        test_ok();
    } else {
        test_error("could not set power mode");
    }
}

// Output name of outputs and power state
static void cmd_identify(struct test_state *state) {
    struct output_entry *oe;

    wl_list_for_each(oe, &state->outputs, link) {
        char *power = (oe->mode == ZWLR_OUTPUT_POWER_V1_MODE_ON) ? "ON" : "OFF";
        test_message("Output: %s (Power: %s)", oe->name, power);
    }

    test_ok();
}

// Verify number of outputs presented by compositor
static void cmd_outputs(struct test_state *state, const char *arg) {
    int target = atoi(arg);
    int count = 0;
    struct output_entry *oe;
    wl_list_for_each(oe, &state->outputs, link) { count++; }

    if (count == target) {
        test_ok();
    } else {
        test_error("expected %d got %d", target, count);
    }
}

static bool dispatch_command(struct client_state *base, const char *cmd, const char *arg) {
    struct test_state *state = (struct test_state *)base;

    if (strcmp(cmd, "count_on") == 0)
        cmd_count_power_mode(state, arg, ZWLR_OUTPUT_POWER_V1_MODE_ON);
    else if (strcmp(cmd, "count_off") == 0)
        cmd_count_power_mode(state, arg, ZWLR_OUTPUT_POWER_V1_MODE_OFF);
    else if (strcmp(cmd, "power_on") == 0)
        cmd_set_power(state, arg, ZWLR_OUTPUT_POWER_V1_MODE_ON);
    else if (strcmp(cmd, "power_off") == 0)
        cmd_set_power(state, arg, ZWLR_OUTPUT_POWER_V1_MODE_OFF);
    else if (strcmp(cmd, "identify") == 0)
        cmd_identify(state);
    else if (strcmp(cmd, "outputs") == 0)
        cmd_outputs(state, arg);
    else if (strcmp(cmd, "quit") == 0) {
        test_ok();
        return false;
    }
    return true;
}

void cleanup(struct client_state *base) { struct test_state *state = (struct test_state *)base; }

void setup(struct client_state *base) {
    struct test_state *state = (struct test_state *)base;

    wl_list_init(&state->outputs);
}

int main(void) {
    struct test_state state = {0};

    const struct client_ops ops = {.setup = setup,
                                   .registry_global = registry_handler,
                                   .dispatch_command = dispatch_command,
                                   .cleanup = cleanup};

    return client_run(&state.base, &ops);
}
