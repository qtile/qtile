#ifndef SERVER_H
#define SERVER_H

#include <assert.h>
#include <getopt.h>
#include <stdbool.h>
#include <unistd.h>

#include <cairo.h>
#include <wayland-server-core.h>
#include <wlr/backend.h>
#include <wlr/backend/session.h>
#include <wlr/config.h>
#include <wlr/render/allocator.h>
#include <wlr/render/wlr_renderer.h>
#include <wlr/types/wlr_alpha_modifier_v1.h>
#include <wlr/types/wlr_compositor.h>
#include <wlr/types/wlr_data_control_v1.h>
#include <wlr/types/wlr_data_device.h>
#include <wlr/types/wlr_export_dmabuf_v1.h>
#include <wlr/types/wlr_foreign_toplevel_management_v1.h>
#include <wlr/types/wlr_fractional_scale_v1.h>
#include <wlr/types/wlr_gamma_control_v1.h>
#include <wlr/types/wlr_input_device.h>
#include <wlr/types/wlr_keyboard.h>
#include <wlr/types/wlr_layer_shell_v1.h>
#include <wlr/types/wlr_output.h>
#include <wlr/types/wlr_output_layout.h>
#include <wlr/types/wlr_pointer.h>
#include <wlr/types/wlr_presentation_time.h>
#include <wlr/types/wlr_primary_selection.h>
#include <wlr/types/wlr_primary_selection_v1.h>
#include <wlr/types/wlr_scene.h>
#include <wlr/types/wlr_screencopy_v1.h>
#include <wlr/types/wlr_seat.h>
#include <wlr/types/wlr_single_pixel_buffer_v1.h>
#include <wlr/types/wlr_subcompositor.h>
#include <wlr/types/wlr_viewporter.h>
#include <wlr/types/wlr_xdg_activation_v1.h>
#include <wlr/types/wlr_xdg_shell.h>
#include <wlr/util/log.h>
#include <xkbcommon/xkbcommon.h>
#if WLR_HAS_XWAYLAND
#include <wlr/xwayland/xwayland.h>
#endif
#include "layer-view.h"

// Callback typedefs for input and view events

// Keyboard key event callback: keysym, modifier mask, and user data
typedef int (*keyboard_key_cb_t)(xkb_keysym_t keysym, uint32_t mask, void *userdata);

// Forward declaration of view struct
struct qw_view;

// Callbacks for managing views
typedef void (*unmanage_view_cb_t)(struct qw_view *view, void *userdata);
typedef void (*manage_view_cb_t)(struct qw_view *view, void *userdata);

// Cursor motion event callback: relative x, y and user data
typedef void (*cursor_motion_cb_t)(int x, int y, void *userdata);

// Cursor button event callback: button, modifiers, pressed state, position, user data
typedef int (*cursor_button_cb_t)(int button, uint32_t mask, bool pressed, int x, int y,
                                  void *userdata);

// Output dimensions callback: x, y, width, height of output
typedef void (*output_dims_cb_t)(int x, int y, int width, int height);

// Query tree node wid callback
typedef void (*node_wid_cb_t)(int wid);

// Callback for when screen configuration changes
typedef void (*on_screen_change_cb_t)(void *userdata);

// Forward declaration of output struct
struct qw_output;

// Callback for when the screen reserves space
typedef void (*on_screen_reserve_space_cb_t)(struct qw_output *output, void *userdata);

// Forward declaration of input device struct
struct qw_input_device;

// Iterate input devices callback
typedef void (*input_device_cb_t)(struct qw_input_device *input_device, const char *name, int type,
                                  int vendor, int product);

// Callback for when an input device is added
typedef void (*on_input_device_added_cb_t)(void *userdata);

// Callback to focus current window (if available). Returns success
typedef bool (*focus_current_window_cb_t)(void *userdata);

enum {
    LAYER_BACKGROUND,   // background, layer shell
    LAYER_BOTTOM,       // bottom, layer shell
    LAYER_KEEPBELOW,    // windows that are marked 'keep below'
    LAYER_LAYOUT,       // the normal tiled windows in the layout
    LAYER_KEEPABOVE,    // windows that are marked 'keep above', including floating windows if
                        // 'floats_kept_above = True'
    LAYER_MAX,          // windows that are maximized
    LAYER_FULLSCREEN,   // windows that are fullscreen
    LAYER_BRINGTOFRONT, // windows that are marked bring to front
    LAYER_TOP,          // top, layer shell
    LAYER_OVERLAY,      // overlay, layer shell
    LAYER_END           // keeping track of the end
};

// Mode for drawing wallpaper
enum qw_wallpaper_mode {
    WALLPAPER_MODE_ORIGINAL, // Don't modify wallpaper
    WALLPAPER_MODE_STRETCH,  // Fit to screen - don't preserve aspect ratio
    WALLPAPER_MODE_FILL,     // Resize to screen - preserve aspect ratio
    WALLPAPER_MODE_CENTER,   // Don't resize - place in centre of screen
};

struct scene_node_info {
    char *name;
    char *type;
    bool enabled;
    int x;
    int y;
    int view_wid;
};

// Callback for building scene graph in python
typedef void (*node_info_cb_t)(uintptr_t node_ptr, uintptr_t parent_ptr,
                               struct scene_node_info info);

typedef void (*view_urgent_cb_t)(struct qw_view *view, void *userdata);

// Main server struct containing Wayland and wlroots state and user callbacks
struct qw_server {
    // Public API
    const char *socket;
    keyboard_key_cb_t keyboard_key_cb;
    manage_view_cb_t manage_view_cb;
    unmanage_view_cb_t unmanage_view_cb;
    cursor_motion_cb_t cursor_motion_cb;
    cursor_button_cb_t cursor_button_cb;
    on_screen_change_cb_t on_screen_change_cb;
    on_screen_reserve_space_cb_t on_screen_reserve_space_cb;
    view_urgent_cb_t view_urgent_cb;
    on_input_device_added_cb_t on_input_device_added_cb;
    focus_current_window_cb_t focus_current_window_cb;
    void *view_urgent_cb_data;
    void *cb_data;
    struct qw_layer_view *exclusive_layer;

    // Private data
    struct wl_event_loop *event_loop;
    struct wlr_compositor *compositor;
    struct wl_display *display;
    struct wlr_backend *backend;
    struct wlr_session *session;
    struct wlr_renderer *renderer;
    struct wlr_allocator *allocator;
    struct wlr_scene *scene;
    struct wlr_scene_tree *scene_wallpaper_tree;
    struct wlr_scene_tree *scene_windows_tree;
    struct wlr_scene_tree *scene_windows_layers[LAYER_END];
    // TODO: drag icon tree
    struct wlr_scene_output_layout *scene_layout;
    struct wlr_output_layout *output_layout;
    struct wl_list outputs;
    struct wlr_output *current_output;
    struct wlr_output_manager_v1 *output_mgr;
    struct wl_listener output_manager_apply;
    struct wl_listener output_manager_test;
    struct wl_listener new_output;
    struct wl_listener output_layout_change;
    struct wl_listener new_input;
    struct wl_listener renderer_lost;
    struct wl_list keyboards;
    struct wl_list input_devices;
    struct wlr_seat *seat;
    struct qw_cursor *cursor;
    struct wlr_xdg_shell *xdg_shell;
    struct wlr_layer_shell_v1 *layer_shell;
    struct wlr_xdg_decoration_manager_v1 *xdg_decoration_mgr;
    struct wlr_xdg_activation_v1 *activation;
    struct wl_listener new_xdg_toplevel;
    struct wl_listener new_decoration;
    struct wl_listener new_layer_surface;
    struct wl_listener request_cursor;
    struct wl_listener request_set_selection;
    struct wl_listener request_set_primary_selection;
    struct wlr_foreign_toplevel_manager_v1 *ftl_mgr;
#if WLR_HAS_XWAYLAND
    struct wlr_xwayland *xwayland;
    struct wl_listener new_xwayland_surface;
#endif
    struct wl_listener request_activate;
    struct wl_listener new_token;
};

// Utility functions exposed by the server API

// Get symbolic key name string from a key code
const char *qw_server_get_sym_from_code(struct qw_server *server, int code);

// Poll for server events (non-blocking)
void qw_server_poll(struct qw_server *server);

// Clean up and free server resources
void qw_server_finalize(struct qw_server *server);

// Start the server event loop (blocking)
void qw_server_start(struct qw_server *server);

// Get file descriptor of the event loop (for integration with other event loops)
int qw_server_get_event_loop_fd(struct qw_server *server);

// Iterate over outputs and call the provided callback with their geometry
void qw_server_loop_output_dims(struct qw_server *server, output_dims_cb_t cb);

// Create and initialize a new server instance (allocates memory)
struct qw_server *qw_server_create(void);

// Find the view at a given layout coordinate (lx, ly)
// If a surface pointer is provided, it will be set to the surface under the point
// sx and sy are surface-local coordinates of the point
struct qw_view *qw_server_view_at(struct qw_server *server, double lx, double ly,
                                  struct wlr_surface **surface, double *sx, double *sy);
void qw_server_keyboard_clear_focus(struct qw_server *server);

// Change virtual terminal
bool qw_server_change_vt(struct qw_server *server, int vt);

struct qw_cursor *qw_server_get_cursor(struct qw_server *server);

void qw_server_loop_visible_views(struct qw_server *server, node_wid_cb_t);

void qw_server_set_keymap(struct qw_server *server, const char *layout, const char *options,
                          const char *variant);
const char *qw_server_xwayland_display_name(struct qw_server *server);

void qw_server_paint_wallpaper(struct qw_server *server, int x, int y, cairo_surface_t *source,
                               enum qw_wallpaper_mode mode);

void qw_server_paint_background_color(struct qw_server *server, int x, int y, float color[4]);

void qw_server_loop_input_devices(struct qw_server *server, input_device_cb_t cb);
void qw_server_traverse_scene_graph(struct qw_server *server, node_info_cb_t cb);

#endif /* SERVER_H */
