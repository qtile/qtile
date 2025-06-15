#ifndef SERVER_H
#define SERVER_H

#include <assert.h>
#include <getopt.h>
#include <stdbool.h>
#include <unistd.h>
#include <wayland-server-core.h>
#include <wlr/backend.h>
#include <wlr/render/allocator.h>
#include <wlr/render/wlr_renderer.h>
#include <wlr/types/wlr_alpha_modifier_v1.h>
#include <wlr/types/wlr_compositor.h>
#include <wlr/types/wlr_data_control_v1.h>
#include <wlr/types/wlr_data_device.h>
#include <wlr/types/wlr_export_dmabuf_v1.h>
#include <wlr/types/wlr_fractional_scale_v1.h>
#include <wlr/types/wlr_input_device.h>
#include <wlr/types/wlr_keyboard.h>
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
#include <wlr/types/wlr_xdg_decoration_v1.h>
#include <wlr/types/wlr_xdg_shell.h>
#include <wlr/util/log.h>
#include <xkbcommon/xkbcommon.h>

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

// Callback for when screen configuration changes
typedef void (*on_screen_change_cb_t)(void *userdata);

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
    void *cb_data;

    // private data
    struct wl_event_loop *event_loop;
    struct wlr_compositor *compositor;
    struct wl_display *display;
    struct wlr_backend *backend;
    struct wlr_renderer *renderer;
    struct wlr_allocator *allocator;
    struct wlr_scene *scene;
    struct wlr_scene_output_layout *scene_layout;
    struct wlr_output_layout *output_layout;
    struct wl_list outputs;
    struct wlr_output_manager_v1 *output_mgr;
    struct wl_listener output_manager_apply;
    struct wl_listener output_manager_test;
    struct wl_listener new_output;
    struct wl_listener output_layout_change;
    struct wl_listener new_input;
    struct wl_list keyboards;
    struct wlr_seat *seat;
    struct qw_cursor *cursor;
    struct wlr_xdg_shell *xdg_shell;
    struct wlr_xdg_decoration_manager_v1 *xdg_decoration_mgr;
    struct wl_listener new_xdg_toplevel;
    struct wl_listener new_decoration;
    struct wl_listener request_cursor;
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
struct qw_server *qw_server_create();

// Find the view at a given layout coordinate (lx, ly)
// If a surface pointer is provided, it will be set to the surface under the point
// sx and sy are surface-local coordinates of the point
struct qw_view *qw_server_view_at(struct qw_server *server, double lx, double ly,
                                  struct wlr_surface **surface, double *sx, double *sy);

#endif /* SERVER_H */
