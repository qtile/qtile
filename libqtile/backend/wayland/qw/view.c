#include "view.h"
#include <stdlib.h>
#include <wlr/util/log.h>

void qw_view_cleanup_borders(struct qw_view *view) {
    if (!view->borders) {
        return;
    }
    for (int i = 0; i < view->bn; ++i) {
        for (int j = 0; j < 4; ++j) {
            wlr_scene_node_destroy(&view->borders[i][j]->node);
        }
    }
    free(view->borders);
}

void qw_view_paint_borders(struct qw_view *view, float (*colors)[4], int width, int n) {
    struct wlr_scene_node *tree_node = view->get_tree_node(view);
    if (!tree_node || !view->content_tree) {
        return;
    }
    qw_view_cleanup_borders(view);
    view->bn = n;
    view->borders = malloc(n * sizeof(struct wlr_scene_rect[4]));
    if (!view->borders) {
        wlr_log(WLR_ERROR, "failed to allocate memory for borders");
        return;
    }
    wlr_scene_node_set_position(tree_node, width, width);

    int outer_w = view->width + width * 2;
    int outer_h = view->height + width * 2;
    int coord = 0;

    struct border_pairs {
        int x;
        int y;
        int w;
        int h;
    };

    for (int i = 0; i < n; i++) {
        // set the current border width to equal parts of the total width
        // and distribute the remainder
        int bw = (int)(width / n) + (int)(i < (width % n));
        // let's keep it readable
        // clang format makes a giant mess here
        // clang-format off
        struct border_pairs pairs[4] = {
            { .x = coord, .y = coord, .w = outer_w - coord * 2, .h = bw },
            { .x = outer_w - bw - coord, .y = bw + coord, .w = bw, .h = outer_h - bw * 2 - coord * 2 },
            { .x = coord, .y = outer_h - bw - coord, .w = outer_w - coord * 2, .h = bw },
            { .x = coord, .y = bw + coord, .w = bw, .h = outer_h - bw * 2 - coord * 2 },
        };
        // clang-format on
        for (int j = 0; j < 4; j++) {
            view->borders[i][j] =
                wlr_scene_rect_create(view->content_tree, pairs[j].w, pairs[j].h, colors[i]);
            wlr_scene_node_set_position(&view->borders[i][j]->node, pairs[j].x, pairs[j].y);
        }
        coord += bw;
    }

    wlr_scene_node_raise_to_top(tree_node);
}
