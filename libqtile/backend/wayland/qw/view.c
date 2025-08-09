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

bool qw_view_is_visible(struct qw_view *view) {
    return view->content_tree->node.enabled;
}

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
