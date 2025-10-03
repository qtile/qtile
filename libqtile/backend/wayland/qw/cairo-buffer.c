#include "cairo-buffer.h"
#include "wlr/util/log.h"
#include <drm_fourcc.h>
#include <wlr/interfaces/wlr_buffer.h>

#include "util.h"

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
    UNUSED(flags);

    struct cairo_buffer *buffer = wl_container_of(wlr_buffer, buffer, base);
    *data = buffer->data;
    *stride = buffer->stride;
    *format = DRM_FORMAT_ARGB8888;
    return true;
}

// Called after data access is done, no action needed here
static void handle_end_data_ptr_access(struct wlr_buffer *wlr_buffer) {
    UNUSED(wlr_buffer);
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

// Creates a wlr_buffer from a subregion of a cairo image surface
struct wlr_buffer *cairo_buffer_from_surface_region(cairo_surface_t *surface, int x, int y,
                                                    int width, int height) {
    if (cairo_surface_get_type(surface) != CAIRO_SURFACE_TYPE_IMAGE) {
        wlr_log(WLR_ERROR, "Cairo surface is not an image surface\n");
        return NULL;
    }

    cairo_surface_flush(surface);

    unsigned char *data = cairo_image_surface_get_data(surface);
    int surface_width = cairo_image_surface_get_width(surface);
    int surface_height = cairo_image_surface_get_height(surface);
    int stride = cairo_image_surface_get_stride(surface);

    if (x < 0 || y < 0 || x + width > surface_width || y + height > surface_height) {
        wlr_log(WLR_ERROR, "Requested subregion (%d,%d %dx%d) is out of bounds (%dx%d)\n", x, y,
                width, height, surface_width, surface_height);
        return NULL;
    }

    // Compute offset pointer for the subregion
    unsigned char *sub_data = data + y * stride + x * 4;

    return cairo_buffer_create(width, height, stride, sub_data);
}

// Given a surface, slice it into 4 fixed regions and create scene buffers
struct wlr_scene_buffer **create_scene_buffers_from_surface(struct wlr_scene_tree *scene,
                                                            cairo_surface_t *surface,
                                                            struct wlr_box *regions,
                                                            int num_regions) {
    struct wlr_scene_buffer **scene_buffers =
        calloc(num_regions, sizeof(struct wlr_scene_buffer *));
    if (!scene_buffers) {
        wlr_log(WLR_ERROR, "Failed to allocate scene buffer array\n");
        return NULL;
    }

    for (int i = 0; i < num_regions; ++i) {
        struct wlr_buffer *buf = cairo_buffer_from_surface_region(
            surface, regions[i].x, regions[i].y, regions[i].width, regions[i].height);

        if (!buf) {
            wlr_log(WLR_ERROR, "Failed to create buffer for region %d\n", i);
            continue;
        }

        scene_buffers[i] = wlr_scene_buffer_create(scene, buf);
        wlr_buffer_drop(buf); // Transfer ownership to the scene buffer
    }

    return scene_buffers;
}
