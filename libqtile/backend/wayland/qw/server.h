#ifndef SERVER_H
#define SERVER_H

#include <assert.h>
#include <getopt.h>
#include <stdbool.h>
#include <unistd.h>

#include "session-lock.h"
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
#include <wlr/types/wlr_idle_inhibit_v1.h>
#include <wlr/types/wlr_idle_notify_v1.h>
#include <wlr/types/wlr_input_device.h>
#include <wlr/types/wlr_keyboard.h>
#include <wlr/types/wlr_layer_shell_v1.h>
#include <wlr/types/wlr_output.h>
#include <wlr/types/wlr_output_layout.h>
#include <wlr/types/wlr_output_power_management_v1.h>
#include <wlr/types/wlr_pointer.h>
#include <wlr/types/wlr_presentation_time.h>
#include <wlr/types/wlr_primary_selection.h>
#include <wlr/types/wlr_primary_selection_v1.h>
#include <wlr/types/wlr_scene.h>
#include <wlr/types/wlr_screencopy_v1.h>
#include <wlr/types/wlr_seat.h>
#include <wlr/types/wlr_session_lock_v1.h>
#include <wlr/types/wlr_single_pixel_buffer_v1.h>
#include <wlr/types/wlr_subcompositor.h>
#include <wlr/types/wlr_viewporter.h>
#include <wlr/types/wlr_virtual_keyboard_v1.h>
#include <wlr/types/wlr_virtual_pointer_v1.h>
#include <wlr/types/wlr_xdg_activation_v1.h>
#include <wlr/types/wlr_xdg_shell.h>
#include <wlr/util/log.h>
#include <xkbcommon/xkbcommon.h>
#if WLR_HAS_XWAYLAND
#include <wlr/xwayland/xwayland.h>
#include <xcb/xcb.h>
#endif
#include "layer-view.h"

#if WLR_HAS_XWAYLAND
// _NET_WM_WINDOW_TYPE atoms
enum {
    NET_WM_WINDOW_TYPE_DIALOG,
    NET_WM_WINDOW_TYPE_UTILITY,
    NET_WM_WINDOW_TYPE_TOOLBAR,
    NET_WM_WINDOW_TYPE_MENU,
    NET_WM_WINDOW_TYPE_SPLASH,
    NET_WM_WINDOW_TYPE_DOCK,
    NET_WM_WINDOW_TYPE_TOOLTIP,
    NET_WM_WINDOW_TYPE_NOTIFICATION,
    NET_WM_WINDOW_TYPE_DESKTOP,
    NET_WM_WINDOW_TYPE_DROPDOWN_MENU,
    NET_WM_WINDOW_TYPE_POPUP_MENU,
    NET_WM_WINDOW_TYPE_COMBO,
    NET_WM_WINDOW_TYPE_DND,
    NET_WM_WINDOW_TYPE_NORMAL,
    ATOM_LAST,
};
#endif

// Callback typedefs for input and view events

// Keyboard key event callback: keysym, modifier mask, and user data
typedef int (*keyboard_key_cb_t)(xkb_keysym_t keysym, uint32_t mask, void *userdata);

// Forward declaration of view struct
struct qw_view;

// Callbacks for managing views
typedef void (*unmanage_view_cb_t)(struct qw_view *view, void *userdata);
typedef void (*manage_view_cb_t)(struct qw_view *view, void *userdata);

// Cursor motion event callback: user data
typedef void (*cursor_motion_cb_t)(void *userdata);

// Cursor button event callback: button, modifiers, pressed state, position, user data
typedef int (*cursor_button_cb_t)(int button, uint32_t mask, bool pressed, int x, int y,
                                  void *userdata);

// Output dimensions callback: x, y, width, height of output
typedef void (*output_dims_cb_t)(int x, int y, int width, int height);

// Query tree node wid callback
typedef void (*node_wid_cb_t)(int wid);

// Callback for when screen configuration changes
typedef void (*on_screen_change_cb_t)(void *userdata);

// Callback for when session lock status changes
typedef void (*on_session_lock_cb_t)(bool locked, void *userdata);

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

// Callback to get output dimensions for qtile's current screen
typedef struct wlr_box (*get_current_output_dims_cb_t)(void *userdata);

// Callbacks for idle inhibit functions
typedef bool (*add_idle_inhibitor_cb_t)(void *userdata, void *inhibitor, void *view,
                                        bool is_layer_surface, bool is_session_lock_surface);
typedef bool (*remove_idle_inhibitor_cb_t)(void *userdata, void *inhibitor);
typedef bool (*check_inhibited_cb_t)(void *userdata);

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
    LAYER_DRAG_ICON,    // drag icon displayed above everything
    LAYER_LOCK,         // session lock above everything
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

typedef void (*view_activation_cb_t)(struct qw_view *view, void *userdata);

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
    view_activation_cb_t view_activation_cb;
    on_input_device_added_cb_t on_input_device_added_cb;
    focus_current_window_cb_t focus_current_window_cb;
    on_session_lock_cb_t on_session_lock_cb;
    get_current_output_dims_cb_t get_current_output_dims_cb;
    add_idle_inhibitor_cb_t add_idle_inhibitor_cb;
    remove_idle_inhibitor_cb_t remove_idle_inhibitor_cb;
    check_inhibited_cb_t check_inhibited_cb;
    void *view_activation_cb_data;
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
    struct wlr_scene_tree *drag_icon;
    struct wlr_scene_output_layout *scene_layout;
    struct wlr_output_layout *output_layout;
    struct wl_list outputs;
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
    struct wl_listener request_start_drag;
    struct wl_listener start_drag;
    struct wl_listener new_session_lock;
    struct wlr_session_lock_manager_v1 *lock_manager;
    struct qw_session_lock *lock;
    struct wlr_scene_tree *lock_tree;
    enum qw_session_lock_state lock_state;
    struct wlr_foreign_toplevel_manager_v1 *ftl_mgr;
    struct wlr_virtual_keyboard_manager_v1 *virtual_keyboard;
    struct wlr_virtual_pointer_manager_v1 *virtual_pointer;
    struct wl_listener virtual_keyboard_new;
    struct wl_listener virtual_pointer_new;
    struct wlr_idle_inhibit_manager_v1 *idle_inhibit_manager;
    struct wlr_idle_notifier_v1 *idle_notifier;
    struct wl_listener new_idle_inhibitor;
    struct wl_list idle_inhibitors;
    struct wlr_output_power_manager_v1 *output_power_manager;
    struct wl_listener set_output_power_mode;
#if WLR_HAS_XWAYLAND
    struct wlr_xwayland *xwayland;
    struct wl_listener xwayland_ready;
    struct wl_listener new_xwayland_surface;
    xcb_atom_t xwayland_atoms[ATOM_LAST];
#endif
    struct wl_listener request_activate;
    struct wl_listener new_token;
    struct wlr_relative_pointer_manager_v1 *relative_pointer_manager;
    struct wlr_pointer_constraints_v1 *pointer_constraints;
    struct wl_listener new_pointer_constraint;
};

struct qw_drag_icon {
    struct qw_server *server;
    // Private data
    struct wlr_scene_tree *scene_icon;
    struct wl_listener destroy;
};

struct qw_idle_inhibitor {
    struct qw_server *server;
    // Private data
    struct wlr_idle_inhibitor_v1 *wlr_inhibitor;
    struct wl_listener destroy;
    struct wl_list link; // server->idle_inhibitors
};

// Utility functions exposed by the server API

// Get  key sym from a key code
xkb_keysym_t qw_server_get_sym_from_code(struct qw_server *server, int code);

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

void qw_server_set_output_fullscreen_background(struct qw_server *server, int x, int y,
                                                bool enabled);

struct wlr_output *qw_server_get_current_output(struct qw_server *server);

void qw_server_idle_notify_activity(struct qw_server *server);
void qw_server_set_inhibited(struct qw_server *server, bool inhibited);
bool qw_server_inhibitor_surface_visible(struct qw_idle_inhibitor *inhibitor,
                                         struct wlr_surface *surface);

#endif /* SERVER_H */
