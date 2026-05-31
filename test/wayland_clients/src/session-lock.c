#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "client-base.h"

#include "ext-session-lock-v1-client-protocol.h"

struct test_state {
    struct client_state base;

    struct ext_session_lock_manager_v1 *lock_manager;

    struct wl_list outputs;  // output_entry
    struct wl_list surfaces; // surface_entry

    struct ext_session_lock_v1 *lock;
    bool got_locked;
    bool lock_finished;

    bool do_crash;
};

struct output_entry {
    struct wl_output *wl_output;
    int32_t x, y, width, height; /* logical geometry */
    struct wl_list link;
};

struct surface_entry {
    struct ext_session_lock_surface_v1 *lock_surface;
    struct wl_surface *wl_surface;
    struct output_entry *output;
    struct buffer *buffer;
    uint32_t width;
    uint32_t height;
    bool configured;
    struct wl_list link;
    struct test_state *state;
};

static void surface_configure(void *data, struct ext_session_lock_surface_v1 *lock_surface,
                              uint32_t serial, uint32_t width, uint32_t height) {
    struct surface_entry *se = data;

    se->configured = true;
    se->width = width;
    se->height = height;

    ext_session_lock_surface_v1_ack_configure(lock_surface, serial);

    if (se->buffer == NULL) {
        se->buffer = create_buffer(&se->state->base, width, height, 0xFF606060);

        if (se->buffer == NULL) {
            fprintf(stderr, "failed to create buffer\n");
            return;
        }
    }

    wl_surface_attach(se->wl_surface, se->buffer->wl_buffer, 0, 0);
    wl_surface_damage_buffer(se->wl_surface, 0, 0, INT32_MAX, INT32_MAX);
    wl_surface_commit(se->wl_surface);
}

static const struct ext_session_lock_surface_v1_listener surface_listener = {
    .configure = surface_configure,
};

static void lock_locked(void *data, struct ext_session_lock_v1 *lock) {
    (void)lock;
    struct test_state *state = data;
    state->got_locked = true;
}

static void lock_finished(void *data, struct ext_session_lock_v1 *lock) {
    /*
     * "finished" is sent when:
     *   (a) the compositor rejects the lock (already locked / crashed), or
     *   (b) another compositor-side event invalidates this lock.
     * In either case the client MUST destroy the lock object.
     */
    struct test_state *state = data;
    state->lock_finished = true;
    ext_session_lock_v1_destroy(lock);
    state->lock = NULL;
}

static const struct ext_session_lock_v1_listener lock_listener = {
    .locked = lock_locked,
    .finished = lock_finished,
};

static void output_geometry(void *data, struct wl_output *wl_output, int32_t x, int32_t y,
                            int32_t physical_width, int32_t physical_height, int32_t subpixel,
                            const char *make, const char *model, int32_t transform) {
    struct output_entry *oe = data;
    oe->x = x;
    oe->y = y;
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

static void registry_handler(struct client_state *base, struct wl_registry *registry, uint32_t name,
                             const char *interface, uint32_t version) {
    struct test_state *state = (struct test_state *)base;

    if (strcmp(interface, ext_session_lock_manager_v1_interface.name) == 0) {
        state->lock_manager =
            wl_registry_bind(registry, name, &ext_session_lock_manager_v1_interface, 1);

    } else if (strcmp(interface, wl_output_interface.name) == 0) {
        struct output_entry *oe = calloc(1, sizeof(*oe));
        oe->wl_output = wl_registry_bind(registry, name, &wl_output_interface, 4);
        wl_output_add_listener(oe->wl_output, &output_listener, oe);
        wl_list_insert(&state->outputs, &oe->link);
    }
}

static void cmd_lock(struct test_state *state) {
    if (state->lock_manager == NULL) {
        test_error("ext_session_lock_manager_v1 not advertised by compositor");
        return;
    }
    if (state->lock != NULL) {
        test_error("already holding a lock object");
        return;
    }

    state->got_locked = false;
    state->lock_finished = false;

    state->lock = ext_session_lock_manager_v1_lock(state->lock_manager);
    ext_session_lock_v1_add_listener(state->lock, &lock_listener, state);

    /* Give the compositor a chance to reply */
    do_roundtrip(&state->base);

    if (state->got_locked) {
        test_ok();
    } else if (state->lock_finished) {
        test_error("compositor rejected lock");
    } else {
        test_error("neither locked nor finished received after roundtrip");
    }
}

static void cmd_unlock(struct test_state *state) {
    if (state->lock == NULL) {
        test_error("no active lock");
        return;
    }
    if (!state->got_locked) {
        test_error("lock was never confirmed (no locked event)");
        return;
    }

    ext_session_lock_v1_unlock_and_destroy(state->lock);
    state->lock = NULL;
    state->got_locked = false;

    do_roundtrip(&state->base);
    test_ok();
}

static void cmd_create_surface(struct test_state *state) {
    if (state->lock == NULL || !state->got_locked) {
        test_error("not locked");
        return;
    }
    if (state->base.compositor == NULL) {
        test_error("wl_compositor not available");
        return;
    }

    int created = 0;
    struct output_entry *oe;
    wl_list_for_each(oe, &state->outputs, link) {
        struct surface_entry *se = calloc(1, sizeof(*se));
        se->state = state;
        se->output = oe;
        se->wl_surface = wl_compositor_create_surface(state->base.compositor);

        se->lock_surface =
            ext_session_lock_v1_get_lock_surface(state->lock, se->wl_surface, oe->wl_output);
        ext_session_lock_surface_v1_add_listener(se->lock_surface, &surface_listener, se);

        wl_list_insert(&state->surfaces, &se->link);
        created++;
    }

    if (created == 0) {
        test_error("no outputs found");
        return;
    }

    /* Roundtrip: compositor should send configure events */
    do_roundtrip(&state->base);

    /* Check all surfaces received configure */
    bool all_configured = true;
    struct surface_entry *se;
    wl_list_for_each(se, &state->surfaces, link) {
        if (!se->configured) {
            all_configured = false;
            break;
        }
    }

    if (all_configured) {
        test_ok();
    } else {
        test_error("one or more lock surfaces did not receive configure event");
    }
}

static void cmd_destroy_surface(struct test_state *state) {
    if (wl_list_empty(&state->surfaces)) {
        test_error("no surfaces to destroy");
        return;
    }

    struct surface_entry *se, *tmp;
    wl_list_for_each_safe(se, tmp, &state->surfaces, link) {
        ext_session_lock_surface_v1_destroy(se->lock_surface);
        wl_surface_destroy(se->wl_surface);
        wl_list_remove(&se->link);
        free(se);
    }

    do_roundtrip(&state->base);
    test_ok();
}

/*
 * check_locked
 * Verify we have received the "locked" event (synchronous check).
 */
static void cmd_check_locked(struct test_state *state) {
    do_roundtrip(&state->base);
    if (state->lock != NULL && state->got_locked) {
        test_ok();
    } else {
        test_error("not in locked state");
    }
}

static void cmd_check_unlocked(struct test_state *state) {
    do_roundtrip(&state->base);
    if (state->lock == NULL && !state->got_locked) {
        test_ok();
    } else {
        test_error("still in locked state");
    }
}

static void cmd_check_surface_count(struct test_state *state, const char *arg) {
    if (arg == NULL) {
        test_error("usage: check_surface_count <N>");
        return;
    }
    int expected = atoi(arg);
    int actual = 0;
    struct surface_entry *se;
    wl_list_for_each(se, &state->surfaces, link) { actual++; }
    if (actual == expected) {
        test_ok();
    } else {
        printf("ERROR: expected %d surfaces, got %d\n", expected, actual);
    }
}

static bool dispatch_command(struct client_state *base, const char *cmd, const char *arg) {
    struct test_state *state = (struct test_state *)base;

    if (strcmp(cmd, "lock") == 0)
        cmd_lock(state);
    else if (strcmp(cmd, "unlock") == 0)
        cmd_unlock(state);
    else if (strcmp(cmd, "create_surface") == 0)
        cmd_create_surface(state);
    else if (strcmp(cmd, "destroy_surface") == 0)
        cmd_destroy_surface(state);
    else if (strcmp(cmd, "check_locked") == 0)
        cmd_check_locked(state);
    else if (strcmp(cmd, "check_unlocked") == 0)
        cmd_check_unlocked(state);
    else if (strcmp(cmd, "check_surface_count") == 0)
        cmd_check_surface_count(state, arg);
    else if (strcmp(cmd, "crash") == 0) {
        state->do_crash = true;
        test_ok();
        return false;
    } else if (strcmp(cmd, "quit") == 0) {
        test_ok();
        return false;
    }
    return true;
}

void cleanup(struct client_state *base) {
    struct test_state *state = (struct test_state *)base;

    if (!state->do_crash) {
        struct surface_entry *se, *stmp;
        wl_list_for_each_safe(se, stmp, &state->surfaces, link) {
            ext_session_lock_surface_v1_destroy(se->lock_surface);
            wl_surface_destroy(se->wl_surface);
            free(se);
        }
        if (state->lock) {
            ext_session_lock_v1_destroy(state->lock);
        }
    }
}

void setup(struct client_state *base) {
    struct test_state *state = (struct test_state *)base;

    wl_list_init(&state->outputs);
    wl_list_init(&state->surfaces);
}

int main(void) {
    struct test_state state = {0};

    const struct client_ops ops = {.setup = setup,
                                   .registry_global = registry_handler,
                                   .dispatch_command = dispatch_command,
                                   .cleanup = cleanup};

    return client_run(&state.base, &ops);
}
