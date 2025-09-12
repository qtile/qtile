#include "view.h"
#include "cairo-buffer.h"
#include "server.h"
#include <stdlib.h>
#include <wlr/util/log.h>

// Frees all border rectangles and their associated scene nodes of the view.
// Checks if borders exist, then destroys each of the 4 border scene nodes per border set.
// Finally frees the allocated borders array.
void qw_view_cleanup_borders(struct qw_view *view) {
    if (!view->borders) {
        return;
    }

    for (int i = 0; i < view->bn; i++) {
        switch (view->borders[i].type) {
        case QW_BORDER_RECT:
            for (int j = 0; j < 4; j++) {
                if (view->borders[i].rects[j]) {
                    wlr_scene_node_destroy(&view->borders[i].rects[j]->node);
                    view->borders[i].rects[j] = NULL;
                }
            }
            break;
        case QW_BORDER_BUFFER:
            for (int j = 0; j < 4; j++) {
                if (view->borders[i].scene_bufs[j]) {
                    wlr_scene_node_destroy(&view->borders[i].scene_bufs[j]->node);
                    view->borders[i].scene_bufs[j] = NULL;
                }
            }
            break;
        }
    }

    free(view->borders);
}

void qw_view_reparent(struct qw_view *view, int layer) {
    wlr_scene_node_reparent(&view->content_tree->node, view->server->scene_windows_layers[layer]);
    view->layer = layer;
}

void qw_view_raise_to_top(struct qw_view *view) {
    wlr_scene_node_raise_to_top(&view->content_tree->node);
}
void qw_view_lower_to_bottom(struct qw_view *view) {
    wlr_scene_node_lower_to_bottom(&view->content_tree->node);
}

void qw_view_move_up(struct qw_view *view) {
    // the rightmost sibling in the tree
    // is the upper one
    // so we need to get the window to the right (x)
    // of this window and place this window above x
    struct wlr_scene_node *next_sibling = NULL;
    bool found_child = false;
    struct wlr_scene_node *child;
    wl_list_for_each(child, &view->server->scene_windows_tree[view->layer].children, link) {
        if (child == &view->content_tree->node) {
            found_child = true;
        } else if (found_child) {
            next_sibling = child;
            break;
        }
    }
    if (next_sibling) {
        wlr_scene_node_place_above(&view->content_tree->node, next_sibling);
    }
}

void qw_view_move_down(struct qw_view *view) {
    // the leftmost sibling in the tree
    // is the bottom one
    // so we need to get the window to the left (x)
    // of this window and place this window below x
    struct wlr_scene_node *prev_sibling = NULL;
    struct wlr_scene_node *child;
    wl_list_for_each(child, &view->server->scene_windows_tree[view->layer].children, link) {
        if (child == &view->content_tree->node) {
            break;
        }
        prev_sibling = child;
    }
    if (prev_sibling) {
        wlr_scene_node_place_above(&view->content_tree->node, prev_sibling);
    }
}

bool qw_view_is_visible(struct qw_view *view) { return view->content_tree->node.enabled; }

// Creates and paints multiple border layers around the view content.
// borders: array of qw_border for each border.
// border_count: number of border layers to draw.
void qw_view_paint_borders(struct qw_view *view, const struct qw_border *borders,
                           int border_count) {
    struct wlr_scene_node *tree_node = view->get_tree_node(view);
    if (!tree_node || !view->content_tree) {
        return;
    }

    qw_view_cleanup_borders(view);

    view->borders = calloc(border_count, sizeof(*view->borders));
    if (!view->borders) {
        wlr_log(WLR_ERROR, "Failed to allocate border layer tracking");
        return;
    }
    view->bn = border_count;

    int total_width = 0;
    for (int i = 0; i < border_count; i++) {
        total_width += borders[i].width;
    }

    wlr_scene_node_set_position(tree_node, total_width, total_width);

    int outer_w = view->width + total_width * 2;
    int outer_h = view->height + total_width * 2;

    int coord = 0;
    for (int i = 0; i < border_count; i++) {
        const struct qw_border *src = &borders[i];
        view->borders[i].type = src->type;

        int bw = src->width;

        // clang-format off
        struct wlr_box sides[4] = {
            { coord, coord, outer_w - coord * 2, bw },                              // top
            { outer_w - bw - coord, bw + coord, bw, outer_h - 2 * bw - coord * 2 }, // right
            { coord, outer_h - bw - coord, outer_w - coord * 2, bw },               // bottom
            { coord, bw + coord, bw, outer_h - 2 * bw - coord * 2 },                // left
        };
        // clang-format on

        if (src->type == QW_BORDER_RECT) {
            for (int j = 0; j < 4; j++) {
                struct wlr_scene_rect *rect = wlr_scene_rect_create(
                    view->content_tree, sides[j].width, sides[j].height, src->rect.color[j]);
                if (!rect) {
                    wlr_log(WLR_ERROR, "Failed to create scene_rect for border");
                    continue;
                }
                wlr_scene_node_set_position(&rect->node, sides[j].x, sides[j].y);
                view->borders[i].rects[j] = rect;
            }

        } else if (src->type == QW_BORDER_BUFFER) {
            cairo_surface_t *surface = src->buffer.surface;
            struct wlr_scene_buffer **buffers =
                create_scene_buffers_from_surface(view->content_tree, surface, sides, 4);

            for (int j = 0; j < 4; j++) {
                if (!buffers[j]) {
                    continue;
                }
                wlr_scene_node_set_position(&buffers[j]->node, sides[j].x, sides[j].y);
                view->borders[i].scene_bufs[j] = buffers[j];
            }
        }

        coord += bw;
    }

    wlr_scene_node_raise_to_top(tree_node);
}

// Foreign toplevel manager requests
static void qw_handle_ftl_request_activate(struct wl_listener *listener, void *data) {
    struct qw_view *view = wl_container_of(listener, view, ftl_request_activate);
    if (view != NULL) {
        int handled = view->request_focus_cb(view->cb_data);
        if (!handled) {
            wlr_log(WLR_ERROR, "Could not focus window from foreign toplevel manager.");
        }
    }
}

static void qw_handle_ftl_request_close(struct wl_listener *listener, void *data) {
    struct qw_view *view = wl_container_of(listener, view, ftl_request_close);
    if (view != NULL) {
        int handled = view->request_close_cb(view->cb_data);
        if (!handled) {
            wlr_log(WLR_ERROR, "Could not close window from foreign toplevel manager.");
        }
    }
}

static void qw_handle_ftl_request_maximize(struct wl_listener *listener, void *data) {
    struct wlr_foreign_toplevel_handle_v1_maximized_event *event = data;
    struct qw_view *view = wl_container_of(listener, view, ftl_request_maximize);
    if (view != NULL) {
        int handled = view->request_maximize_cb(event->maximized, view->cb_data);
        if (!handled) {
            wlr_log(WLR_ERROR, "Could not maximize window from foreign toplevel manager.");
        }
    }
}

static void qw_handle_ftl_request_minimize(struct wl_listener *listener, void *data) {
    struct wlr_foreign_toplevel_handle_v1_minimized_event *event = data;
    struct qw_view *view = wl_container_of(listener, view, ftl_request_minimize);
    if (view != NULL) {
        int handled = view->request_minimize_cb(event->minimized, view->cb_data);
        if (!handled) {
            wlr_log(WLR_ERROR, "Could not minimize window from foreign toplevel manager.");
        }
    }
}

static void qw_handle_ftl_request_fullscreen(struct wl_listener *listener, void *data) {
    struct wlr_foreign_toplevel_handle_v1_fullscreen_event *event = data;
    struct qw_view *view = wl_container_of(listener, view, ftl_request_fullscreen);
    if (view != NULL) {
        int handled = view->request_fullscreen_cb(event->fullscreen, view->cb_data);
        if (!handled) {
            wlr_log(WLR_ERROR, "Could not fullscreen window from foreign toplevel manager.");
        }
    }
}

static void qw_handle_ftl_output_enter(struct wl_listener *listener, void *data) {
    struct qw_view *view = wl_container_of(listener, view, ftl_output_enter);
    struct wlr_scene_output *output = data;
    if (view->ftl_handle != NULL) {
        wlr_foreign_toplevel_handle_v1_output_enter(view->ftl_handle, output->output);
    }
}

static void qw_handle_ftl_output_leave(struct wl_listener *listener, void *data) {
    struct qw_view *view = wl_container_of(listener, view, ftl_output_leave);
    struct wlr_scene_output *output = data;
    if (view->ftl_handle != NULL) {
        wlr_foreign_toplevel_handle_v1_output_leave(view->ftl_handle, output->output);
    }
}

static bool qw_handle_ftl_point_accepts_input(struct wlr_scene_buffer *buffer, double *x,
                                              double *y) {
    return false;
}

void qw_view_resize_ftl_output_tracking_buffer(struct qw_view *view, int width, int height) {
    if (view->ftl_output_tracking_buffer == NULL) {
        return;
    }
    wlr_scene_buffer_set_dest_size(view->ftl_output_tracking_buffer, width, height);
}

void qw_view_ftl_manager_handle_create(struct qw_view *view) {
    // Create a foreign toplevel handle and set up listeners
    view->ftl_handle = wlr_foreign_toplevel_handle_v1_create(view->server->ftl_mgr);

    view->ftl_request_activate.notify = qw_handle_ftl_request_activate;
    wl_signal_add(&view->ftl_handle->events.request_activate, &view->ftl_request_activate);

    view->ftl_request_close.notify = qw_handle_ftl_request_close;
    wl_signal_add(&view->ftl_handle->events.request_close, &view->ftl_request_close);

    view->ftl_request_maximize.notify = qw_handle_ftl_request_maximize;
    wl_signal_add(&view->ftl_handle->events.request_maximize, &view->ftl_request_maximize);

    view->ftl_request_minimize.notify = qw_handle_ftl_request_minimize;
    wl_signal_add(&view->ftl_handle->events.request_minimize, &view->ftl_request_minimize);

    view->ftl_request_fullscreen.notify = qw_handle_ftl_request_fullscreen;
    wl_signal_add(&view->ftl_handle->events.request_fullscreen, &view->ftl_request_fullscreen);

    view->ftl_output_tracking_buffer = wlr_scene_buffer_create(view->content_tree, NULL);
    if (view->ftl_output_tracking_buffer != NULL) {
        view->ftl_output_enter.notify = qw_handle_ftl_output_enter;
        wl_signal_add(&view->ftl_output_tracking_buffer->events.output_enter,
                      &view->ftl_output_enter);
        view->ftl_output_leave.notify = qw_handle_ftl_output_leave;
        wl_signal_add(&view->ftl_output_tracking_buffer->events.output_leave,
                      &view->ftl_output_leave);
        view->ftl_output_tracking_buffer->point_accepts_input = qw_handle_ftl_point_accepts_input;
    } else {
        wlr_log(WLR_ERROR, "Failed to create a foreign toplevel tracking buffer.");
    }
}

void qw_view_ftl_manager_handle_destroy(struct qw_view *view) {
    if (view->ftl_handle == NULL) {
        return;
    }

    // Remove signal listeners
    wl_list_remove(&view->ftl_request_activate.link);
    wl_list_remove(&view->ftl_request_close.link);
    wl_list_remove(&view->ftl_request_maximize.link);
    wl_list_remove(&view->ftl_request_minimize.link);
    wl_list_remove(&view->ftl_request_fullscreen.link);

    // Remove output tracking
    if (view->ftl_output_tracking_buffer != NULL) {
        wl_list_remove(&view->ftl_output_enter.link);
        wl_list_remove(&view->ftl_output_leave.link);
        wlr_scene_node_destroy(&view->ftl_output_tracking_buffer->node);
        view->ftl_output_tracking_buffer = NULL;
    }

    // Destroy the handle
    wlr_foreign_toplevel_handle_v1_destroy(view->ftl_handle);
    view->ftl_handle = NULL;
}
