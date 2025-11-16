#include "layer-view.h"
#include "cursor.h"
#include "output.h"
#include "server.h"
#include "util.h"
#include "view.h"
#include <stdlib.h>

static const int zlayer_to_layer[] = {LAYER_BACKGROUND, LAYER_BOTTOM, LAYER_TOP, LAYER_OVERLAY};

static void qw_layer_view_handle_destroy(struct wl_listener *listener, void *data) {
    UNUSED(data);

    struct qw_layer_view *layer_view = wl_container_of(listener, layer_view, destroy);
    wl_list_remove(&layer_view->link);
    wl_list_remove(&layer_view->destroy.link);
    wl_list_remove(&layer_view->unmap.link);
    wl_list_remove(&layer_view->commit.link);
    wl_list_remove(&layer_view->new_popup.link);
    wlr_scene_node_destroy(&layer_view->scene->tree->node);
    wlr_scene_node_destroy(&layer_view->popups->node);
    free(layer_view);
}

static void qw_layer_view_handle_unmap(struct wl_listener *listener, void *data) {
    UNUSED(data);

    struct qw_layer_view *layer_view = wl_container_of(listener, layer_view, unmap);

    layer_view->mapped = false;

    wlr_scene_node_set_enabled(&layer_view->scene->tree->node, false);

    // Release exclusive layer lock
    if (layer_view == layer_view->server->exclusive_layer) {
        layer_view->server->exclusive_layer = NULL;
    }

    if (layer_view->surface->output) {
        layer_view->output = layer_view->surface->output->data;
        qw_output_arrange_layers(layer_view->output);
    }

    // Focus qtile's current_window if available, otherwise release focus
    // Force a cursor motion update for follow_mouse_focus
    if (layer_view->surface->surface == layer_view->server->seat->keyboard_state.focused_surface) {
        bool success = layer_view->server->focus_current_window_cb(layer_view->server->cb_data);
        if (!success) {
            wlr_seat_keyboard_clear_focus(layer_view->server->seat);
        }

        double x = layer_view->server->cursor->cursor->x;
        double y = layer_view->server->cursor->cursor->y;
        qw_cursor_warp_cursor(layer_view->server->cursor, x, y);
    }
}

// Handle commit event: called when surface commits state changes
static void qw_layer_view_handle_commit(struct wl_listener *listener, void *data) {
    UNUSED(data);

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

// Focus the layer_view if it is mapped (visible), calling internal focus helper
void qw_layer_view_focus(struct qw_layer_view *layer_view) {
    if (!layer_view->mapped) {
        return; // Can't focus if not mapped
    }

    struct qw_server *server = layer_view->server;
    struct wlr_seat *seat = server->seat;
    struct wlr_surface *prev_surface = seat->keyboard_state.focused_surface;

    if (prev_surface == layer_view->surface->surface) {
        return;
    }

    // Deactivate previous surface if any
    if (prev_surface) {
        qw_util_deactivate_surface(prev_surface);
    }

    // Notify keyboard about entering this surface (for keyboard input)
    struct wlr_keyboard *keyboard = wlr_seat_get_keyboard(seat);
    if (keyboard) {
        wlr_seat_keyboard_notify_enter(seat, layer_view->surface->surface, keyboard->keycodes,
                                       keyboard->num_keycodes, &keyboard->modifiers);
    }
}

static void qw_layer_popup_handle_destroy(struct wl_listener *listener, void *data) {
    UNUSED(data);

    struct qw_layer_popup *popup = wl_container_of(listener, popup, destroy);

    wl_list_remove(&popup->new_popup.link);
    wl_list_remove(&popup->destroy.link);
    wl_list_remove(&popup->surface_commit.link);
    free(popup);
}

static void qw_layer_popup_unconstrain(struct qw_layer_popup *popup) {
    struct wlr_xdg_popup *wlr_popup = popup->wlr_popup;
    struct qw_output *output = popup->toplevel->output;

    // if a client tries to create a popup while we are in the process of destroying
    // its output, don't crash.
    if (output == NULL) {
        return;
    }

    int width, height;
    wlr_output_effective_resolution(output->wlr_output, &width, &height);

    int lx, ly;
    wlr_scene_node_coords(&popup->toplevel->scene->tree->node, &lx, &ly);

    // the output box expressed in the coordinate system of the toplevel parent
    // of the popup
    struct wlr_box output_toplevel_sx_box = {
        .x = output->x - lx,
        .y = output->y - ly,
        .width = width,
        .height = height,
    };

    wlr_xdg_popup_unconstrain_from_box(wlr_popup, &output_toplevel_sx_box);
}

static void qw_layer_popup_handle_surface_commit(struct wl_listener *listener, void *data) {
    UNUSED(data);

    struct qw_layer_popup *popup = wl_container_of(listener, popup, surface_commit);
    if (popup->wlr_popup->base->initial_commit) {
        qw_layer_popup_unconstrain(popup);
    }
}

// Forward declaration
static void qw_layer_popup_handle_new_popup(struct wl_listener *listener, void *data);

static struct qw_layer_popup *qw_layer_popup_new(struct wlr_xdg_popup *wlr_popup,
                                                 struct qw_layer_view *toplevel,
                                                 struct wlr_scene_tree *parent) {
    struct qw_layer_popup *popup = calloc(1, sizeof(struct qw_layer_popup));
    if (popup == NULL) {
        wlr_log(WLR_ERROR, "failed to create qw_layer_popup struct");
        return NULL;
    }

    popup->toplevel = toplevel;
    popup->wlr_popup = wlr_popup;

    popup->xdg_surface_tree = wlr_scene_xdg_surface_create(parent, wlr_popup->base);
    if (popup->xdg_surface_tree == NULL) {
        free(popup);
        return NULL;
    }

    wl_signal_add(&wlr_popup->base->surface->events.commit, &popup->surface_commit);
    popup->surface_commit.notify = qw_layer_popup_handle_surface_commit;
    wl_signal_add(&wlr_popup->base->events.new_popup, &popup->new_popup);
    popup->new_popup.notify = qw_layer_popup_handle_new_popup;
    wl_signal_add(&wlr_popup->base->events.destroy, &popup->destroy);
    popup->destroy.notify = qw_layer_popup_handle_destroy;

    return popup;
}

static void qw_layer_popup_handle_new_popup(struct wl_listener *listener, void *data) {
    struct qw_layer_popup *popup = wl_container_of(listener, popup, new_popup);
    struct wlr_xdg_popup *wlr_popup = data;
    qw_layer_popup_new(wlr_popup, popup->toplevel, popup->xdg_surface_tree);
}

static void qw_layer_view_handle_new_popup(struct wl_listener *listener, void *data) {
    struct qw_layer_view *layer_view = wl_container_of(listener, layer_view, new_popup);
    struct wlr_xdg_popup *wlr_popup = data;
    qw_layer_popup_new(wlr_popup, layer_view, layer_view->popups);
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
        struct wlr_output *current_output = qw_server_get_current_output(server);
        if (current_output == NULL) {
            wlr_log(WLR_ERROR,
                    "cannot assign layer surface an output as there is no current output");
            wlr_layer_surface_v1_destroy(layer_surface);
            free(layer_view);
            return;
        }
        layer_surface->output = current_output;
    }

    layer_surface->data = layer_view;

    layer_view->commit.notify = qw_layer_view_handle_commit;
    wl_signal_add(&layer_surface->surface->events.commit, &layer_view->commit);
    layer_view->unmap.notify = qw_layer_view_handle_unmap;
    wl_signal_add(&layer_surface->surface->events.unmap, &layer_view->unmap);
    layer_view->destroy.notify = qw_layer_view_handle_destroy;
    wl_signal_add(&layer_surface->events.destroy, &layer_view->destroy);
    layer_view->new_popup.notify = qw_layer_view_handle_new_popup;
    wl_signal_add(&layer_surface->events.new_popup, &layer_view->new_popup);

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
