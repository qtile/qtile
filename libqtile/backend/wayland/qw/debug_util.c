#include "debug_util.h"

static void print_scene_node(struct wlr_scene_node *node, int depth, bool *draw_verticals, int child_i, int child_count, bool hide_rects) {
    if (hide_rects && node->type == WLR_SCENE_NODE_RECT) {
        return;
    }

    bool is_last = false;
    if (child_i == child_count-1) {
        is_last = true;
    }

    const char *type = "unknown";
    switch (node->type) {
        case WLR_SCENE_NODE_TREE:   type = "tree"; break;
        case WLR_SCENE_NODE_RECT:   type = "rect"; break;
        case WLR_SCENE_NODE_BUFFER: type = "buffer"; break;
    }

    const char* layer_name = "unknown";
    switch (child_i) {
        case LAYER_BACKGROUND:   layer_name = "LAYER_BACKGROUND"; break;
        case LAYER_BOTTOM:       layer_name = "LAYER_BOTTOM"; break;
        case LAYER_KEEPBELOW:    layer_name = "LAYER_KEEPBELOW"; break;
        case LAYER_LAYOUT:       layer_name = "LAYER_LAYOUT"; break;
        case LAYER_KEEPABOVE:    layer_name = "LAYER_KEEPABOVE"; break;
        case LAYER_MAX:          layer_name = "LAYER_MAX"; break;
        case LAYER_FULLSCREEN:   layer_name = "LAYER_FULLSCREEN"; break;
        case LAYER_BRINGTOFRONT: layer_name = "LAYER_BRINGTOFRONT"; break;
        case LAYER_TOP:          layer_name = "LAYER_TOP"; break;
        case LAYER_OVERLAY:      layer_name = "LAYER_OVERLAY"; break;
        case LAYER_END:          layer_name = "LAYER_END"; break;
    }

    struct qw_view *view = node->data;

    // Print visual indent tree structure
    char line[512] = {0};
    char *p = line;
    for (int i = 1; i < depth; i++) {
        if (draw_verticals[i]) {
            p += sprintf(p, "│   ");
        } else {
            p += sprintf(p, "    ");
        }
    }
    if (depth > 0) {
        p += sprintf(p, is_last ? "└── " : "├── ");
    }

    // Append node info
    if (view) {
        if (view->wid == -1) {
            sprintf(p, "%s (%sInternal)",
                    type, node->enabled ? "" : "disabled, ");
            wlr_log(WLR_ERROR, "%s", line);
        } else {
            sprintf(p, "%s (%sname=%s, wid=%d)",
                    type, node->enabled ? "" : "disabled, ", view->title, view->wid);
            wlr_log(WLR_ERROR, "%s", line);
        }
    } else if (depth == 2 && child_count > 1) {
        sprintf(p, "%s (%s%s)",
                type, layer_name, node->enabled ? "" : ", disabled");
        wlr_log(WLR_ERROR, "%s", line);
    }
    else {
        sprintf(p, "%s (%s)",
                type, node->enabled ? "" : "disabled");
        wlr_log(WLR_ERROR, "%s", line);
    }


    // Recurse into children if this is a tree node
    if (node->type == WLR_SCENE_NODE_TREE) {
        struct wlr_scene_tree *tree = wl_container_of(node, tree, node);
        size_t count = wl_list_length(&tree->children);
        size_t j = 0;

        struct wlr_scene_node *child;
        wl_list_for_each(child, &tree->children, link) {
            draw_verticals[depth] = !is_last; // draw vertical line at this level if not last
            print_scene_node(child, depth + 1, draw_verticals, j++, count,  hide_rects);
        }
    }
}

void qw_debug_dump_scene_graph(struct qw_server *server) {
    struct wlr_scene *scene = server->scene;
    wlr_log(WLR_ERROR, "Scene Graph Dump:");
    bool draw_verticals[64] = {1}; // Max depth = 64
    print_scene_node(&scene->tree.node, 0, draw_verticals, 0, 1, false);
}
