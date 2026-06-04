#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "client-base.h"

#include "wlr-foreign-toplevel-management-unstable-v1-client-protocol.h"

struct test_state {
    struct client_state base;

    struct zwlr_foreign_toplevel_manager_v1 *ftl_manager;

    struct wl_list toplevels; // toplevel_entry
    struct wl_list outputs;   // output_entry

    bool pending_close;
};

enum {
    STATE_MAXIMIZED = 1 << 0,
    STATE_MINIMIZED = 1 << 1,
    STATE_ACTIVATED = 1 << 2,
    STATE_FULLSCREEN = 1 << 3,
};

enum {
    OUTPUT_RESET,
    OUTPUT_ENTER,
    OUTPUT_LEAVE,
};

struct output_entry {
    struct wl_output *wl_output;
    char *name;
    struct wl_list link;
};

struct toplevel_entry {
    struct test_state *test_state;
    struct zwlr_foreign_toplevel_handle_v1 *ftl_handle;
    char *title;
    char *app_id;
    uint32_t toplevel_state;
    struct wl_list link;
    char *output_enter;
    char *output_leave;
};

static char *find_output_name(struct test_state *state, struct wl_output *wl_output) {
    struct output_entry *oe;
    wl_list_for_each(oe, &state->outputs, link) {
        if (oe->wl_output == wl_output) {
            return oe->name;
        }
    }
    return NULL;
}

static void toplevel_title(void *data,
                           struct zwlr_foreign_toplevel_handle_v1 *zwlr_foreign_toplevel_handle_v1,
                           const char *title) {
    (void)zwlr_foreign_toplevel_handle_v1;
    struct toplevel_entry *te = data;
    free(te->title);
    te->title = strdup(title);
}

static void toplevel_app_id(void *data,
                            struct zwlr_foreign_toplevel_handle_v1 *zwlr_foreign_toplevel_handle_v1,
                            const char *app_id) {
    (void)zwlr_foreign_toplevel_handle_v1;
    struct toplevel_entry *te = data;
    free(te->app_id);
    te->app_id = strdup(app_id);
}

static void
toplevel_output_enter(void *data,
                      struct zwlr_foreign_toplevel_handle_v1 *zwlr_foreign_toplevel_handle_v1,
                      struct wl_output *wl_output) {
    (void)zwlr_foreign_toplevel_handle_v1;
    struct toplevel_entry *te = data;
    free(te->output_enter);
    te->output_enter = strdup(find_output_name(te->test_state, wl_output));
}

static void
toplevel_output_leave(void *data,
                      struct zwlr_foreign_toplevel_handle_v1 *zwlr_foreign_toplevel_handle_v1,
                      struct wl_output *wl_output) {
    (void)zwlr_foreign_toplevel_handle_v1;
    struct toplevel_entry *te = data;
    free(te->output_leave);
    te->output_leave = strdup(find_output_name(te->test_state, wl_output));
}

static void toplevel_state(void *data,
                           struct zwlr_foreign_toplevel_handle_v1 *zwlr_foreign_toplevel_handle_v1,
                           struct wl_array *state) {
    struct toplevel_entry *te = data;
    uint32_t flags = 0;
    uint32_t *s;

    wl_array_for_each(s, state) {
        switch (*s) {
        case ZWLR_FOREIGN_TOPLEVEL_HANDLE_V1_STATE_MAXIMIZED:
            flags |= STATE_MAXIMIZED;
            break;
        case ZWLR_FOREIGN_TOPLEVEL_HANDLE_V1_STATE_MINIMIZED:
            flags |= STATE_MINIMIZED;
            break;
        case ZWLR_FOREIGN_TOPLEVEL_HANDLE_V1_STATE_ACTIVATED:
            flags |= STATE_ACTIVATED;
            break;
        case ZWLR_FOREIGN_TOPLEVEL_HANDLE_V1_STATE_FULLSCREEN:
            flags |= STATE_FULLSCREEN;
            break;
        }
    }
    te->toplevel_state = flags;
}

static void toplevel_done(void *data,
                          struct zwlr_foreign_toplevel_handle_v1 *zwlr_foreign_toplevel_handle_v1) {
    (void)data;
    (void)zwlr_foreign_toplevel_handle_v1;
}

static void
toplevel_closed(void *data,
                struct zwlr_foreign_toplevel_handle_v1 *zwlr_foreign_toplevel_handle_v1) {
    struct toplevel_entry *te = data;
    zwlr_foreign_toplevel_handle_v1_destroy(zwlr_foreign_toplevel_handle_v1);

    wl_list_remove(&te->link);
    te->test_state->pending_close = false;
    free(te);
}

static void toplevel_parent(void *data,
                            struct zwlr_foreign_toplevel_handle_v1 *zwlr_foreign_toplevel_handle_v1,
                            struct zwlr_foreign_toplevel_handle_v1 *parent) {
    (void)data;
    (void)zwlr_foreign_toplevel_handle_v1;
    (void)parent;
}

static const struct zwlr_foreign_toplevel_handle_v1_listener toplevel_listener = {
    .title = toplevel_title,
    .app_id = toplevel_app_id,
    .output_enter = toplevel_output_enter,
    .output_leave = toplevel_output_leave,
    .state = toplevel_state,
    .done = toplevel_done,
    .closed = toplevel_closed,
    .parent = toplevel_parent,
};

static void
ftl_finished(void *data,
             struct zwlr_foreign_toplevel_manager_v1 *zwlr_foreign_toplevel_manager_v1) {
    (void)data;
    (void)zwlr_foreign_toplevel_manager_v1;
}

static void ftl_toplevel(void *data,
                         struct zwlr_foreign_toplevel_manager_v1 *zwlr_foreign_toplevel_manager_v1,
                         struct zwlr_foreign_toplevel_handle_v1 *toplevel) {

    (void)zwlr_foreign_toplevel_manager_v1;
    struct test_state *state = data;
    struct toplevel_entry *te = calloc(1, sizeof(*te));
    te->ftl_handle = toplevel;
    te->test_state = state;
    zwlr_foreign_toplevel_handle_v1_add_listener(te->ftl_handle, &toplevel_listener, te);
    wl_list_insert(&state->toplevels, &te->link);
}

static const struct zwlr_foreign_toplevel_manager_v1_listener ftl_listener = {
    .toplevel = ftl_toplevel,
    .finished = ftl_finished,
};

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

    if (strcmp(interface, zwlr_foreign_toplevel_manager_v1_interface.name) == 0) {
        state->ftl_manager =
            wl_registry_bind(registry, name, &zwlr_foreign_toplevel_manager_v1_interface, 3);
        zwlr_foreign_toplevel_manager_v1_add_listener(state->ftl_manager, &ftl_listener, state);
    } else if (strcmp(interface, wl_output_interface.name) == 0) {
        // wlroots only sends output_enter/leave events if the outputs are also bound by the client
        struct output_entry *oe = calloc(1, sizeof(*oe));
        oe->wl_output = wl_registry_bind(registry, name, &wl_output_interface, 4);
        oe->name = NULL;
        wl_output_add_listener(oe->wl_output, &output_listener, oe);
        wl_list_insert(&state->outputs, &oe->link);
    }
}

char *format_state(uint32_t toplevel_state, uint32_t reference) {
    if (toplevel_state & reference) {
        return "Y";
    }
    return "N";
}

/*
List toplevel view "title (app_id) state:"
*/
static void cmd_list_toplevels(struct test_state *state) {
    struct toplevel_entry *te;
    wl_list_for_each(te, &state->toplevels, link) {
        test_message("title:%s app_id:%s activated:%s fullscreen:%s maximized:%s minimized:%s",
                     te->title, te->app_id, format_state(te->toplevel_state, STATE_ACTIVATED),
                     format_state(te->toplevel_state, STATE_FULLSCREEN),
                     format_state(te->toplevel_state, STATE_MAXIMIZED),
                     format_state(te->toplevel_state, STATE_MINIMIZED));
    }
    test_ok();
}

/*
Close toplevel window and verify close message received from server.
*/
static void cmd_close(struct test_state *state, const char *title) {
    test_message("close requested");
    struct toplevel_entry *te;
    bool found = false;
    wl_list_for_each(te, &state->toplevels, link) {
        if (strcmp(te->title, title) == 0) {
            zwlr_foreign_toplevel_handle_v1_close(te->ftl_handle);
            found = true;
            break;
        }
    }

    if (!found) {
        test_error("toplevel not found");
        return;
    }

    do_roundtrip(&state->base);
    if (state->pending_close) {
        test_error("close message not received");
    } else {
        test_ok();
    }
}

static void cmd_check_state(struct test_state *state, const char *title, uint32_t toplevel_state) {
    struct toplevel_entry *te;
    wl_list_for_each(te, &state->toplevels, link) {
        if (strcmp(te->title, title) == 0) {
            if (te->toplevel_state & toplevel_state) {
                test_ok();
            } else {
                test_error("state does not match");
            }
            return;
        }
    }
    test_error("toplevel not found");
}

static void cmd_toggle_state(struct test_state *state, const char *title, uint32_t toplevel_state) {
    struct toplevel_entry *te;
    bool found = false;
    bool expected;
    wl_list_for_each(te, &state->toplevels, link) {
        if (strcmp(te->title, title) == 0) {
            expected = !(te->toplevel_state & toplevel_state);
            if (toplevel_state & STATE_FULLSCREEN) {
                if (te->toplevel_state & STATE_FULLSCREEN) {
                    zwlr_foreign_toplevel_handle_v1_unset_fullscreen(te->ftl_handle);
                } else {
                    zwlr_foreign_toplevel_handle_v1_set_fullscreen(te->ftl_handle, NULL);
                }
            } else if (toplevel_state & STATE_MAXIMIZED) {
                if (te->toplevel_state & STATE_MAXIMIZED) {
                    zwlr_foreign_toplevel_handle_v1_unset_maximized(te->ftl_handle);
                } else {
                    zwlr_foreign_toplevel_handle_v1_set_maximized(te->ftl_handle);
                }
            } else if (toplevel_state & STATE_MINIMIZED) {
                if (te->toplevel_state & STATE_MINIMIZED) {
                    zwlr_foreign_toplevel_handle_v1_unset_minimized(te->ftl_handle);
                } else {
                    zwlr_foreign_toplevel_handle_v1_set_minimized(te->ftl_handle);
                }

            } else if (toplevel_state & STATE_ACTIVATED) {
                if (!(te->toplevel_state & STATE_ACTIVATED)) {
                    zwlr_foreign_toplevel_handle_v1_activate(te->ftl_handle, state->base.seat);
                }
            }
            break;
        }
    }

    do_roundtrip(&state->base);
    bool actual = te->toplevel_state & toplevel_state;
    if (actual == expected) {
        test_ok();
    } else {
        test_error("state not changed");
    }
}

static void cmd_output(struct test_state *state, const char *title, int output_mode) {
    struct toplevel_entry *te;
    bool expected;
    wl_list_for_each(te, &state->toplevels, link) {
        if (strcmp(te->title, title) == 0) {
            if (output_mode == OUTPUT_RESET) {
                free(te->output_enter);
                free(te->output_leave);
                te->output_enter = NULL;
                te->output_leave = NULL;
                test_ok();
            } else if (output_mode == OUTPUT_ENTER) {
                if (te->output_enter) {
                    test_message("output_enter: %s", te->output_enter);
                    test_ok();
                } else {
                    test_error("output_enter message not received");
                }
            } else if (output_mode == OUTPUT_LEAVE) {
                if (te->output_leave) {
                    test_message("output_leave: %s", te->output_leave);
                    test_ok();
                } else {
                    test_error("output_leave message not received");
                }
            }
            return;
        }
    }
    test_error("toplevel not found");
}

static bool dispatch_command(struct client_state *base, const char *cmd, const char *arg) {
    struct test_state *state = (struct test_state *)base;

    if (strcmp(cmd, "list") == 0)
        cmd_list_toplevels(state);
    else if (strcmp(cmd, "close") == 0)
        cmd_close(state, arg);
    else if (strcmp(cmd, "check_activated") == 0)
        cmd_check_state(state, arg, STATE_ACTIVATED);
    else if (strcmp(cmd, "check_maximized") == 0)
        cmd_check_state(state, arg, STATE_MAXIMIZED);
    else if (strcmp(cmd, "check_maximized") == 0)
        cmd_check_state(state, arg, STATE_MINIMIZED);
    else if (strcmp(cmd, "check_fullscreen") == 0)
        cmd_check_state(state, arg, STATE_FULLSCREEN);
    else if (strcmp(cmd, "fullscreen") == 0)
        cmd_toggle_state(state, arg, STATE_FULLSCREEN);
    else if (strcmp(cmd, "maximize") == 0)
        cmd_toggle_state(state, arg, STATE_MAXIMIZED);
    else if (strcmp(cmd, "minimize") == 0)
        cmd_toggle_state(state, arg, STATE_MINIMIZED);
    else if (strcmp(cmd, "activate") == 0)
        cmd_toggle_state(state, arg, STATE_ACTIVATED);
    else if (strcmp(cmd, "output_reset") == 0)
        cmd_output(state, arg, OUTPUT_RESET);
    else if (strcmp(cmd, "output_enter") == 0)
        cmd_output(state, arg, OUTPUT_ENTER);
    else if (strcmp(cmd, "output_leave") == 0)
        cmd_output(state, arg, OUTPUT_LEAVE);
    else if (strcmp(cmd, "quit") == 0) {
        test_ok();
        return false;
    }
    return true;
}

void cleanup(struct client_state *base) { struct test_state *state = (struct test_state *)base; }

void setup(struct client_state *base) {
    struct test_state *state = (struct test_state *)base;

    wl_list_init(&state->toplevels);
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
