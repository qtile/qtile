#ifndef INTERNAL_VIEW_H
#define INTERNAL_VIEW_H

#include "view.h"
#include <cairo.h>
#include <wlr/types/wlr_scene.h>

struct qw_server;

struct qw_internal_view {
    struct qw_view base;
    struct wlr_scene_buffer *scene_buffer;
    struct wlr_buffer *buffer;
    cairo_surface_t *image_surface;
    double scale;
};

// Update the buffer's damaged region (x, y, width, height)
void qw_internal_view_set_buffer_with_damage(struct qw_internal_view *view, int x, int y, int width,
                                             int height);

// Get pointer to the base qw_view inside the internal view struct
struct qw_view *qw_internal_view_get_base(struct qw_internal_view *view);

// Create a new internal view with given geometry attached to server
struct qw_internal_view *qw_server_internal_view_new(struct qw_server *server, int x, int y,
                                                     int width, int height);

#endif /* INTERNAL_VIEW_H */
