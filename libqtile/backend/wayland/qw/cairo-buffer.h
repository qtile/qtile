#ifndef CAIRO_BUFFER_H
#define CAIRO_BUFFER_H

#include "view.h"
#include <stdlib.h>

/* Creates a wlroots buffer backed by Cairo pixel data.
 * Parameters:
 * - width, height: dimensions of the buffer
 * - stride: number of bytes per row in data
 * - data: pointer to the pixel data (must remain valid while buffer exists)
 * Returns a pointer to the base wlr_buffer interface. */
struct wlr_buffer *cairo_buffer_create(int width, int height, size_t stride, void *data);

struct wlr_buffer *cairo_buffer_from_surface_region(cairo_surface_t *surface, int x, int y,
                                                    int width, int height);

// Creates a wlr_buffer from a subregion of a cairo image surface
struct wlr_buffer *cairo_buffer_from_surface_region(cairo_surface_t *surface, int x, int y,
                                                    int width, int height);

// Given a surface, slice it into 4 fixed regions and create scene buffers
struct wlr_scene_buffer **create_scene_buffers_from_surface(struct wlr_scene_tree *scene,
                                                            cairo_surface_t *surface,
                                                            struct wlr_box *regions,
                                                            int num_regions);

#endif // CAIRO_BUFFER_H
