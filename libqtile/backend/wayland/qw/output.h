#ifndef OUTPUT_H
#define OUTPUT_H

#include <cairo/cairo.h>
#include <wayland-server-core.h>
#include <wlr/backend/headless.h>
#include <wlr/types/wlr_buffer.h>
#include <wlr/types/wlr_output.h>
#include <wlr/types/wlr_scene.h>

struct qw_server;

enum qw_wallpaper_mode;

struct qw_output_background_wallpaper {
    struct wlr_scene_buffer *buffer;
    cairo_surface_t *surface;
};

struct qw_output_background {
    enum qw_background_type {
        QW_BACKGROUND_COLOR_RECT,
        QW_BACKGROUND_WALLPAPER,
        QW_BACKGROUND_DESTROYED // only set after destroying backgrounds
    } type;

    union {
        struct wlr_scene_rect *color_rect;
        struct qw_output_background_wallpaper *wallpaper;
    };
};

struct qw_output {
    struct qw_server *server;
    struct wlr_scene_output *scene;
    struct wlr_output *wlr_output;
    int x;
    int y;

    struct wlr_box full_area;
    struct wlr_box area;

    // Private data
    struct wl_list link;
    struct wl_listener frame;
    struct wl_listener request_state;
    struct wl_listener destroy;
    struct wl_list layers[4];
    struct qw_output_background background;
};

void qw_output_arrange_layers(struct qw_output *output);

void qw_server_output_new(struct qw_server *server, struct wlr_output *wlr_output);

void qw_output_paint_wallpaper(struct qw_output *output, cairo_surface_t *source,
                               enum qw_wallpaper_mode mode);

void qw_output_paint_background_color(struct qw_output *output, float color[4]);

#endif /* OUTPUT_H */
