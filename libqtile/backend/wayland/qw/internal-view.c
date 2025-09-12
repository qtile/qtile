#include "internal-view.h"
#include "cairo-buffer.h"
#include "pixman.h"
#include "server.h"
#include "view.h"
#include <stdlib.h>
#include <wlr/util/log.h>

// Create or recreate the internal view's buffer and associated Cairo surface
// If init is false, drop the old buffer before creating a new one
static void qw_internal_view_buffer_new(struct qw_internal_view *view, bool init) {
    if (!init) {
        wlr_buffer_drop(view->buffer);
    }

    // Create a new Cairo image surface with ARGB32 format
    view->image_surface =
        cairo_image_surface_create(CAIRO_FORMAT_ARGB32, view->base.width, view->base.height);

    unsigned char *data = cairo_image_surface_get_data(view->image_surface);
    size_t stride = cairo_image_surface_get_stride(view->image_surface);

    // Create a wlr_buffer backed by the Cairo surface's pixel data
    view->buffer = cairo_buffer_create(view->base.width, view->base.height, stride, data);

    if (!view->buffer) {
        wlr_log(WLR_ERROR, "failed allocating wlr_buffer for internal view");
    } else if (!init) {
        wlr_scene_buffer_set_buffer_with_damage(view->scene_buffer, view->buffer, NULL);
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
    pixman_region32_init_rect(&region, x, y, width, height);

    wlr_scene_buffer_set_buffer_with_damage(view->scene_buffer, view->buffer, &region);

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
                                   const struct qw_border *borders, int bn, int above) {
    struct qw_internal_view *view = (struct qw_internal_view *)self;
    if (above != 0) {
        qw_view_reparent(&view->base, LAYER_BRINGTOFRONT);
    }
    view->base.x = x;
    view->base.y = y;
    wlr_scene_node_set_position(&view->base.content_tree->node, x, y);

    // Resize and recreate buffer if size changed
    if (width != view->base.width || height != view->base.height) {
        view->base.width = width;
        view->base.height = height;
        qw_internal_view_buffer_new(view, false);
    }
}

// TODO: Focus logic for internal views (empty for now)
void qw_internal_view_focus(void *self, int above) {
    // TODO
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

static void qw_internal_view_kill(void *self) { qw_internal_view_hide(self); }

// Internal views don't have a PID, so return 0
static int qw_internal_view_get_pid(void *self) { return 0; }

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
        .bn = 0,
        .state = NOT_FLOATING,
        .wid = -1, // Window ID, to be set by compositor
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

    // Create the initial buffer and disable the scene node by default
    qw_internal_view_buffer_new(view, true);
    wlr_scene_node_set_enabled(&view->base.content_tree->node, false);
    wlr_scene_node_set_position(&view->base.content_tree->node, x, y);

    // Create the scene buffer node for rendering the buffer
    view->scene_buffer = wlr_scene_buffer_create(view->base.content_tree, view->buffer);
    return view;
}
