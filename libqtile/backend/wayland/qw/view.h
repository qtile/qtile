#ifndef VIEW_H
#define VIEW_H

#include <wayland-server-core.h>
#include <wlr/types/wlr_scene.h>

// pretty much a copy of backend/base/window.py
// TODO: avoid this duplication
enum qw_view_state {
    NOT_FLOATING = 1,
    FLOATING = 2,
    MAXIMIZED = 3,
    FULLSCREEN = 4,
    TOP = 5,
    MINIMIZED = 6,
};

struct qw_view {
    int x;
    int y;
    int width;
    int height;
    int bn;
    enum qw_view_state state;
    int wid;
    struct wlr_scene_tree *content_tree;

    struct wlr_scene_node *(*get_tree_node)(void *self);
    void (*place)(void *self, int x, int y, int width, int height, int bw, float (*bc)[4], int bn,
                  int above);
    void (*focus)(void *self, int warp);
    void (*bring_to_front)(void *self);
    void (*kill)(void *self);
    void (*hide)(void *self);
    void (*unhide)(void *self);
    int (*get_pid)(void *self);

    // private data
    struct wlr_scene_rect *(*borders)[4];
};

void qw_view_cleanup_borders(struct qw_view *xdg_view);

void qw_view_paint_borders(struct qw_view *xdg_view, float (*colors)[4], int width, int n);

#endif /* VIEW_H */
