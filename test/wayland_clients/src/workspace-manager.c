#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "client-base.h"
#include "ext-workspace-v1-client-protocol.h"

struct test_state {
    struct client_state base;
    struct ext_workspace_manager_v1 *manager;
    struct wl_list groups;     // group_node::link
    struct wl_list workspaces; // workspace_node::global_link
};

struct group_node {
    struct ext_workspace_group_handle_v1 *handle;
    struct test_state *state;
    struct wl_list workspaces; // workspace_node::group_link
    struct wl_list link;
    uint32_t capabilities;
    uint8_t output_count;
};

struct workspace_node {
    struct ext_workspace_handle_v1 *handle;
    struct test_state *state;
    struct group_node *group;
    char *id;
    char *name;
    bool active;
    bool hidden;
    bool urgent;
    struct wl_list global_link;
    struct wl_list group_link;
    uint32_t capabilities;
};

enum { WORKSPACE_ACTION_ACTIVATE, WORKSPACE_ACTION_REMOVE, WORKSPACE_ACTION_CREATE };

static struct group_node *find_workspace_group_by_id(struct test_state *state, int index) {
    if (index < 0) {
        test_error("invalid index.");
        return NULL;
    }

    if (wl_list_empty(&state->groups)) {
        test_error("no workspace groups.");
        return NULL;
    }

    int i = 0;
    struct group_node *group = NULL;
    struct group_node *entry;

    wl_list_for_each(entry, &state->groups, link) {
        if (i == index) {
            group = entry;
            return group;
        }
        i++;
    }

    test_error("index out of bounds.");
    return NULL;
}

static struct workspace_node *find_workspace_by_id(struct test_state *state, const char *id) {

    struct workspace_node *workspace;
    wl_list_for_each(workspace, &state->workspaces, global_link) {
        if (workspace->id != NULL && strcmp(workspace->id, id) == 0) {
            return workspace;
        }
    }
    return NULL;
}

static void ws_handle_id(void *data, struct ext_workspace_handle_v1 *handle, const char *id) {
    struct workspace_node *ws = data;
    free(ws->id);
    ws->id = strdup(id);
}

static void ws_handle_name(void *data, struct ext_workspace_handle_v1 *handle, const char *name) {
    struct workspace_node *ws = data;
    free(ws->name);
    ws->name = strdup(name);
}

static void ws_handle_coordinates(void *data, struct ext_workspace_handle_v1 *handle,
                                  struct wl_array *coordinates) {}

static void ws_handle_state(void *data, struct ext_workspace_handle_v1 *handle,
                            uint32_t state_flags) {
    struct workspace_node *ws = data;

    ws->active = (state_flags & EXT_WORKSPACE_HANDLE_V1_STATE_ACTIVE) != 0;
    ws->hidden = (state_flags & EXT_WORKSPACE_HANDLE_V1_STATE_HIDDEN) != 0;
    ws->urgent = (state_flags & EXT_WORKSPACE_HANDLE_V1_STATE_URGENT) != 0;
}

static void ws_handle_capabilities(void *data, struct ext_workspace_handle_v1 *handle,
                                   uint32_t caps) {
    struct workspace_node *workspace = data;
    workspace->capabilities = caps;
}

static void ws_handle_removed(void *data, struct ext_workspace_handle_v1 *handle) {
    struct workspace_node *ws = data;
    if (ws->group_link.next) {
        wl_list_remove(&ws->group_link);
    }
    wl_list_remove(&ws->global_link);

    ext_workspace_handle_v1_destroy(handle);
    free(ws->id);
    free(ws->name);
    struct test_state *state = ws->state;
    free(ws);
}

static const struct ext_workspace_handle_v1_listener workspace_listener = {
    .id = ws_handle_id,
    .name = ws_handle_name,
    .coordinates = ws_handle_coordinates,
    .state = ws_handle_state,
    .capabilities = ws_handle_capabilities,
    .removed = ws_handle_removed,
};

static void group_handle_capabilities(void *data,
                                      struct ext_workspace_group_handle_v1 *group_handle,
                                      uint32_t caps) {
    struct group_node *group = data;
    group->capabilities = caps;
}

static void group_handle_output_enter(void *data,
                                      struct ext_workspace_group_handle_v1 *group_handle,
                                      struct wl_output *output) {
    struct group_node *group = data;
    group->output_count++;
}

static void group_handle_output_leave(void *data,
                                      struct ext_workspace_group_handle_v1 *group_handle,
                                      struct wl_output *output) {
    struct group_node *group = data;
    group->output_count--;
}

static void group_handle_workspace_enter(void *data,
                                         struct ext_workspace_group_handle_v1 *group_handle,
                                         struct ext_workspace_handle_v1 *ws_handle) {
    struct group_node *group = data;

    // Look up workspace handle in the manager's workspace list
    struct workspace_node *ws, *target_ws = NULL;
    wl_list_for_each(ws, &group->state->workspaces, global_link) {
        if (ws->handle == ws_handle) {
            target_ws = ws;
            break;
        }
    }

    if (!target_ws) {
        return;
    }

    target_ws->group = group;

    // Add to group's workspace list if not already present
    struct workspace_node *gws;
    wl_list_for_each(gws, &group->workspaces, group_link) {
        if (gws == target_ws)
            return;
    }

    wl_list_insert(&group->workspaces, &target_ws->group_link);
}

static void group_handle_workspace_leave(void *data,
                                         struct ext_workspace_group_handle_v1 *group_handle,
                                         struct ext_workspace_handle_v1 *ws_handle) {
    struct group_node *group = data;
    struct workspace_node *ws, *tmp;
    wl_list_for_each_safe(ws, tmp, &group->workspaces, group_link) {
        if (ws->handle == ws_handle) {
            wl_list_remove(&ws->group_link);
            ws->group = NULL;
            break;
        }
    }
}

static void group_handle_removed(void *data, struct ext_workspace_group_handle_v1 *group_handle) {
    struct group_node *group = data;
    wl_list_remove(&group->link);
    ext_workspace_group_handle_v1_destroy(group_handle);
    struct test_state *state = group->state;
    free(group);
}

static const struct ext_workspace_group_handle_v1_listener group_listener = {
    .capabilities = group_handle_capabilities,
    .output_enter = group_handle_output_enter,
    .output_leave = group_handle_output_leave,
    .workspace_enter = group_handle_workspace_enter,
    .workspace_leave = group_handle_workspace_leave,
    .removed = group_handle_removed,
};

static void manager_handle_workspace_group(void *data, struct ext_workspace_manager_v1 *mgr,
                                           struct ext_workspace_group_handle_v1 *group_handle) {
    struct test_state *state = data;

    struct group_node *group = calloc(1, sizeof(*group));
    group->handle = group_handle;
    group->state = state;
    wl_list_init(&group->workspaces);

    wl_list_insert(&state->groups, &group->link);
    ext_workspace_group_handle_v1_add_listener(group_handle, &group_listener, group);
}

static void manager_handle_workspace(void *data, struct ext_workspace_manager_v1 *mgr,
                                     struct ext_workspace_handle_v1 *ws_handle) {
    struct test_state *state = data;

    struct workspace_node *ws = calloc(1, sizeof(*ws));
    ws->handle = ws_handle;
    ws->state = state;

    wl_list_insert(&state->workspaces, &ws->global_link);

    ext_workspace_handle_v1_add_listener(ws_handle, &workspace_listener, ws);
}

static void manager_handle_done(void *data, struct ext_workspace_manager_v1 *mgr) {}

static void manager_handle_finished(void *data, struct ext_workspace_manager_v1 *mgr) {}

static const struct ext_workspace_manager_v1_listener manager_listener = {
    .workspace_group = manager_handle_workspace_group,
    .workspace = manager_handle_workspace,
    .done = manager_handle_done,
    .finished = manager_handle_finished,
};

static void registry_handler(struct client_state *base, struct wl_registry *registry, uint32_t name,
                             const char *interface, uint32_t version) {
    struct test_state *state = (struct test_state *)base;

    if (strcmp(interface, ext_workspace_manager_v1_interface.name) == 0) {
        state->manager = wl_registry_bind(registry, name, &ext_workspace_manager_v1_interface, 1);
        ext_workspace_manager_v1_add_listener(state->manager, &manager_listener, state);
    } else if (strcmp(interface, wl_output_interface.name) == 0) {
        // We need to bind to the output interface to get output enter/leave events
        wl_registry_bind(registry, name, &wl_output_interface, 1);
    }
}

static void cmd_list(struct test_state *state) {
    int group_idx = 0;
    struct group_node *group;
    wl_list_for_each(group, &state->groups, link) {
        struct workspace_node *ws;
        wl_list_for_each(ws, &group->workspaces, group_link) {
            test_message("Workspace [%s] \"%s\" (active=%s, hidden=%s, urgent=%s)",
                         ws->id ? ws->id : "no-id", ws->name ? ws->name : "no-name",
                         ws->active ? "YES" : "no", ws->hidden ? "YES" : "no",
                         ws->urgent ? "YES" : "no");
        }
    }
    test_ok();
}

static void cmd_action(struct test_state *state, const char *id, int action) {
    struct workspace_node *workspace = find_workspace_by_id(state, id);

    if (workspace == NULL && action != WORKSPACE_ACTION_CREATE) {
        test_error("unknown workspace id: %s", id);
        return;
    } else if (workspace != NULL && action == WORKSPACE_ACTION_CREATE) {
        test_error("can't create workspace with existing id.");
        return;
    }

    if (action == WORKSPACE_ACTION_ACTIVATE) {
        ext_workspace_handle_v1_activate(workspace->handle);
    } else if (action == WORKSPACE_ACTION_REMOVE) {
        ext_workspace_handle_v1_remove(workspace->handle);
    } else if (action == WORKSPACE_ACTION_CREATE) {
        if (wl_list_empty(&state->groups)) {
            test_error("no workspace groups found.");
            return;
        }
        struct group_node *group = wl_container_of(state->groups.next, group, link);
        ext_workspace_group_handle_v1_create_workspace(group->handle, id);
    }

    ext_workspace_manager_v1_commit(state->manager);
    test_ok();
}

static void cmd_workspace_group_capabilities(struct test_state *state, int index) {
    struct group_node *group = find_workspace_group_by_id(state, index);

    if (group == NULL) {
        return;
    }

    if (group->capabilities && EXT_WORKSPACE_GROUP_HANDLE_V1_GROUP_CAPABILITIES_CREATE_WORKSPACE) {
        test_message("create_workspace");
    }
    test_ok();
}

static void cmd_workspace_group_outputs(struct test_state *state, int index) {
    struct group_node *group = find_workspace_group_by_id(state, index);

    if (group == NULL) {
        return;
    }

    test_message("outputs: %d", group->output_count);
    test_ok();
}

static void cmd_workspace_capabilities(struct test_state *state, const char *id) {
    struct workspace_node *workspace = find_workspace_by_id(state, id);

    if (workspace == NULL) {
        test_error("unknown workspace id: %s.", id);
        return;
    }

    if (workspace->capabilities & EXT_WORKSPACE_HANDLE_V1_WORKSPACE_CAPABILITIES_ACTIVATE) {
        test_message("activate");
    }
    if (workspace->capabilities & EXT_WORKSPACE_HANDLE_V1_WORKSPACE_CAPABILITIES_DEACTIVATE) {
        test_message("deactivate");
    }
    if (workspace->capabilities & EXT_WORKSPACE_HANDLE_V1_WORKSPACE_CAPABILITIES_REMOVE) {
        test_message("remove");
    }
    if (workspace->capabilities & EXT_WORKSPACE_HANDLE_V1_WORKSPACE_CAPABILITIES_ASSIGN) {
        test_message("assign");
    }
    test_ok();
}

static bool dispatch_command(struct client_state *base, const char *cmd, const char *arg) {
    struct test_state *state = (struct test_state *)base;

    if (strcmp(cmd, "list") == 0) {
        cmd_list(state);
    } else if (strcmp(cmd, "activate") == 0) {
        cmd_action(state, arg, WORKSPACE_ACTION_ACTIVATE);
    } else if (strcmp(cmd, "remove") == 0) {
        cmd_action(state, arg, WORKSPACE_ACTION_REMOVE);
    } else if (strcmp(cmd, "create_workspace") == 0) {
        cmd_action(state, arg, WORKSPACE_ACTION_CREATE);
    } else if (strcmp(cmd, "workspace_group_capabilities") == 0) {
        cmd_workspace_group_capabilities(state, atoi(arg));
    } else if (strcmp(cmd, "workspace_capabilities") == 0) {
        cmd_workspace_capabilities(state, arg);
    } else if (strcmp(cmd, "workspace_group_outputs") == 0) {
        cmd_workspace_group_outputs(state, atoi(arg));
    } else if (strcmp(cmd, "quit") == 0) {
        return false;
    }
    return true;
}

void setup(struct client_state *base) {
    struct test_state *state = (struct test_state *)base;

    wl_list_init(&state->groups);
    wl_list_init(&state->workspaces);
}

void cleanup(struct client_state *base) {
    struct test_state *state = (struct test_state *)base;
    if (state == NULL) {
        return;
    }

    struct workspace_node *ws, *tmp_ws;
    wl_list_for_each_safe(ws, tmp_ws, &state->workspaces, global_link) {
        wl_list_remove(&ws->global_link);

        if (ws->group_link.next && ws->group_link.prev) {
            wl_list_remove(&ws->group_link);
        }

        if (ws->handle) {
            ext_workspace_handle_v1_destroy(ws->handle);
        }

        free(ws->id);
        free(ws->name);
        free(ws);
    }

    struct group_node *group, *tmp_group;
    wl_list_for_each_safe(group, tmp_group, &state->groups, link) {
        wl_list_remove(&group->link);

        if (group->handle) {
            ext_workspace_group_handle_v1_destroy(group->handle);
        }

        free(group);
    }

    if (state->manager) {
        ext_workspace_manager_v1_destroy(state->manager);
        state->manager = NULL;
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
