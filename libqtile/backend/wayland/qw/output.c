#include "output.h"
#include "server.h"
#include <stdio.h>
#include <stdlib.h>

static void qw_output_handle_frame(struct wl_listener *listener, void *data) {
    struct qw_output *output = wl_container_of(listener, output, frame);
    struct wlr_scene *scene = output->server->scene;

    struct wlr_scene_output *scene_output = wlr_scene_get_scene_output(scene, output->wlr_output);

    wlr_scene_output_commit(scene_output, NULL);

    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    wlr_scene_output_send_frame_done(scene_output, &now);
}

static void qw_output_handle_destroy(struct wl_listener *listener, void *data) {
    struct qw_output *output = wl_container_of(listener, output, destroy);

    wl_list_remove(&output->frame.link);
    wl_list_remove(&output->request_state.link);
    wl_list_remove(&output->destroy.link);
    wl_list_remove(&output->link);
    free(output);
}

static void qw_output_handle_request_state(struct wl_listener *listener, void *data) {
    struct qw_output *output = wl_container_of(listener, output, request_state);
    const struct wlr_output_event_request_state *event = data;
    wlr_output_commit_state(output->wlr_output, event->state);
}

void qw_server_output_new(struct qw_server *server, struct wlr_output *wlr_output) {
    struct qw_output *output = calloc(1, sizeof(*output));
    if (!output) {
        wlr_log(WLR_ERROR, "failed to create qw_output struct");
        return;
    }
    wlr_output_init_render(wlr_output, server->allocator, server->renderer);
    output->scene = wlr_scene_output_create(server->scene, wlr_output);

    struct wlr_output_state state;
    wlr_output_state_init(&state);
    wlr_output_state_set_enabled(&state, true);

    struct wlr_output_mode *mode = wlr_output_preferred_mode(wlr_output);
    if (mode) {
        wlr_output_state_set_mode(&state, mode);
    }
    wlr_output_commit_state(wlr_output, &state);
    wlr_output_state_finish(&state);

    output->wlr_output = wlr_output;
    output->server = server;

    output->frame.notify = qw_output_handle_frame;
    wl_signal_add(&wlr_output->events.frame, &output->frame);

    output->request_state.notify = qw_output_handle_request_state;
    wl_signal_add(&wlr_output->events.request_state, &output->request_state);

    output->destroy.notify = qw_output_handle_destroy;
    wl_signal_add(&wlr_output->events.destroy, &output->destroy);
    wl_list_insert(&server->outputs, &output->link);
    struct wlr_output_layout_output *l_output =
        wlr_output_layout_add_auto(server->output_layout, wlr_output);
    wlr_scene_output_layout_add_output(server->scene_layout, l_output, output->scene);
}
