#include "debug_util.h"
#include "server.h"
#include "wlr/util/log.h"
#include <wlr/types/wlr_scene.h>

static char *LAYER_NAMES[] = {[LAYER_BACKGROUND] = "LAYER_BACKGROUND",
                              [LAYER_BOTTOM] = "LAYER_BOTTOM",
                              [LAYER_KEEPBELOW] = "LAYER_KEEPBELOW",
                              [LAYER_LAYOUT] = "LAYER_LAYOUT",
                              [LAYER_KEEPABOVE] = "LAYER_KEEPABOVE",
                              [LAYER_MAX] = "LAYER_MAX",
                              [LAYER_FULLSCREEN] = "LAYER_FULLSCREEN",
                              [LAYER_BRINGTOFRONT] = "LAYER_BRINGTOFRONT",
                              [LAYER_TOP] = "LAYER_TOP",
                              [LAYER_OVERLAY] = "LAYER_OVERLAY",
                              [LAYER_END] = "LAYER_END"};

static char *NODE_NAMES[] = {[WLR_SCENE_NODE_TREE] = "tree",
                             [WLR_SCENE_NODE_RECT] = "rect",
                             [WLR_SCENE_NODE_BUFFER] = "buffer"};

struct scene_graph_dump_settings {
    const size_t max_depth;
    const size_t max_line_length;
    const int debug_level;
};

static int append(char **p, size_t *remaining, const char *fmt, ...) {
    va_list args;
    va_start(args, fmt);

    int n = vsnprintf(*p, *remaining, fmt, args);

    va_end(args);

    if (n < 0) {
        // vsnprintf error
        n = 0;
    } else if ((size_t)n >= *remaining) {
        // truncation
        wlr_log(WLR_ERROR, "Maximum line length exceeded. Output truncated");
        n = (*remaining > 0) ? (int)(*remaining - 1) : 0;
    }

    *p += n;
    *remaining -= n;

    return n;
}

static void print_scene_node(struct wlr_scene_node *node, size_t depth, bool *draw_verticals,
                             int child_i, int child_count,
                             struct scene_graph_dump_settings settings) {
    if (depth >= settings.max_depth) {
        wlr_log(WLR_ERROR, "Exceeded maximum tree depth: %zu", settings.max_depth);
        return;
    }

    bool is_last = false;
    if (child_i == child_count - 1) {
        is_last = true;
    }

    const char *type;
    if (node->type < 3) {
        type = NODE_NAMES[node->type];
    } else {
        type = "unknown";
    }

    const char *layer_name;
    if (child_i < LAYER_END + 1) {
        layer_name = LAYER_NAMES[child_i];
    } else {
        layer_name = "unknown";
    }

    struct qw_view *view = node->data;

    // Print visual indent tree structure
    char line[settings.max_line_length] = {};
    char *p = line;
    size_t remaining = sizeof(line);
    for (size_t i = 1; i < depth; i++) {
        if (draw_verticals[i]) {
            append(&p, &remaining, "|   ");
        } else {
            append(&p, &remaining, "    ");
        }
    }
    if (depth > 0) {
        append(&p, &remaining, "%s", is_last ? "└── " : "├── ");
    }

    // Append node info
    if (view) {
        append(&p, &remaining, "%s (%sname=%s, wid=%d)", type, node->enabled ? "" : "disabled, ",
               view->title, view->wid);
        wlr_log(settings.debug_level, "%s", line);
    } else if (depth == 2 && child_count > 1) {
        // A tree node corresponding to a named layer
        append(&p, &remaining, "%s (%s%s)", type, layer_name, node->enabled ? "" : ", disabled");
        wlr_log(settings.debug_level, "%s", line);
    } else {
        append(&p, &remaining, "%s (%s)", type, node->enabled ? "" : "disabled");
        wlr_log(settings.debug_level, "%s", line);
    }

    // Recurse into children if this is a tree node
    if (node->type == WLR_SCENE_NODE_TREE) {
        struct wlr_scene_tree *tree = wl_container_of(node, tree, node);
        size_t count = wl_list_length(&tree->children);
        size_t j = 0;

        struct wlr_scene_node *child;
        wl_list_for_each(child, &tree->children, link) {
            draw_verticals[depth] = !is_last; // draw vertical line at this level if not last
            print_scene_node(child, depth + 1, draw_verticals, j++, count, settings);
        }
    }
}

void qw_debug_dump_scene_graph(struct qw_server *server, int debug_level) {
    struct wlr_scene *scene = server->scene;
    wlr_log(debug_level, "Scene Graph Dump:");

    struct scene_graph_dump_settings settings = {
        .max_depth = 64, .max_line_length = 512, .debug_level = debug_level};
    bool draw_verticals[settings.max_depth] = {};

    print_scene_node(&scene->tree.node, 0, draw_verticals, 0, 1, settings);
}
