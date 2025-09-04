#include "layer-view.h"
#include "output.h"
#include "server.h"
#include "view.h"
#include <stdlib.h>

static const int zlayer_to_layer[] = {LAYER_BACKGROUND, LAYER_BOTTOM, LAYER_TOP, LAYER_OVERLAY};

static void qw_layer_view_handle_destroy(struct wl_listener *listener, void *data) {
    struct qw_layer_view *layer_view = wl_container_of(listener, layer_view, destroy);
    wl_list_remove(&layer_view->link);
    wl_list_remove(&layer_view->destroy.link);
    wl_list_remove(&layer_view->unmap.link);
    wl_list_remove(&layer_view->commit.link);
    wlr_scene_node_destroy(&layer_view->scene->tree->node);
    wlr_scene_node_destroy(&layer_view->popups->node);
    free(layer_view);
}

static void qw_layer_view_handle_unmap(struct wl_listener *listener, void *data) {
    struct qw_layer_view *layer_view = wl_container_of(listener, layer_view, unmap);

    layer_view->mapped = false;

    wlr_scene_node_set_enabled(&layer_view->scene->tree->node, false);
    // TODO: exclusive focus

    if (layer_view->surface->output) {
        layer_view->output = layer_view->surface->output->data;
        qw_output_arrange_layers(layer_view->output);
    }
    // TODO: focus
    // TODO: motionnotify?
}

// Handle commit event: called when surface commits state changes
static void qw_layer_view_handle_commit(struct wl_listener *listener, void *data) {
    struct qw_layer_view *layer_view = wl_container_of(listener, layer_view, commit);

    if (layer_view->surface->initial_commit) {
        struct qw_output *output = layer_view->surface->output->data;
        wlr_fractional_scale_v1_notify_scale(layer_view->surface->surface,
                                             output->wlr_output->scale);
        wlr_surface_set_preferred_buffer_scale(layer_view->surface->surface,
                                               (int32_t)ceilf(output->wlr_output->scale));

        struct wlr_layer_surface_v1_state state = layer_view->surface->current;
        layer_view->surface->current = layer_view->surface->pending;
        qw_output_arrange_layers(layer_view->output);
        layer_view->state = state;
        return;
    }

    bool mapped = layer_view->surface->surface->mapped;
    if (layer_view->surface->current.committed == 0 && layer_view->mapped == mapped) {
        return;
    }
    layer_view->mapped = mapped;

    int layer = zlayer_to_layer[layer_view->surface->current.layer];
    struct wlr_scene_tree *layer_tree = layer_view->server->scene_windows_layers[layer];

    if (layer_tree != layer_view->scene->tree->node.parent) {
        wlr_scene_node_reparent(&layer_view->scene->tree->node, layer_tree);
        wl_list_remove(&layer_view->link);
        wl_list_insert(&layer_view->output->layers[layer_view->surface->current.layer],
                       &layer_view->link);
        wlr_scene_node_reparent(&layer_view->popups->node,
                                (layer_view->surface->current.layer < ZWLR_LAYER_SHELL_V1_LAYER_TOP
                                     ? layer_view->server->scene_windows_layers[LAYER_TOP]
                                     : layer_tree));
    }

    qw_output_arrange_layers(layer_view->output);
}

// Create a new qw_layer_view for a given wlr_layer_surface
void qw_server_layer_view_new(struct qw_server *server,
                              struct wlr_layer_surface_v1 *layer_surface) {
    struct qw_layer_view *layer_view = calloc(1, sizeof(*layer_view));
    if (!layer_view) {
        wlr_log(WLR_ERROR, "failed to create qw_layer_view struct");
        return;
    }

    layer_view->server = server;
    layer_view->surface = layer_surface;

    // the layer surface does not have an output associated with it
    // assign it the current output
    if (!layer_surface->output) {
        // we cannot assign it to any output as we have none
        if (!server->current_output) {
            wlr_log(WLR_ERROR,
                    "cannot assign layer surface an output as there is no current output");
            wlr_layer_surface_v1_destroy(layer_surface);
            free(layer_view);
            return;
        }
        layer_surface->output = server->current_output;
    }

    layer_surface->data = layer_view;

    layer_view->commit.notify = qw_layer_view_handle_commit;
    wl_signal_add(&layer_surface->surface->events.commit, &layer_view->commit);
    layer_view->unmap.notify = qw_layer_view_handle_unmap;
    wl_signal_add(&layer_surface->surface->events.unmap, &layer_view->unmap);
    layer_view->destroy.notify = qw_layer_view_handle_destroy;
    wl_signal_add(&layer_surface->events.destroy, &layer_view->destroy);

    int layer = zlayer_to_layer[layer_surface->pending.layer];
    struct wlr_scene_tree *layer_tree = layer_view->server->scene_windows_layers[layer];
    layer_view->scene = wlr_scene_layer_surface_v1_create(layer_tree, layer_surface);
    layer_view->output = layer_surface->output->data;
    layer_view->popups = layer_surface->data =
        wlr_scene_tree_create(layer_surface->current.layer < ZWLR_LAYER_SHELL_V1_LAYER_TOP
                                  ? layer_view->server->scene_windows_layers[LAYER_TOP]
                                  : layer_tree);
    layer_view->scene->tree->node.data = layer_view->popups->node.data = layer_view;

    wl_list_insert(&layer_view->output->layers[layer_surface->pending.layer], &layer_view->link);
    wlr_surface_send_enter(layer_surface->surface, layer_surface->output);
}
