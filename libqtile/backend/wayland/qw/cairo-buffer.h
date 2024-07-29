#ifndef CAIRO_BUFFER_H
#define CAIR_BUFFER_H

#include <stdlib.h>

struct wlr_buffer *cairo_buffer_create(int width, int height, size_t stride, void *data);

#endif // CAIRO_BUFFER_H
