#include "cairo-buffer.h"

#include <drm_fourcc.h>
#include <wlr/interfaces/wlr_buffer.h>

struct cairo_buffer {
    struct wlr_buffer base;
    void *data;
    size_t stride;
};

// Called when the buffer is destroyed, frees our cairo_buffer wrapper
static void handle_destroy(struct wlr_buffer *wlr_buffer) {
    struct cairo_buffer *buffer = wl_container_of(wlr_buffer, buffer, base);
    free(buffer);
}

// Called when wlroots wants access to the raw pixel data
// Provides pointer, stride, and pixel format
static bool handle_begin_data_ptr_access(struct wlr_buffer *wlr_buffer, uint32_t flags, void **data,
                                         uint32_t *format, size_t *stride) {
    struct cairo_buffer *buffer = wl_container_of(wlr_buffer, buffer, base);
    *data = buffer->data;
    *stride = buffer->stride;
    *format = DRM_FORMAT_ARGB8888;
    return true;
}

// Called after data access is done, no action needed here
static void handle_end_data_ptr_access(struct wlr_buffer *wlr_buffer) {
    // This space is intentionally left blank
}

// wlroots buffer implementation with function pointers to our handlers
static const struct wlr_buffer_impl cairo_buffer_impl = {
    .destroy = handle_destroy,
    .begin_data_ptr_access = handle_begin_data_ptr_access,
    .end_data_ptr_access = handle_end_data_ptr_access,
};

// Create a new cairo_buffer wrapping given pixel data and stride
// Returns a pointer to the base wlroots buffer interface
struct wlr_buffer *cairo_buffer_create(int width, int height, size_t stride, void *data) {
    struct cairo_buffer *cairo_buffer = calloc(1, sizeof(struct cairo_buffer));
    if (cairo_buffer == NULL) {
        return NULL;
    }

    wlr_buffer_init(&cairo_buffer->base, &cairo_buffer_impl, width, height);
    cairo_buffer->data = data;
    cairo_buffer->stride = stride;
    return &cairo_buffer->base;
}
