#ifndef INTERNAL_VIEW_H
#define INTERNAL_VIEW_H

#include "view.h"
#include <cairo.h>
#include <wlr/types/wlr_scene.h>

struct qw_server;

struct qw_internal_view {
    struct qw_view base;
    struct qw_server *server;
    struct wlr_scene_buffer *scene_buffer;
    struct wlr_buffer *buffer;
    cairo_surface_t *image_surface;
};

void qw_internal_view_set_buffer_with_damage(struct qw_internal_view *view, int x, int y, int width,
                                             int height);
struct qw_view *qw_internal_view_get_base(struct qw_internal_view *view);

struct qw_internal_view *qw_server_internal_view_new(struct qw_server *server, int x, int y,
                                                     int width, int height);

#endif /* INTERNAL_VIEW_H */
