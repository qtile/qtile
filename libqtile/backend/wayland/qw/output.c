#include "output.h"
#include "cairo-buffer.h"
#include "layer-view.h"
#include "proto/wlr-layer-shell-unstable-v1-protocol.h"
#include "server.h"
#include "session-lock.h"
#include "util.h"
#include <stdio.h>
#include <stdlib.h>

static void qw_output_handle_frame(struct wl_listener *listener, void *data) {
    UNUSED(data);

    // Called when the output is ready to display a new frame
    struct qw_output *output = wl_container_of(listener, output, frame);
    struct wlr_scene *scene = output->server->scene;

    struct wlr_scene_output *scene_output = wlr_scene_get_scene_output(scene, output->wlr_output);

    wlr_scene_output_commit(scene_output, NULL);

    // Send a frame done event with the current time
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    wlr_scene_output_send_frame_done(scene_output, &now);
}

static void qw_output_handle_destroy(struct wl_listener *listener, void *data) {
    UNUSED(data);
    struct qw_output *output = wl_container_of(listener, output, destroy);

    wl_list_remove(&output->frame.link);
    wl_list_remove(&output->request_state.link);
    wl_list_remove(&output->destroy.link);
    wl_list_remove(&output->link);
    free(output);
}

static void qw_output_handle_request_state(struct wl_listener *listener, void *data) {
    // Handle client requests to change the output state (mode, enabled, etc.)
    struct qw_output *output = wl_container_of(listener, output, request_state);
    const struct wlr_output_event_request_state *event = data;
    wlr_output_commit_state(output->wlr_output, event->state);
}

void qw_output_arrange_layer(struct qw_output *output, struct wl_list *list,
                             struct wlr_box *usable_area, int exclusive) {
    struct wlr_box full_area = output->full_area;

    struct qw_layer_view *layer_view;
    wl_list_for_each(layer_view, list, link) {
        struct wlr_layer_surface_v1 *layer_surface = layer_view->surface;
        if (!layer_surface)
            continue;

        if (!layer_surface->initialized)
            continue;

        if (exclusive != (layer_surface->current.exclusive_zone > 0))
            continue;

        wlr_scene_layer_surface_v1_configure(layer_view->scene, &full_area, usable_area);
        wlr_scene_node_set_position(&layer_view->popups->node, layer_view->scene->tree->node.x,
                                    layer_view->scene->tree->node.y);
    }
}

void qw_output_arrange_layers(struct qw_output *output) {
    int i;
    struct wlr_box usable_area = output->full_area;
    if (!output->wlr_output->enabled || output->disabled_by_opm) {
        return;
    }

    for (i = 3; i >= 0; i--) {
        qw_output_arrange_layer(output, &output->layers[i], &usable_area, 1);
    }

    if (!wlr_box_equal(&usable_area, &output->area)) {
        output->area = usable_area;
        output->server->on_screen_reserve_space_cb(output, output->server->cb_data);
    }

    for (i = 3; i >= 0; i--) {
        qw_output_arrange_layer(output, &output->layers[i], &usable_area, 0);
    }

    uint32_t layers_above_shell[] = {
        ZWLR_LAYER_SHELL_V1_LAYER_OVERLAY,
        ZWLR_LAYER_SHELL_V1_LAYER_TOP,
    };

    for (i = 0; i < 2; i++) {
        struct qw_layer_view *layer_view;
        wl_list_for_each_reverse(layer_view, &output->layers[layers_above_shell[i]], link) {
            // TODO: locked
            if (!layer_view->surface->current.keyboard_interactive || !layer_view->mapped)
                continue;

            if (layer_view->surface->current.keyboard_interactive ==
                ZWLR_LAYER_SURFACE_V1_KEYBOARD_INTERACTIVITY_EXCLUSIVE) {
                layer_view->server->exclusive_layer = layer_view;
                qw_layer_view_focus(layer_view);
                return;
            }

            if (layer_view->server->exclusive_layer == layer_view) {
                // This window previously had exclusive focus, but no longer wants it.
                layer_view->server->exclusive_layer = NULL;
            }
        }
    }
}

void qw_server_output_new(struct qw_server *server, struct wlr_output *wlr_output) {
    // Allocate and initialize a new output object
    struct qw_output *output = calloc(1, sizeof(*output));
    if (!output) {
        wlr_log(WLR_ERROR, "failed to create qw_output struct");
        return;
    }

    wlr_output_init_render(wlr_output, server->allocator, server->renderer);

    output->scene = wlr_scene_output_create(server->scene, wlr_output);

    // Setup initial output state and enable the output
    struct wlr_output_state state;
    wlr_output_state_init(&state);
    wlr_output_state_set_enabled(&state, true);

    // During tests, we want to fix the geometry of the 1 or 2 outputs
    if (getenv("PYTEST_CURRENT_TEST") && wlr_output_is_headless(wlr_output)) {
        if (wl_list_empty(&server->outputs)) {
            wlr_output_state_set_custom_mode(&state, 800, 600, 0);
        } else {
            wlr_output_state_set_custom_mode(&state, 640, 480, 0);
        }
    } else {
        struct wlr_output_mode *mode = wlr_output_preferred_mode(wlr_output);
        if (mode) {
            wlr_output_state_set_mode(&state, mode);
        }
    }

    wlr_output_commit_state(wlr_output, &state);
    wlr_output_state_finish(&state);

    wlr_output->data = output;
    output->wlr_output = wlr_output;
    output->server = server;

    // Store references to the wlr_output and server
    for (int i = 0; i < 4; i++)
        wl_list_init(&output->layers[i]);

    qw_session_lock_output_create_blanking_rects(output);

    // Setup listeners for frame, request_state, and destroy events
    output->frame.notify = qw_output_handle_frame;
    wl_signal_add(&wlr_output->events.frame, &output->frame);

    output->request_state.notify = qw_output_handle_request_state;
    wl_signal_add(&wlr_output->events.request_state, &output->request_state);

    output->destroy.notify = qw_output_handle_destroy;
    wl_signal_add(&wlr_output->events.destroy, &output->destroy);

    // Insert output at end of list
    wl_list_insert(server->outputs.prev, &output->link);

    // Create black background for FULLSCREEN layer and disable it
    float black[4] = {0, 0, 0, 1.0};
    output->fullscreen_background =
        wlr_scene_rect_create(server->scene_windows_layers[LAYER_FULLSCREEN], 0, 0, black);
    wlr_scene_node_set_enabled(&output->fullscreen_background->node, false);

    // Add the output to the output layout automatically and to the scene layout
    struct wlr_output_layout_output *l_output =
        wlr_output_layout_add_auto(server->output_layout, wlr_output);
    wlr_scene_output_layout_add_output(server->scene_layout, l_output, output->scene);
}

void qw_output_background_destroy(struct qw_output *output) {
    // Destroy the color scene_rect if it exists
    if (output->background.type == QW_BACKGROUND_COLOR_RECT) {
        struct wlr_scene_rect *color_rect = output->background.color_rect;
        if (color_rect != NULL) {
            wlr_scene_node_destroy(&color_rect->node);
            output->background.color_rect = NULL;
        }
    }

    // Destroy wallpaper resources if wallpaper exists
    else if (output->background.type == QW_BACKGROUND_WALLPAPER) {
        if (output->background.wallpaper != NULL) {
            struct wlr_scene_buffer *buffer = output->background.wallpaper->buffer;
            if (buffer != NULL) {
                wlr_scene_node_destroy(&buffer->node);
                output->background.wallpaper->buffer = NULL;
            }

            cairo_surface_t *surface = output->background.wallpaper->surface;
            if (surface != NULL) {
                cairo_surface_destroy(surface);
                output->background.wallpaper->surface = NULL;
            }

            free(output->background.wallpaper);
            output->background.wallpaper = NULL;
        }
    }

    // Reset type to indicate no background
    output->background.type = QW_BACKGROUND_DESTROYED;
}

void qw_output_toggle_fullscreen_background(struct qw_output *output, bool enabled) {
    if (output->fullscreen_background != NULL) {
        wlr_scene_node_set_enabled(&output->fullscreen_background->node, enabled);
        wlr_scene_node_lower_to_bottom(&output->fullscreen_background->node);
    }
}

void qw_output_paint_wallpaper(struct qw_output *output, cairo_surface_t *source,
                               enum qw_wallpaper_mode mode) {
    // Note: libqtile.backend.wayland.core.Painter owns the reference to the source surface
    // so we don't destroy it in this function.

    // Remove previous background
    qw_output_background_destroy(output);

    // Get dimensions of source image and screen
    int img_width = cairo_image_surface_get_width(source);
    int img_height = cairo_image_surface_get_height(source);
    int o_width, o_height;
    wlr_output_effective_resolution(output->wlr_output, &o_width, &o_height);

    // Calculate x and y scaling factors
    double scale_x = (double)o_width / img_width;
    double scale_y = (double)o_height / img_height;

    // Create a new surface sized to output size
    cairo_surface_t *wallpaper_surface =
        cairo_image_surface_create(CAIRO_FORMAT_ARGB32, o_width, o_height);
    if (cairo_surface_status(wallpaper_surface) != CAIRO_STATUS_SUCCESS) {
        wlr_log(WLR_ERROR, "Failed to create Cairo image surface for wallpaper.");
        cairo_surface_destroy(wallpaper_surface);
        return;
    }

    // Create context
    cairo_t *cr = cairo_create(wallpaper_surface);
    if (cairo_status(cr) != CAIRO_STATUS_SUCCESS) {
        wlr_log(WLR_ERROR, "Failed to create Cairo context for wallpaper.");
        cairo_destroy(cr);
        cairo_surface_destroy(wallpaper_surface);
        return;
    }

    // Limit drawing to the screen area
    cairo_rectangle(cr, 0, 0, o_width, o_height);
    cairo_clip(cr);

    int t_x;
    int t_y;

    switch (mode) {

    // We don't touch the image and draw it at 0, 0
    case WALLPAPER_MODE_ORIGINAL:
        break;

    // Fill screen as best as possible while preserving aspect ratio
    // Image is centered on screen
    case WALLPAPER_MODE_FILL:
        if ((scale_x * img_height) > o_height) {
            cairo_translate(cr, 0, -(img_height * scale_x - o_height) / 2);
            cairo_scale(cr, scale_x, scale_x);
        } else {
            cairo_translate(cr, -(img_width * scale_y - o_width) / 2, 0);
            cairo_scale(cr, scale_y, scale_y);
        }
        break;

    // Scale image to screen - don't preserve aspect ratio
    case WALLPAPER_MODE_STRETCH:
        cairo_scale(cr, scale_x, scale_y);
        break;

    // Center image on screen but don't scale image
    case WALLPAPER_MODE_CENTER:
        t_x = (o_width - img_width) / 2;
        t_y = (o_height - img_height) / 2;
        cairo_translate(cr, t_x, t_y);
        break;

    default:
        wlr_log(WLR_ERROR, "Unexpected wallpaper mode.");
        cairo_destroy(cr);
        cairo_surface_destroy(wallpaper_surface);
        return;
    }

    // Paint the modified image to our wallpaper image
    cairo_set_source_surface(cr, source, 0, 0);
    cairo_paint(cr);

    // Get data and stride from scaled surface
    unsigned char *data = cairo_image_surface_get_data(wallpaper_surface);
    int stride = cairo_image_surface_get_stride(wallpaper_surface);

    // Create wlr_buffer from scaled surface data
    struct wlr_buffer *buffer = cairo_buffer_create(o_width, o_height, stride, data);
    if (buffer == NULL) {
        wlr_log(WLR_ERROR, "Failed to create wlr_buffer from scaled surface");
        cairo_surface_destroy(wallpaper_surface);
        return;
    }

    struct wlr_scene_buffer *scene_buf =
        wlr_scene_buffer_create(output->server->scene_wallpaper_tree, buffer);

    if (output->background.wallpaper == NULL) {
        output->background.wallpaper = calloc(1, sizeof(struct qw_output_background_wallpaper));
        if (!output->background.wallpaper) {
            wlr_log(WLR_ERROR, "Failed to allocate memory for wallpaper image.");
            wlr_buffer_drop(buffer);
            cairo_surface_destroy(wallpaper_surface);
            return;
        }
    }

    // Save references to scene buffer and wallpaper so we can destroy them later
    output->background.wallpaper->buffer = scene_buf;
    output->background.wallpaper->surface = wallpaper_surface;
    output->background.type = QW_BACKGROUND_WALLPAPER;

    // Tidy up objects
    // scene_buffer takes its own ref to the buffer, drop ours
    wlr_buffer_drop(buffer);

    // Destroy unneeded cairo objects
    cairo_destroy(cr);

    // Place the wallpaper
    wlr_scene_node_set_position(&scene_buf->node, output->x, output->y);
}

void qw_output_paint_background_color(struct qw_output *output, float color[4]) {
    // Remove previous background
    qw_output_background_destroy(output);

    // Get screen dimensions
    int o_width, o_height;
    wlr_output_effective_resolution(output->wlr_output, &o_width, &o_height);

    // Create the scene rect
    struct wlr_scene_rect *rect =
        wlr_scene_rect_create(output->server->scene_wallpaper_tree, o_width, o_height, color);
    if (rect == NULL) {
        wlr_log(WLR_ERROR, "Failed to create scene_rect for background.");
    }

    // Save reference to scene rect so we can destroy it later
    output->background.color_rect = rect;
    output->background.type = QW_BACKGROUND_COLOR_RECT;

    // Place the background
    wlr_scene_node_set_position(&rect->node, output->x, output->y);
}
