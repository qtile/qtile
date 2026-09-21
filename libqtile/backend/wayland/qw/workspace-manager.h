#ifndef WORKSPACE_MANAGER_H
#define WORKSPACE_MANAGER_H

#include <stdbool.h>
#include <wlr/types/wlr_ext_workspace_v1.h>

struct qw_server;

enum { WORKSPACE_GROUP_ACTIVATE, WORKSPACE_GROUP_REMOVE, WORKSPACE_GROUP_CREATE_WORKSPACE };

// Functions for workspace manager lifecycle
bool qw_workspace_manager_init(struct qw_server *server);
void qw_workspace_manager_finish(struct qw_server *server);

// Functions called from the python backend
void qw_workspace_manager_create_workspace(struct qw_server *server, const char *id,
                                           const char *name);
void qw_workspace_manager_delete_workspace(struct qw_server *server, const char *id);
void qw_workspace_set_state(struct qw_server *server, const char *id, const char *name, bool active,
                            bool hidden, bool urgent);

#endif /* WORKSPACE_MANAGER_H */
