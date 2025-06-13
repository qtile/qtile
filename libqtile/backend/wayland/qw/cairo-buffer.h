#ifndef CAIRO_BUFFER_H
#define CAIR_BUFFER_H

#include <stdlib.h>

/* Creates a wlroots buffer backed by Cairo pixel data.
 * Parameters:
 * - width, height: dimensions of the buffer
 * - stride: number of bytes per row in data
 * - data: pointer to the pixel data (must remain valid while buffer exists)
 * Returns a pointer to the base wlr_buffer interface. */
struct wlr_buffer *cairo_buffer_create(int width, int height, size_t stride, void *data);

#endif // CAIRO_BUFFER_H
