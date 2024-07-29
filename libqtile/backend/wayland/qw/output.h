#ifndef OUTPUT_H
#define OUTPUT_H

#include <wayland-server-core.h>
#include <wlr/types/wlr_output.h>
#include <wlr/types/wlr_scene.h>

struct qw_server;

struct qw_output {
    struct wl_list link;
    struct qw_server *server;
    struct wlr_scene_output *scene;
    struct wlr_output *wlr_output;
    struct wl_listener frame;
    struct wl_listener request_state;
    struct wl_listener destroy;
    int x;
    int y;
};

void qw_server_output_new(struct qw_server *server, struct wlr_output *wlr_output);

#endif /* OUTPUT_H */
