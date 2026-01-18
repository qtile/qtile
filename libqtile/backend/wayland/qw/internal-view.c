#include "internal-view.h"
#include "cairo-buffer.h"
#include "pixman.h"
#include "server.h"
#include "util.h"
#include "view.h"
#include <stdlib.h>
#include <wlr/util/log.h>

// Create or recreate the internal view's buffer and associated Cairo surface
// If init is false, drop the old buffer before creating a new one
//
// We scale the cairo surface (wayland/drawer.py) and buffer by its output (display) scale - since
// cairo largely uses vector drawing primitives, this produces a sharper result than letting wayland
// upscale for us. We need to set the destination size for wayland to correctly scale the buffer
static void qw_internal_view_buffer_new(struct qw_internal_view *view, bool init) {
    if (!init) {
        wlr_buffer_drop(view->buffer);
    }

    int scaled_width = (int)(view->base.width * view->scale);
    int scaled_height = (int)(view->base.height * view->scale);

    // Create a new Cairo image surface with ARGB32 format
    view->image_surface =
        cairo_image_surface_create(CAIRO_FORMAT_ARGB32, scaled_width, scaled_height);

    unsigned char *data = cairo_image_surface_get_data(view->image_surface);
    size_t stride = cairo_image_surface_get_stride(view->image_surface);

    // Create a wlr_buffer backed by the Cairo surface's pixel data
    view->buffer = cairo_buffer_create(scaled_width, scaled_height, stride, data);

    if (!view->buffer) {
        wlr_log(WLR_ERROR, "failed allocating wlr_buffer for internal view");
    } else if (!init) {
        wlr_scene_buffer_set_buffer_with_damage(view->scene_buffer, view->buffer, NULL);
        wlr_scene_buffer_set_dest_size(view->scene_buffer, view->base.width, view->base.height);
    }
}

// Update the scene buffer with damage in the specified rectangle region
void qw_internal_view_set_buffer_with_damage(struct qw_internal_view *view, int x, int y, int width,
                                             int height) {
    if (!view->scene_buffer || !view->buffer) {
        return;
    }

    // Initialize a pixman region covering the damage rectangle
    pixman_region32_t region;
    pixman_region32_init_rect(&region, (int)(x * view->scale), (int)(y * view->scale),
                              (int)(width * view->scale), (int)(height * view->scale));

    wlr_scene_buffer_set_buffer_with_damage(view->scene_buffer, view->buffer, &region);
    wlr_scene_buffer_set_dest_size(view->scene_buffer, view->base.width, view->base.height);

    // Clean up pixman region
    pixman_region32_fini(&region);
}

// Return the underlying scene node for this internal view
static struct wlr_scene_node *qw_internal_view_get_tree_node(void *self) {
    struct qw_internal_view *view = (struct qw_internal_view *)self;
    if (!view->scene_buffer) {
        return NULL;
    }
    return &view->scene_buffer->node;
}

// Place the internal view at a new position and resize if needed
// If 'above' is nonzero, bring the view to the front
static void qw_internal_view_place(void *self, int x, int y, int width, int height,
                                   const struct qw_border *borders, int border_count, int above) {
    UNUSED(borders);
    UNUSED(border_count);

    struct qw_internal_view *view = (struct qw_internal_view *)self;
    if (above != 0) {
        qw_view_reparent(&view->base, LAYER_BRINGTOFRONT);
    }
    view->base.x = x;
    view->base.y = y;
    wlr_scene_node_set_position(&view->base.content_tree->node, x, y);

    // Update scale as view may have moved
    double prev_scale = view->scale;
    struct wlr_output *output = wlr_output_layout_output_at(view->base.server->output_layout, x, y);
    if (output != NULL) {
        view->scale = output->scale;
    }

    // Resize and recreate buffer if size or scale has changed
    if (width != view->base.width || height != view->base.height || view->scale != prev_scale) {
        view->base.width = width;
        view->base.height = height;
        qw_internal_view_buffer_new(view, false);
    }
}

// TODO: Focus logic for internal views (empty for now)
void qw_internal_view_focus(void *self, int above) {
    UNUSED(self);
    UNUSED(above);
}

// Hide this internal view by disabling its scene node
static void qw_internal_view_hide(void *self) {
    struct qw_internal_view *view = (struct qw_internal_view *)self;
    wlr_scene_node_set_enabled(&view->base.content_tree->node, false);
}

// Unhide this internal view by enabling its scene node
static void qw_internal_view_unhide(void *self) {
    struct qw_internal_view *view = (struct qw_internal_view *)self;
    wlr_scene_node_set_enabled(&view->base.content_tree->node, true);
}

static void qw_internal_view_kill(void *self) {
    struct qw_internal_view *view = (struct qw_internal_view *)self;
    cairo_surface_destroy(view->image_surface);
    view->image_surface = NULL;
    wlr_buffer_drop(view->buffer);
    wlr_scene_node_destroy(&view->base.content_tree->node);
    free(view);
}

// Internal views don't have a PID, so return 0
static int qw_internal_view_get_pid(void *self) {
    UNUSED(self);
    return 0;
}

// Get pointer to the base view struct inside the internal view
struct qw_view *qw_internal_view_get_base(struct qw_internal_view *view) { return &view->base; }

// Allocate and initialize a new internal view with the specified geometry
struct qw_internal_view *qw_server_internal_view_new(struct qw_server *server, int x, int y,
                                                     int width, int height) {
    struct qw_internal_view *view = calloc(1, sizeof(*view));
    if (!view) {
        wlr_log(WLR_ERROR, "failed to create qw_internal_view struct");
        return NULL;
    }

    // Initialize the base qw_view with provided geometry and callbacks
    struct qw_view base = {
        .server = server,
        .layer = LAYER_LAYOUT,
        .x = x,
        .y = y,
        .width = width,
        .height = height,
        .border_count = 0,
        .state = NOT_FLOATING,
        .wid = -1, // Window ID, to be set by compositor
        .skip_taskbar = true,
        .content_tree = wlr_scene_tree_create(&server->scene->tree),
        .get_tree_node = qw_internal_view_get_tree_node,
        .place = qw_internal_view_place,
        .focus = qw_internal_view_focus,
        .get_pid = qw_internal_view_get_pid,
        .kill = qw_internal_view_kill,
        .hide = qw_internal_view_hide,
        .unhide = qw_internal_view_unhide,
    };
    view->base = base;
    view->base.content_tree->node.data = view;
    view->base.view_type = QW_VIEW_INTERNAL;
    view->scale = 1.0;
    struct wlr_output *output = wlr_output_layout_output_at(server->output_layout, x, y);
    if (output != NULL) {
        view->scale = output->scale;
    }

    // Create the initial buffer and disable the scene node by default
    qw_internal_view_buffer_new(view, true);
    wlr_scene_node_set_enabled(&view->base.content_tree->node, false);
    wlr_scene_node_set_position(&view->base.content_tree->node, x, y);

    // Create the scene buffer node for rendering the buffer
    view->scene_buffer = wlr_scene_buffer_create(view->base.content_tree, view->buffer);
    return view;
}
