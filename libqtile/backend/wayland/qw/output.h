#ifndef OUTPUT_H
#define OUTPUT_H

#include <wayland-server-core.h>
#include <wlr/backend/headless.h>
#include <wlr/types/wlr_output.h>
#include <wlr/types/wlr_scene.h>

struct qw_server;

struct qw_output {
    struct qw_server *server;
    struct wlr_scene_output *scene;
    struct wlr_output *wlr_output;
    int x;
    int y;

    struct wlr_box full_area;
    struct wlr_box area;

    // Private data
    struct wl_list link;
    struct wl_listener frame;
    struct wl_listener request_state;
    struct wl_listener destroy;
    struct wl_list layers[4];
};

void qw_output_arrange_layers(struct qw_output *output);

void qw_server_output_new(struct qw_server *server, struct wlr_output *wlr_output);

#endif /* OUTPUT_H */
