#include <stdlib.h>
#include <wayland-server-core.h>
#include <wlr/types/wlr_ext_workspace_v1.h>

#include "output.h"
#include "server.h"
#include "workspace-manager.h"

static struct wlr_ext_workspace_handle_v1 *find_workspace_by_id(struct qw_server *server,
                                                                const char *id) {
    if (!server || !server->workspace_manager || !id)
        return NULL;

    struct wlr_ext_workspace_handle_v1 *ws;
    wl_list_for_each(ws, &server->workspace_manager->workspaces, link) {
        if (ws->id && strcmp(ws->id, id) == 0) {
            return ws;
        }
    }
    return NULL;
}

static void handle_workspace_commit(struct wl_listener *listener, void *data) {
    struct qw_server *server = wl_container_of(listener, server, workspace_commit);
    struct wlr_ext_workspace_v1_commit_event *event = data;
    struct wlr_ext_workspace_v1_request *req;

    wl_list_for_each(req, event->requests, link) {
        switch (req->type) {
        case WLR_EXT_WORKSPACE_V1_REQUEST_ACTIVATE:
            if (req->activate.workspace != NULL && req->activate.workspace->id != NULL) {
                server->workspace_manager_group_action_cb(
                    server->cb_data, req->activate.workspace->id, WORKSPACE_GROUP_ACTIVATE);
            }
            break;

        // Deactivating a group should only be done by qtile
        case WLR_EXT_WORKSPACE_V1_REQUEST_DEACTIVATE:
            break;

        case WLR_EXT_WORKSPACE_V1_REQUEST_CREATE_WORKSPACE:
            if (req->create_workspace.name != NULL) {
                server->workspace_manager_group_action_cb(
                    server->cb_data, req->create_workspace.name, WORKSPACE_GROUP_CREATE_WORKSPACE);
            }
            break;

        case WLR_EXT_WORKSPACE_V1_REQUEST_REMOVE:
            if (req->remove.workspace != NULL && req->remove.workspace->id != NULL) {
                server->workspace_manager_group_action_cb(
                    server->cb_data, req->remove.workspace->id, WORKSPACE_GROUP_REMOVE);
            }
            break;

        // Assigning a workspace to a workspace group has no meaning in qtile
        // as we use a single, global workspace group.
        case WLR_EXT_WORKSPACE_V1_REQUEST_ASSIGN:
            break;
        }
    }
}

bool qw_workspace_manager_init(struct qw_server *server) {
    if (server == NULL || server->display == NULL) {
        return false;
    }

    wlr_log(WLR_ERROR, "Workspace manager init");

    server->workspace_manager =
        wlr_ext_workspace_manager_v1_create(server->display, 1); // Version 1
    if (server->workspace_manager == NULL) {
        return false;
    }

    // Create a global workspace group with creation capabilities
    uint32_t group_caps = EXT_WORKSPACE_GROUP_HANDLE_V1_GROUP_CAPABILITIES_CREATE_WORKSPACE;
    server->workspace_group =
        wlr_ext_workspace_group_handle_v1_create(server->workspace_manager, group_caps);
    if (server->workspace_group == NULL) {
        return false;
    }

    server->workspace_commit.notify = handle_workspace_commit;
    wl_signal_add(&server->workspace_manager->events.commit, &server->workspace_commit);

    return true;
}

void qw_workspace_manager_finish(struct qw_server *server) {
    if (server == NULL || server->workspace_manager == NULL) {
        return;
    }

    wl_list_remove(&server->workspace_commit.link);

    if (server->workspace_group != NULL) {
        wlr_ext_workspace_group_handle_v1_destroy(server->workspace_group);
        server->workspace_group = NULL;
    }

    struct wlr_ext_workspace_handle_v1 *ws, *tmp_ws;
    wl_list_for_each_safe(ws, tmp_ws, &server->workspace_manager->workspaces, link) {
        wlr_ext_workspace_handle_v1_destroy(ws);
    }

    server->workspace_manager = NULL;
}

void qw_workspace_manager_create_workspace(struct qw_server *server, const char *id,
                                           const char *name) {
    if (server == NULL || server->workspace_manager == NULL || server->workspace_group == NULL ||
        id == NULL) {
        return;
    }

    uint32_t caps = EXT_WORKSPACE_HANDLE_V1_WORKSPACE_CAPABILITIES_ACTIVATE |
                    EXT_WORKSPACE_HANDLE_V1_WORKSPACE_CAPABILITIES_REMOVE;

    struct wlr_ext_workspace_handle_v1 *ws =
        wlr_ext_workspace_handle_v1_create(server->workspace_manager, id, caps);

    wlr_ext_workspace_handle_v1_set_name(ws, name);
    wlr_ext_workspace_handle_v1_set_group(ws, server->workspace_group);
}

void qw_workspace_manager_delete_workspace(struct qw_server *server, const char *id) {
    struct wlr_ext_workspace_handle_v1 *ws = find_workspace_by_id(server, id);
    if (ws != NULL) {
        wlr_ext_workspace_handle_v1_destroy(ws);
    }
}

void qw_workspace_set_state(struct qw_server *server, const char *id, const char *name, bool active,
                            bool hidden, bool urgent) {
    struct wlr_ext_workspace_handle_v1 *ws = find_workspace_by_id(server, id);
    if (ws == NULL) {
        return;
    }

    uint32_t current_state = ws->state;

    bool current_active = (current_state & EXT_WORKSPACE_HANDLE_V1_STATE_ACTIVE) != 0;
    bool current_hidden = (current_state & EXT_WORKSPACE_HANDLE_V1_STATE_HIDDEN) != 0;
    bool current_urgent = (current_state & EXT_WORKSPACE_HANDLE_V1_STATE_URGENT) != 0;

    if (strcmp(ws->name, name) != 0) {
        wlr_ext_workspace_handle_v1_set_name(ws, name);
    }

    if (current_active != active) {
        wlr_ext_workspace_handle_v1_set_active(ws, active);
    }

    if (current_hidden != hidden) {
        wlr_ext_workspace_handle_v1_set_hidden(ws, hidden);
    }

    if (current_urgent != urgent) {
        wlr_ext_workspace_handle_v1_set_urgent(ws, urgent);
    }
}
