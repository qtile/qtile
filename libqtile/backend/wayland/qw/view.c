#include "view.h"
#include <stdlib.h>
#include <wlr/util/log.h>

// Frees all border rectangles and their associated scene nodes of the view.
// Checks if borders exist, then destroys each of the 4 border scene nodes per border set.
// Finally frees the allocated borders array.
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

// Creates and paints multiple border layers around the view content.
// colors: array of RGBA colors for each border layer (each is 4 floats).
// width: total border width in pixels.
// n: number of border layers to draw.
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

    // Offset the view's tree node by the border width so content appears centered inside borders
    wlr_scene_node_set_position(tree_node, width, width);

    int outer_w = view->width + width * 2;
    int outer_h = view->height + width * 2;
    int coord = 0; // Keeps track of cumulative offset for layering borders

    // Helper struct to define rectangle parameters for each border side
    struct border_pairs {
        int x;
        int y;
        int w;
        int h;
    };

    for (int i = 0; i < n; i++) {
        // Divide the total border width into equal parts for each border layer
        // Add leftover pixels to the first few layers to sum to total width
        int bw = (int)(width / n) + (int)(i < (width % n));

        // clang-format off
        struct border_pairs pairs[4] = {
            { .x = coord, .y = coord, .w = outer_w - coord * 2, .h = bw },                          // top border
            { .x = outer_w - bw - coord, .y = bw + coord, .w = bw, .h = outer_h - bw * 2 - coord * 2 },  // right border
            { .x = coord, .y = outer_h - bw - coord, .w = outer_w - coord * 2, .h = bw },          // bottom border
            { .x = coord, .y = bw + coord, .w = bw, .h = outer_h - bw * 2 - coord * 2 },          // left border
        };
        // clang-format on

        // Create rectangles and position them according to pairs
        for (int j = 0; j < 4; j++) {
            view->borders[i][j] =
                wlr_scene_rect_create(view->content_tree, pairs[j].w, pairs[j].h, colors[i]);
            wlr_scene_node_set_position(&view->borders[i][j]->node, pairs[j].x, pairs[j].y);
        }

        // Increase the offset for the next inner border layer
        coord += bw;
    }

    // Ensure the tree node is painted above other nodes
    wlr_scene_node_raise_to_top(tree_node);
}
