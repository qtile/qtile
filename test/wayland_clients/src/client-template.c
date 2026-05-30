/*
This file shows a skeleton for building clients to test client interaction
with the qtile wayland compositor.

In addition to creating a new test client, you must add the necessary information
to build.py to build the client. This includes building the necessary client protocol
files and the client itself.

Example:

PROTOS: list[Protocol] = [
    ...,
    Protocol(
        f"{WAYLAND_PROTOCOLS}/staging/ext-idle-notify/ext-idle-notify-v1.xml",
        build_client=True,
        build_server=False,
    ),
    Protocol(
        f"{WAYLAND_PROTOCOLS}/unstable/idle-inhibit/idle-inhibit-unstable-v1.xml",
        build_client=True,
        build_server=False,
    ),
]

TEST_CLIENTS: list[TestClient] = [
    TestClient(
        name="idle-client",
        sources=[
            TEST_CLIENT_SRC_PATH / "idle-client.c",
            CLIENT_BASE,
            QW_PROTO_OUT_PATH / "ext-idle-notify-v1-protocol.c",
            QW_PROTO_OUT_PATH / "idle-inhibit-unstable-v1-protocol.c",
        ],
        includes=[QW_PROTO_OUT_PATH, TEST_CLIENT_SRC_PATH],
    )
]

In the TestClient sources, CLIENT_BASE is the path to 'client-base.c'. This must be included if your
client is based off this template.

The pytest fixture for the client expects successful commands to print "OK" to stdout (use
'test_ok') or "ERROR: <error message>" (use 'test_error').
*/

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "client-base.h"

/*
Add required extension includes
*/

struct test_state {
    struct client_state base;

    /*
    Custom state properties for test

    for example:
    struct ext_idle_notifier_v1 *idle_notifier;
    struct ext_idle_notification_v1 *notification;
    */
};

/*
Binding registry globals specific to the test client. The display, compositor etc. are bound before
this function is called.
*/
static void registry_handler(struct client_state *base, struct wl_registry *registry, uint32_t name,
                             const char *interface, uint32_t version) {
    struct test_state *state = (struct test_state *)base;

    /*
    if (strcmp(interface, ext_idle_notifier_v1_interface.name) == 0) {
        state->idle_notifier = wl_registry_bind(registry, name, &ext_idle_notifier_v1_interface, 1);

    } else if (strcmp(interface, zwp_idle_inhibit_manager_v1_interface.name) == 0) {
        state->idle_inhibit_manager =
        wl_registry_bind(registry, name, &zwp_idle_inhibit_manager_v1_interface, 1);
    }
    */
}

/*
Function to handle removal of global items. Only necessary if this benhaviour is expected or
being tested.
*/
static void registry_global_remove(void *data, struct wl_registry *registry, uint32_t name) {
    struct client_state *state = data;
    (void)registry;
    (void)name;
}

/*
Function for parsing commands received via stdin. Function receives the command name
(first word of stdin) and an arg (anything after the command name).

Function should return true to remain in the main loop, returning false will cause the script
to exit.
*/
static bool dispatch_command(struct client_state *base, const char *cmd, const char *arg) {
    struct test_state *state = (struct test_state *)base;

    /*
    if (strcmp(cmd, "quit") == 0) {
        return false;
    }
    */
    return true;
}

/*
Called just before the main loop starts.

Function to handle initalising any variables (e.g. lists). The global registry binding has not
happened at this stage.
*/
void setup(struct client_state *base) { struct test_state *state = (struct test_state *)base; }

/*
Called when the main loop exits.

Function to handle tidying up of any items. Display, compositor etc.
will be destroyed after this function.
*/
void cleanup(struct client_state *base) { struct test_state *state = (struct test_state *)base; }

/*
main function MUST initialise state and bind cliet operations.

"client_run" will start the loop, listening to STDIN as well as the
wayland socket.
*/
int main(void) {
    struct test_state state = {0};

    const struct client_ops ops = {.setup = setup,
                                   .registry_global = registry_handler,
                                   .registry_global_remove = registry_global_remove,
                                   .dispatch_command = dispatch_command,
                                   .cleanup = cleanup};

    return client_run(&state.base, &ops);
}
