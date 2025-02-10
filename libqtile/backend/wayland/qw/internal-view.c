#include "cairo-buffer.h"
#include "internal-view.h"
#include "pixman.h"
#include "server.h"
#include "view.h"
#include <stdlib.h>
#include <wlr/util/log.h>

static void qw_internal_view_buffer_new(struct qw_internal_view *view, bool init) {
    if (!init) {
        wlr_buffer_drop(view->buffer);
    }

    view->image_surface =
        cairo_image_surface_create(CAIRO_FORMAT_ARGB32, view->base.width, view->base.height);
    unsigned char *data = cairo_image_surface_get_data(view->image_surface);
    size_t stride = cairo_image_surface_get_stride(view->image_surface);
    view->buffer = cairo_buffer_create(view->base.width, view->base.height, stride, data);
    if (!view->buffer) {
        wlr_log(WLR_ERROR, "failed allocating wlr_buffer for internal view");
    } else if (!init) {
        wlr_scene_buffer_set_buffer_with_damage(view->scene_buffer, view->buffer, NULL);
    }
}

void qw_internal_view_set_buffer_with_damage(struct qw_internal_view *view, int x, int y, int width,
                                             int height) {
    if (!view->scene_buffer || !view->buffer) {
        return;
    }
    pixman_region32_t region;
    pixman_region32_init_rect(&region, x, y, width, height);
    wlr_scene_buffer_set_buffer_with_damage(view->scene_buffer, view->buffer, &region);
    pixman_region32_fini(&region);
}

static struct wlr_scene_node *qw_internal_view_get_tree_node(void *self) {
    struct qw_internal_view *view = (struct qw_internal_view *)self;
    if (!view->scene_buffer) {
        return NULL;
    }
    return &view->scene_buffer->node;
}

static void qw_internal_view_bring_to_front(void *self) {
    struct qw_internal_view *view = (struct qw_internal_view *)self;
    wlr_scene_node_raise_to_top(&view->base.content_tree->node);
}

static void qw_internal_view_place(void *self, int x, int y, int width, int height, int bw,
                                   float (*bc)[4], int bn, int above) {
    struct qw_internal_view *view = (struct qw_internal_view *)self;
    if (above != 0) {
        qw_internal_view_bring_to_front(view);
    }
    view->base.x = x;
    view->base.y = y;
    wlr_scene_node_set_position(&view->base.content_tree->node, x, y);

    if (width != view->base.width || height != view->base.height) {
        view->base.width = width;
        view->base.height = height;
        qw_internal_view_buffer_new(view, false);
    }
}

void qw_internal_view_focus(void *self, int above) {
    // TODO
}

static void qw_internal_view_hide(void *self) {
    struct qw_internal_view *view = (struct qw_internal_view *)self;
    wlr_scene_node_set_enabled(&view->base.content_tree->node, false);
}

static void qw_internal_view_unhide(void *self) {
    struct qw_internal_view *view = (struct qw_internal_view *)self;
    wlr_scene_node_set_enabled(&view->base.content_tree->node, true);
}

static void qw_internal_view_kill(void *self) { qw_internal_view_hide(self); }

// internal views have no PID
static int qw_internal_view_get_pid(void *self) { return 0; }

struct qw_view *qw_internal_view_get_base(struct qw_internal_view *view) { return &view->base; }

struct qw_internal_view *qw_server_internal_view_new(struct qw_server *server, int x, int y,
                                                     int width, int height) {
    struct qw_internal_view *view = calloc(1, sizeof(*view));
    if (!view) {
        wlr_log(WLR_ERROR, "failed to create qw_internal_view struct");
        return NULL;
    }
    struct qw_view base = {
        .x = x,
        .y = y,
        .width = width,
        .height = height,
        .bn = 0,
        .state = NOT_FLOATING,
        // will be filled in by qtile
        .wid = -1,
        .content_tree = wlr_scene_tree_create(&server->scene->tree),
        .get_tree_node = qw_internal_view_get_tree_node,
        .place = qw_internal_view_place,
        .focus = qw_internal_view_focus,
        .get_pid = qw_internal_view_get_pid,
        .bring_to_front = qw_internal_view_bring_to_front,
        .kill = qw_internal_view_kill,
        .hide = qw_internal_view_hide,
        .unhide = qw_internal_view_unhide,
    };
    view->base = base;
    view->server = server;
    qw_internal_view_buffer_new(view, true);
    wlr_scene_node_set_enabled(&view->base.content_tree->node, false);
    wlr_scene_node_set_position(&view->base.content_tree->node, x, y);
    view->scene_buffer = wlr_scene_buffer_create(view->base.content_tree, view->buffer);
    return view;
}
