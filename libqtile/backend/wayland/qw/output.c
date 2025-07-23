#include "output.h"
#include "layer-view.h"
#include "server.h"
#include <stdio.h>
#include <stdlib.h>

static void qw_output_handle_frame(struct wl_listener *listener, void *data) {
    // Called when the output is ready to display a new frame
    struct qw_output *output = wl_container_of(listener, output, frame);
    struct wlr_scene *scene = output->server->scene;

    struct wlr_scene_output *scene_output = wlr_scene_get_scene_output(scene, output->wlr_output);

    wlr_scene_output_commit(scene_output, NULL);

    // Send a frame done event with the current time
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
    // Handle client requests to change the output state (mode, enabled, etc.)
    struct qw_output *output = wl_container_of(listener, output, request_state);
    const struct wlr_output_event_request_state *event = data;
    wlr_output_commit_state(output->wlr_output, event->state);
}

void qw_output_arrange_layer(struct qw_output *output, struct wl_list *list,
                             struct wlr_box *usable_area, int exclusive) {
    struct wlr_box full_area = output->full_area;

    struct qw_layer_view *layer_view;
    wl_list_for_each(layer_view, list, link) {
        struct wlr_layer_surface_v1 *layer_surface = layer_view->surface;
        if (!layer_surface)
            continue;

        if (!layer_surface->initialized)
            continue;

        if (exclusive != (layer_surface->current.exclusive_zone > 0))
            continue;

        wlr_scene_layer_surface_v1_configure(layer_view->scene, &full_area, usable_area);
        wlr_scene_node_set_position(&layer_view->popups->node, layer_view->scene->tree->node.x,
                                    layer_view->scene->tree->node.y);
    }
}

void qw_output_arrange_layers(struct qw_output *output) {
    int i;
    struct wlr_box usable_area = output->full_area;
    if (!output->wlr_output->enabled) {
        return;
    }

    for (i = 3; i >= 0; i--) {
        qw_output_arrange_layer(output, &output->layers[i], &usable_area, 1);
    }

    if (!wlr_box_equal(&usable_area, &output->area)) {
        output->area = usable_area;
        output->server->on_screen_reserve_space_cb(output, output->server->cb_data);
    }

    for (i = 3; i >= 0; i--) {
        qw_output_arrange_layer(output, &output->layers[i], &usable_area, 0);
    }

    uint32_t layers_above_shell[] = {
        ZWLR_LAYER_SHELL_V1_LAYER_OVERLAY,
        ZWLR_LAYER_SHELL_V1_LAYER_TOP,
    };

    // TODO: topmost keyboard interactive layer
    for (i = 0; i < 2; i++) {
        struct qw_layer_view *layer_view;
        wl_list_for_each_reverse(layer_view, &output->layers[layers_above_shell[i]], link) {
            // TODO: locked
            if (!layer_view->surface->current.keyboard_interactive || !layer_view->mapped)
                continue;
            // TODO: focus, exclusive focus, notify enter
            return;
        }
    }
}

void qw_server_output_new(struct qw_server *server, struct wlr_output *wlr_output) {
    // Allocate and initialize a new output object
    struct qw_output *output = calloc(1, sizeof(*output));
    if (!output) {
        wlr_log(WLR_ERROR, "failed to create qw_output struct");
        return;
    }

    wlr_output_init_render(wlr_output, server->allocator, server->renderer);

    output->scene = wlr_scene_output_create(server->scene, wlr_output);

    // Setup initial output state and enable the output
    struct wlr_output_state state;
    wlr_output_state_init(&state);
    wlr_output_state_set_enabled(&state, true);

    // During tests, we want to fix the geometry of the 1 or 2 outputs
    if (getenv("PYTEST_CURRENT_TEST") && wlr_output_is_headless(wlr_output)) {
        if (wl_list_empty(&server->outputs)) {
            wlr_output_state_set_custom_mode(&state, 800, 600, 0);
        } else {
            wlr_output_state_set_custom_mode(&state, 640, 480, 0);
        }
    } else {
        struct wlr_output_mode *mode = wlr_output_preferred_mode(wlr_output);
        if (mode) {
            wlr_output_state_set_mode(&state, mode);
        }
    }

    wlr_output_commit_state(wlr_output, &state);
    wlr_output_state_finish(&state);

    wlr_output->data = output;
    output->wlr_output = wlr_output;
    output->server = server;

    // Store references to the wlr_output and server
    for (int i = 0; i < 4; i++)
        wl_list_init(&output->layers[i]);

    // Setup listeners for frame, request_state, and destroy events
    output->frame.notify = qw_output_handle_frame;
    wl_signal_add(&wlr_output->events.frame, &output->frame);

    output->request_state.notify = qw_output_handle_request_state;
    wl_signal_add(&wlr_output->events.request_state, &output->request_state);

    output->destroy.notify = qw_output_handle_destroy;
    wl_signal_add(&wlr_output->events.destroy, &output->destroy);

    // Insert output at end of list
    wl_list_insert(server->outputs.prev, &output->link);

    // Add the output to the output layout automatically and to the scene layout
    struct wlr_output_layout_output *l_output =
        wlr_output_layout_add_auto(server->output_layout, wlr_output);
    wlr_scene_output_layout_add_output(server->scene_layout, l_output, output->scene);
}
