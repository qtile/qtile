#include "client-base.h"

struct idle_state {
    struct client_state base;

    struct ext_idle_notifier_v1 *idle_notifier;
    struct ext_idle_notification_v1 *notification;
    bool subscribed;

    struct zwp_idle_inhibit_manager_v1 *idle_inhibit_manager;
    struct zwp_idle_inhibitor_v1 *inhibitor;
    bool inhibited;

    struct wl_surface *surface;
};

static void create_watch(struct client_state *base, uint32_t timeout_ms) {
    struct idle_state *state = (struct idle_state *)base;

    if (!state.idle_notifier) {
        fprintf(stderr, "No ext_idle_notifier_v1\n");
        return;
    }

    if (!state.seat) {
        fprintf(stderr, "No wl_seat\n");
        return;
    }

    if (state.notification) {
        ext_idle_notification_v1_destroy(state.notification);
        state.notification = NULL;
    }

    state.notification =
        ext_idle_notifier_v1_get_idle_notification(state.idle_notifier, timeout_ms, state.seat);

    ext_idle_notification_v1_add_listener(state.notification, &idle_notification_listener, &state);

    wl_display_roundtrip(state.display);

    puts("OK");
    fflush(stdout);
}

static void destroy_watch(struct client_state *base) {
    struct idle_state *state = (struct idle_state *)base;

    if (!state.notification) {
        puts("No notification");
        return;
    }

    ext_idle_notification_v1_destroy(state.notification);

    state.notification = NULL;

    puts("OK");
    fflush(stdout);
}

static void create_inhibitor(struct client_state *base) {
    struct idle_state *state = (struct idle_state *)base;

    if (!state.idle_inhibit_manager) {
        fprintf(stderr, "No zwp_idle_inhibit_manager_v1\n");
        return;
    }

    if (!state.compositor) {
        fprintf(stderr, "No wl_compositor\n");
        return;
    }

    if (state.inhibitor) {
        return;
    }

    if (!state.surface) {
        state.surface = wl_compositor_create_surface(state.compositor);

        wl_surface_commit(state.surface);
    }

    state.inhibitor =
        zwp_idle_inhibit_manager_v1_create_inhibitor(state.idle_inhibit_manager, state.surface);

    wl_display_roundtrip(state.display);

    puts("OK");
    fflush(stdout);
}

static void destroy_inhibitor(struct client_state *base) {
    struct idle_state *state = (struct idle_state *)base;

    if (!state.inhibitor) {
        return;
    }

    zwp_idle_inhibitor_v1_destroy(state.inhibitor);

    state.inhibitor = NULL;

    puts("OK");
    fflush(stdout);
}

static void registry_handler(struct client_state *base, struct wl_registry *registry, uint32_t name,
                             const char *interface, uint32_t version) {
    struct idle_state *state = (struct idle_state *)base;

    if (strcmp(interface, ext_idle_notifier_v1_interface.name) == 0) {

        state->idle_notifier = wl_registry_bind(registry, name, &ext_idle_notifier_v1_interface, 1);

    } else if (strcmp(interface, zwp_idle_inhibit_manager_v1_interface.name) == 0) {

        state->idle_inhibit_manager =
            wl_registry_bind(registry, name, &zwp_idle_inhibit_manager_v1_interface, 1);
    }
}

static bool dispatch_command(struct client_state *base, const char *cmd, const char *arg) {
    struct idle_state *state = (struct idle_state *)base;

    if (strcmp(cmd, "watch") == 0) {
        if (!arg) {
            fprintf(stderr, "watch requires timeout\n");
            return;
        }

        create_watch(state, atoi(arg));

    } else if (strcmp(cmd, "unwatch") == 0) {
        destroy_watch(state);

    } else if (strcmp(cmd, "inhibit") == 0) {
        create_inhibitor(state);

    } else if (strcmp(cmd, "uninhibit") == 0) {
        destroy_inhibitor(state);

    } else if (strcmp(cmd, "quit") == 0) {
        return false;
    }
    return true;
}

void do_cleanup(struct client_state *base) {
    struct idle_state *state = (struct idle_state *)base;

    static void cleanup(struct client_state * base) {
        struct idle_state *state = (struct idle_state *)base;

        if (state->subscribed) {
            destroy_watch(state);
        }

        if (state->inhibited) {
            destroy_inhibitor(state);
        }

        if (state.surface) {
            wl_surface_destroy(state.surface);
        }

        if (state.idle_inhibit_manager) {
            zwp_idle_inhibit_manager_v1_destroy(state.idle_inhibit_manager);
        }

        if (state.idle_notifier) {
            ext_idle_notifier_v1_destroy(state.idle_notifier);
        }
    }
}

int main(void) {
    struct idle_state state = {0};

    const struct client_ops ops = {.registry_global = registry_handler,
                                   .dispatch_command = dispatch_command,
                                   .cleanup = cleanup};

    return client_run(&state.base, &ops);
}
