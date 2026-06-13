#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "client-base.h"

#include "ext-idle-notify-v1-client-protocol.h"
#include "idle-inhibit-unstable-v1-client-protocol.h"

struct test_state {
    struct client_state base;

    struct ext_idle_notifier_v1 *idle_notifier;
    struct ext_idle_notification_v1 *notification;
    bool subscribed;

    struct zwp_idle_inhibit_manager_v1 *idle_inhibit_manager;
    struct zwp_idle_inhibitor_v1 *inhibitor;
    bool inhibited;

    struct wl_surface *surface;
};

static void handle_idled(void *data, struct ext_idle_notification_v1 *notification) {
    (void)data;
    (void)notification;

    test_message("idled");
}

static void handle_resumed(void *data, struct ext_idle_notification_v1 *notification) {
    (void)data;
    (void)notification;

    test_message("resumed");
}

static const struct ext_idle_notification_v1_listener idle_notification_listener = {
    .idled = handle_idled,
    .resumed = handle_resumed,
};

static void create_watch(struct test_state *state, uint32_t timeout_ms) {

    if (!state->idle_notifier) {
        fprintf(stderr, "No ext_idle_notifier_v1\n");
        return;
    }

    if (!state->base.seat) {
        fprintf(stderr, "No wl_seat\n");
        return;
    }

    if (state->notification) {
        ext_idle_notification_v1_destroy(state->notification);
        state->notification = NULL;
    }

    state->notification = ext_idle_notifier_v1_get_idle_notification(state->idle_notifier,
                                                                     timeout_ms, state->base.seat);

    ext_idle_notification_v1_add_listener(state->notification, &idle_notification_listener, state);
    state->subscribed = true;

    wl_display_roundtrip(state->base.display);

    test_ok();
}

static void destroy_watch(struct test_state *state) {

    if (!state->notification) {
        test_message("No notification");
        return;
    }

    ext_idle_notification_v1_destroy(state->notification);

    state->notification = NULL;
    state->subscribed = false;

    test_ok();
}

static void create_inhibitor(struct test_state *state) {

    if (!state->base.compositor) {
        fprintf(stderr, "No wl_compositor\n");
        return;
    }

    if (!state->idle_inhibit_manager) {
        test_error("No zwp_idle_inhibit_manager_v1.");
        return;
    }

    if (state->inhibitor) {
        return;
    }

    if (!state->surface) {
        state->surface = wl_compositor_create_surface(state->base.compositor);
        wl_surface_commit(state->surface);
    }

    state->inhibitor =
        zwp_idle_inhibit_manager_v1_create_inhibitor(state->idle_inhibit_manager, state->surface);

    state->inhibited = true;

    wl_display_roundtrip(state->base.display);

    test_ok();
}

static void destroy_inhibitor(struct test_state *state) {

    if (!state->inhibitor) {
        return;
    }

    zwp_idle_inhibitor_v1_destroy(state->inhibitor);

    state->inhibitor = NULL;
    state->inhibited = false;

    test_ok();
}

static void registry_handler(struct client_state *base, struct wl_registry *registry, uint32_t name,
                             const char *interface, uint32_t version) {
    struct test_state *state = (struct test_state *)base;

    if (strcmp(interface, ext_idle_notifier_v1_interface.name) == 0) {

        state->idle_notifier = wl_registry_bind(registry, name, &ext_idle_notifier_v1_interface, 1);

    } else if (strcmp(interface, zwp_idle_inhibit_manager_v1_interface.name) == 0) {

        state->idle_inhibit_manager =
            wl_registry_bind(registry, name, &zwp_idle_inhibit_manager_v1_interface, 1);
    }
}

static bool dispatch_command(struct client_state *base, const char *cmd, const char *arg) {
    struct test_state *state = (struct test_state *)base;

    if (strcmp(cmd, "watch") == 0) {
        if (!arg) {
            fprintf(stderr, "watch requires timeout\n");
            return true;
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

void cleanup(struct client_state *base) {
    struct test_state *state = (struct test_state *)base;

    if (state->subscribed) {
        destroy_watch(state);
    }

    if (state->inhibited) {
        destroy_inhibitor(state);
    }

    if (state->surface) {
        wl_surface_destroy(state->surface);
    }

    if (state->idle_inhibit_manager) {
        zwp_idle_inhibit_manager_v1_destroy(state->idle_inhibit_manager);
    }

    if (state->idle_notifier) {
        ext_idle_notifier_v1_destroy(state->idle_notifier);
    }
}

int main(void) {
    struct test_state state = {0};

    const struct client_ops ops = {.registry_global = registry_handler,
                                   .dispatch_command = dispatch_command,
                                   .cleanup = cleanup};

    return client_run(&state.base, &ops);
}
