#include <libinput.h>
#include <stdlib.h>
#include <wlr/backend/libinput.h>
#include <wlr/backend/session.h>
#include <wlr/types/wlr_output_management_v1.h>
#include <wlr/types/wlr_pointer_constraints_v1.h>
#include <wlr/types/wlr_relative_pointer_v1.h>
#include <wlr/types/wlr_server_decoration.h>
#include <wlr/types/wlr_virtual_keyboard_v1.h>
#include <wlr/types/wlr_virtual_pointer_v1.h>
#include <wlr/types/wlr_xdg_decoration_v1.h>
#include <wlr/types/wlr_xdg_output_v1.h>

#include "cursor.h"
#include "input-device.h"
#include "keyboard.h"
#include "layer-view.h"
#include "output.h"
#include "server.h"
#include "session-lock.h"
#include "util.h"
#include "view.h"
#include "wayland-server-core.h"
#include "wayland-server-protocol.h"
#include "wayland-util.h"
#include "wlr/util/log.h"
#include "xdg-view.h"
#if WLR_HAS_XWAYLAND
#include "xwayland-view.h"
#endif

#include <cairo/cairo.h>
#include <wlr/render/wlr_texture.h>

// Get the file descriptor of the Wayland event loop (used for epoll integration)
int qw_server_get_event_loop_fd(struct qw_server *server) {
    return wl_event_loop_get_fd(server->event_loop);
}

// Perform a single event loop iteration manually.
// Used when you want control over dispatching (e.g., in embedded event loops).
void qw_server_poll(struct qw_server *server) {
    if (!server->display) {
        return;
    }
    wl_display_flush_clients(server->display);
    wl_event_loop_dispatch(server->event_loop, 0);
    wl_display_flush_clients(server->display);
}

// Cleanup routine to destroy the compositor and free resources.
void qw_server_finalize(struct qw_server *server) {
    // TODO: what else to finalize?
    wl_list_remove(&server->new_input.link);
    wl_list_remove(&server->new_output.link);
    wl_list_remove(&server->output_layout_change.link);
    wl_list_remove(&server->output_manager_apply.link);
    wl_list_remove(&server->output_manager_test.link);
    wl_list_remove(&server->new_xdg_toplevel.link);
    wl_list_remove(&server->new_decoration.link);
    wl_list_remove(&server->new_layer_surface.link);
    wl_list_remove(&server->renderer_lost.link);
    wl_list_remove(&server->request_activate.link);
    wl_list_remove(&server->new_token.link);
    wl_list_remove(&server->request_set_selection.link);
    wl_list_remove(&server->request_set_primary_selection.link);
    wl_list_remove(&server->request_start_drag.link);
    wl_list_remove(&server->start_drag.link);
    wl_list_remove(&server->new_session_lock.link);
    wl_list_remove(&server->virtual_keyboard_new.link);
    wl_list_remove(&server->virtual_pointer_new.link);
    wl_list_remove(&server->new_pointer_constraint.link);
    wl_list_remove(&server->new_idle_inhibitor.link);
    wl_list_remove(&server->set_output_power_mode.link);
#if WLR_HAS_XWAYLAND
    wl_list_remove(&server->new_xwayland_surface.link);
    wl_list_remove(&server->xwayland_ready.link);
    wlr_xwayland_destroy(server->xwayland);
#endif
    wl_display_destroy_clients(server->display);
    wlr_scene_node_destroy(&server->scene->tree.node);
    qw_cursor_destroy(server->cursor);
    wlr_allocator_destroy(server->allocator);
    wlr_renderer_destroy(server->renderer);
    wlr_backend_destroy(server->backend);
    wl_display_destroy(server->display);
}

// Call a callback for each active output, passing its position and dimensions.
void qw_server_loop_output_dims(struct qw_server *server, output_dims_cb_t cb) {
    struct qw_output *o;
    wl_list_for_each(o, &server->outputs, link) {
        if (!o->wlr_output || !o->wlr_output->enabled || o->disabled_by_opm) {
            continue;
        }
        int width, height;
        wlr_output_effective_resolution(o->wlr_output, &width, &height);
        cb(o->x, o->y, width, height);
    }
}

// Initializes event loop and starts the Wayland backend
void qw_server_start(struct qw_server *server) {
    server->event_loop = wl_display_get_event_loop(server->display);
    server->socket = wl_display_add_socket_auto(server->display);
    if (!server->socket) {
        wlr_backend_destroy(server->backend);
        return;
    }
    if (!wlr_backend_start(server->backend)) {
        wlr_backend_destroy(server->backend);
        wl_display_destroy(server->display);
        return;
    }

    wlr_log(WLR_INFO, "Running Wayland compositor on WAYLAND_DISPLAY=%s", server->socket);
}

// Stub function – maybe used for keymap introspection in the future
xkb_keysym_t qw_server_get_sym_from_code(struct qw_server *server, int code) {
    struct wlr_keyboard *keyboard = wlr_seat_get_keyboard(server->seat);

    if (keyboard == NULL || keyboard->xkb_state == NULL) {
        return 0;
    }

    return xkb_state_key_get_one_sym(keyboard->xkb_state, code);
}

void qw_server_keyboard_clear_focus(struct qw_server *server) {
    struct wlr_seat *seat = server->seat;
    wlr_seat_keyboard_clear_focus(seat);
}

// Handle when a new output (monitor/display) is connected.
// Calls qw_server_output_new to add the new output to the server.
static void qw_server_handle_new_output(struct wl_listener *listener, void *data) {
    struct qw_server *server = wl_container_of(listener, server, new_output);
    struct wlr_output *output = data;

    qw_server_output_new(server, output);
}

void qw_server_set_output_fullscreen_background(struct qw_server *server, int x, int y,
                                                bool enabled) {
    struct wlr_output *wout;
    wout = wlr_output_layout_output_at(server->output_layout, x, y);
    if (wout != NULL) {
        struct qw_output *output = wout->data;
        qw_output_toggle_fullscreen_background(output, enabled);
    }
}

// Handle changes in the output layout (like monitor arrangement).
// Updates output configuration accordingly.
static void qw_server_handle_output_layout_change(struct wl_listener *listener, void *data) {
    UNUSED(data);

    struct qw_server *server = wl_container_of(listener, server, output_layout_change);
    struct wlr_output_configuration_v1 *config = wlr_output_configuration_v1_create();
    struct wlr_output_configuration_head_v1 *config_head;
    struct qw_output *o;

    wl_list_for_each(o, &server->outputs, link) {
        if (o->wlr_output->enabled)
            continue;
        config_head = wlr_output_configuration_head_v1_create(config, o->wlr_output);
        config_head->state.enabled = 0;
        wlr_output_layout_remove(server->output_layout, o->wlr_output);
        o->full_area = o->area = (struct wlr_box){0};
    }
    wl_list_for_each(o, &server->outputs, link) {
        if (!o->wlr_output->enabled || o->disabled_by_opm)
            continue;
        if (!wlr_output_layout_get(server->output_layout, o->wlr_output))
            wlr_output_layout_add_auto(server->output_layout, o->wlr_output);
    }

    wl_list_for_each(o, &server->outputs, link) {
        if (!o->wlr_output->enabled || o->disabled_by_opm)
            continue;
        config_head = wlr_output_configuration_head_v1_create(config, o->wlr_output);

        wlr_output_layout_get_box(server->output_layout, o->wlr_output, &o->full_area);
        o->area = o->full_area;

        wlr_scene_output_set_position(o->scene, o->x, o->y);
        wlr_log(WLR_INFO, "Updating: %d,%d (%dx%d)", o->full_area.x, o->full_area.y,
                o->full_area.width, o->full_area.height);

        if (o->fullscreen_background != NULL) {
            wlr_scene_node_set_position(&o->fullscreen_background->node, o->full_area.x,
                                        o->full_area.y);
            wlr_scene_rect_set_size(o->fullscreen_background, o->full_area.width,
                                    o->full_area.height);
        }

        // TODO: lock surface
        qw_session_lock_output_change(o);

        qw_output_arrange_layers(o);

        // TODO: arrange

        config_head->state.x = o->x = o->full_area.x;
        config_head->state.y = o->y = o->full_area.y;
    }

    wlr_output_manager_v1_set_configuration(server->output_mgr, config);

    // Only trigger screen change callback if the session is active
    // or if session is NULL (i.e. in a nested or headless session)
    // This prevents the hook firing on VT changes
    if (server->session == NULL || server->session->active) {
        server->on_screen_change_cb(server->cb_data);
    }
}

// Reconfigure output(s) according to the provided configuration.
// If apply == true, commit changes, else just test the configuration.
static void qw_server_output_manager_reconfigure(struct qw_server *server,
                                                 struct wlr_output_configuration_v1 *config,
                                                 bool apply) {
    bool ok = true;
    struct wlr_output_head_v1 *head;
    wl_list_for_each(head, &config->heads, link) {
        struct wlr_output_state state;
        wlr_output_state_init(&state);
        wlr_output_state_set_enabled(&state, head->state.enabled);
        if (head->state.enabled) {
            if (head->state.mode) {
                wlr_output_state_set_mode(&state, head->state.mode);
            } else {
                wlr_output_state_set_custom_mode(&state, head->state.custom_mode.width,
                                                 head->state.custom_mode.height,
                                                 head->state.custom_mode.refresh);
            }
            wlr_output_state_set_transform(&state, head->state.transform);
            wlr_output_state_set_scale(&state, head->state.scale);
            wlr_output_state_set_adaptive_sync_enabled(&state, head->state.adaptive_sync_enabled);
            struct wlr_box box;
            wlr_output_layout_get_box(server->output_layout, head->state.output, &box);
            if (box.x != head->state.x || box.y != head->state.y) {
                wlr_output_layout_add(server->output_layout, head->state.output, head->state.x,
                                      head->state.y);
            }
            // TODO rescale the cursor if necessary
            // TODO: cursor_manager.load
            // TODO: set_xcursor if no surface
        }
        if (apply) {
            ok &= wlr_output_commit_state(head->state.output, &state);
        } else {
            ok &= wlr_output_test_state(head->state.output, &state);
        }
        wlr_output_state_finish(&state);
    }
    if (ok) {
        wlr_output_configuration_v1_send_succeeded(config);
    } else {
        wlr_output_configuration_v1_send_failed(config);
    }
    wlr_output_configuration_v1_destroy(config);
    if (apply) {
        qw_server_handle_output_layout_change(&server->output_layout_change, NULL);
    }
}

// Listener for output manager apply event (commit config)
static void qw_server_handle_output_manager_apply(struct wl_listener *listener, void *data) {
    struct qw_server *server = wl_container_of(listener, server, output_manager_apply);
    struct wlr_output_configuration_v1 *config = (struct wlr_output_configuration_v1 *)data;
    qw_server_output_manager_reconfigure(server, config, true);
}

// Listener for output manager test event (test config)
static void qw_server_handle_output_manager_test(struct wl_listener *listener, void *data) {
    struct qw_server *server = wl_container_of(listener, server, output_manager_test);
    struct wlr_output_configuration_v1 *config = (struct wlr_output_configuration_v1 *)data;
    qw_server_output_manager_reconfigure(server, config, false);
}

// Handle wlr_renderer lost event caused by GPU resets or driver crashes.
// Recreates renderer/allocator and reinitializes outputs to restore functionality.
static void qw_server_handle_renderer_lost(struct wl_listener *listener, void *data) {
    UNUSED(data);
    struct qw_server *server = wl_container_of(listener, server, renderer_lost);

    wlr_log(WLR_INFO, "Re-generating renderer after GPU reset");

    // Create new renderer
    struct wlr_renderer *new_renderer = wlr_renderer_autocreate(server->backend);
    if (!new_renderer) {
        wlr_log(WLR_ERROR, "Unable to create renderer after GPU reset");
        return;
    }

    // Create new allocator
    struct wlr_allocator *new_allocator = wlr_allocator_autocreate(server->backend, new_renderer);
    if (!new_allocator) {
        wlr_log(WLR_ERROR, "Unable to create allocator after GPU reset");
        wlr_renderer_destroy(new_renderer);
        return;
    }

    // Store old renderer and allocator for cleanup
    struct wlr_renderer *old_renderer = server->renderer;
    struct wlr_allocator *old_allocator = server->allocator;

    // Update server with new renderer and allocator
    server->renderer = new_renderer;
    server->allocator = new_allocator;

    // Remove old renderer lost listener and add new one
    wl_list_remove(&server->renderer_lost.link);
    wl_signal_add(&server->renderer->events.lost, &server->renderer_lost);

    // Update compositor with new renderer
    wlr_compositor_set_renderer(server->compositor, new_renderer);

    // Reinitialize all outputs with new renderer/allocator
    struct qw_output *output;
    bool all_outputs_ok = true;

    wl_list_for_each(output, &server->outputs, link) {
        if (!wlr_output_init_render(output->wlr_output, server->allocator, server->renderer)) {
            wlr_log(WLR_ERROR, "Failed to reinitialize output %s after GPU reset",
                    output->wlr_output->name);
            all_outputs_ok = false;
        }
    }

    if (!all_outputs_ok) {
        wlr_log(WLR_INFO, "Some outputs failed to reinitialize after GPU reset");
    }

    // Reapply current output configuration with new renderer
    // This ensures outputs are properly configured after renderer recreation
    struct wlr_output_configuration_v1 *current_config = wlr_output_configuration_v1_create();
    if (current_config) {
        wl_list_for_each(output, &server->outputs, link) {
            if (!output->wlr_output->enabled || output->disabled_by_opm)
                continue;

            struct wlr_output_configuration_head_v1 *config_head =
                wlr_output_configuration_head_v1_create(current_config, output->wlr_output);

            config_head->state.enabled = true;
            config_head->state.x = output->x;
            config_head->state.y = output->y;
            if (output->wlr_output->current_mode) {
                config_head->state.mode = output->wlr_output->current_mode;
            }
            config_head->state.transform = output->wlr_output->transform;
            config_head->state.scale = output->wlr_output->scale;
        }
    }

    // TODO: Handle existing surfaces/views that might need to be recreated
    // This might involve notifying clients to recreate their buffers

    // Clean up old renderer and allocator
    wlr_allocator_destroy(old_allocator);
    wlr_renderer_destroy(old_renderer);

    wlr_log(WLR_INFO, "Successfully recovered from GPU reset");
}

// Handle new input devices: keyboard or pointer
static void qw_server_handle_new_input(struct wl_listener *listener, void *data) {
    struct qw_server *server = wl_container_of(listener, server, new_input);
    struct wlr_input_device *device = data;

    qw_server_input_device_new(server, device);
}

void qw_server_handle_virtual_keyboard(struct wl_listener *listener, void *data) {
    struct qw_server *server = wl_container_of(listener, server, virtual_keyboard_new);
    struct wlr_virtual_keyboard_v1 *keyboard = data;
    struct wlr_input_device *device = &keyboard->keyboard.base;

    qw_server_input_device_new(server, device);
}

void qw_server_handle_virtual_pointer(struct wl_listener *listener, void *data) {
    struct qw_server *server = wl_container_of(listener, server, virtual_pointer_new);
    struct wlr_virtual_pointer_v1_new_pointer_event *event = data;
    struct wlr_virtual_pointer_v1 *pointer = event->new_pointer;
    struct wlr_input_device *device = &pointer->pointer.base;

    qw_server_input_device_new(server, device);

    if (event->suggested_output != NULL) {
        wlr_cursor_map_input_to_output(server->cursor->cursor, device, event->suggested_output);
    }
}

// Handle new XDG toplevel window creation
static void qw_server_handle_new_xdg_toplevel(struct wl_listener *listener, void *data) {
    struct qw_server *server = wl_container_of(listener, server, new_xdg_toplevel);
    struct wlr_xdg_toplevel *xdg_toplevel = data;
    qw_server_xdg_view_new(server, xdg_toplevel);
}

// Handle new window decoration requests for XDG toplevels
static void qw_server_handle_new_decoration(struct wl_listener *listener, void *data) {
    UNUSED(listener);
    struct wlr_xdg_toplevel_decoration_v1 *decoration = data;
    qw_xdg_view_decoration_new(decoration->toplevel->base->data, decoration);
}

static void qw_server_handle_new_layer_surface(struct wl_listener *listener, void *data) {
    struct qw_server *server = wl_container_of(listener, server, new_layer_surface);
    struct wlr_layer_surface_v1 *layer_surface = data;
    qw_server_layer_view_new(server, layer_surface);
}

#if WLR_HAS_XWAYLAND
// xcb atoms cannot be retrieved by publicly available headers so we need
// to create a connection to the server and submit requests to retrieve the
// information.
static xcb_atom_t qw_intern_atom(xcb_connection_t *conn, const char *name) {
    xcb_intern_atom_cookie_t cookie = xcb_intern_atom(conn, 0, strlen(name), name);
    xcb_intern_atom_reply_t *reply = xcb_intern_atom_reply(conn, cookie, NULL);
    xcb_atom_t atom = reply ? reply->atom : XCB_ATOM_NONE;
    free(reply);
    return atom;
}

// Store details of window type atoms so we can determine a windows _NET_WM_WINDOW_TYPE
void qw_xwayland_atoms_init(struct wlr_xwayland *xwayland, xcb_atom_t *atoms) {
    int screen = 0;
    xcb_connection_t *conn = xcb_connect(xwayland->display_name, &screen);
    if (xcb_connection_has_error(conn)) {
        wlr_log(WLR_ERROR, "Couldn't connect to X server to retrieve atoms.");
        return;
    }
    // clang-format off
    atoms[NET_WM_WINDOW_TYPE_DIALOG]        = qw_intern_atom(conn, "_NET_WM_WINDOW_TYPE_DIALOG");
    atoms[NET_WM_WINDOW_TYPE_UTILITY]       = qw_intern_atom(conn, "_NET_WM_WINDOW_TYPE_UTILITY");
    atoms[NET_WM_WINDOW_TYPE_TOOLBAR]       = qw_intern_atom(conn, "_NET_WM_WINDOW_TYPE_TOOLBAR");
    atoms[NET_WM_WINDOW_TYPE_MENU]          = qw_intern_atom(conn, "_NET_WM_WINDOW_TYPE_MENU");
    atoms[NET_WM_WINDOW_TYPE_SPLASH]        = qw_intern_atom(conn, "_NET_WM_WINDOW_TYPE_SPLASH");
    atoms[NET_WM_WINDOW_TYPE_DOCK]          = qw_intern_atom(conn, "_NET_WM_WINDOW_TYPE_DOCK");
    atoms[NET_WM_WINDOW_TYPE_TOOLTIP]       = qw_intern_atom(conn, "_NET_WM_WINDOW_TYPE_TOOLTIP");
    atoms[NET_WM_WINDOW_TYPE_NOTIFICATION]  = qw_intern_atom(conn, "_NET_WM_WINDOW_TYPE_NOTIFICATION");
    atoms[NET_WM_WINDOW_TYPE_DESKTOP]       = qw_intern_atom(conn, "_NET_WM_WINDOW_TYPE_DESKTOP");
    atoms[NET_WM_WINDOW_TYPE_DROPDOWN_MENU] = qw_intern_atom(conn, "_NET_WM_WINDOW_TYPE_DROPDOWN_MENU");
    atoms[NET_WM_WINDOW_TYPE_POPUP_MENU]    = qw_intern_atom(conn, "_NET_WM_WINDOW_TYPE_POPUP_MENU");
    atoms[NET_WM_WINDOW_TYPE_COMBO]         = qw_intern_atom(conn, "_NET_WM_WINDOW_TYPE_COMBO");
    atoms[NET_WM_WINDOW_TYPE_DND]           = qw_intern_atom(conn, "_NET_WM_WINDOW_TYPE_DND");
    atoms[NET_WM_WINDOW_TYPE_NORMAL]        = qw_intern_atom(conn, "_NET_WM_WINDOW_TYPE_NORMAL");
    // clang-format on
    xcb_disconnect(conn);
}

static void qw_server_handle_new_xwayland_surface(struct wl_listener *listener, void *data) {
    struct qw_server *server = wl_container_of(listener, server, new_xwayland_surface);
    struct wlr_xwayland_surface *xwayland_surface = data;
    if (xwayland_surface->override_redirect) {
        qw_server_xwayland_static_view_new(server, xwayland_surface);
    } else {
        qw_server_xwayland_view_new(server, xwayland_surface);
    }
}

const char *qw_server_xwayland_display_name(struct qw_server *server) {
    return server->xwayland->display_name;
}
#else
const char *qw_server_xwayland_display_name(struct qw_server *server) { return NULL; }
#endif

static void qw_server_handle_xwayland_ready(struct wl_listener *listener, void *data) {
    UNUSED(data);
    struct qw_server *server = wl_container_of(listener, server, xwayland_ready);
    qw_xwayland_atoms_init(server->xwayland, server->xwayland_atoms);
}

// Return the view at the given layout coordinates, if any.
// Also fills out surface and surface-local coords if found.
struct qw_view *qw_server_view_at(struct qw_server *server, double lx, double ly,
                                  struct wlr_surface **surface, double *sx, double *sy) {
    struct wlr_scene_node *node = wlr_scene_node_at(&server->scene->tree.node, lx, ly, sx, sy);
    if (!node) {
        return NULL;
    }

    if (node->type == WLR_SCENE_NODE_BUFFER || node->type == WLR_SCENE_NODE_RECT) {
        if (node->type == WLR_SCENE_NODE_BUFFER) {
            struct wlr_scene_buffer *scene_buffer = wlr_scene_buffer_from_node(node);
            struct wlr_scene_surface *scene_surface =
                wlr_scene_surface_try_from_buffer(scene_buffer);
            if (scene_surface != NULL) {
                *surface = scene_surface->surface;
            }
        }

        // Walk up the tree to find the associated view
        struct wlr_scene_tree *tree = node->parent;
        while (tree && !tree->node.data) {
            tree = tree->node.parent;
        }
        if (tree != NULL) {
            return tree->node.data;
        }
    }

    return NULL;
}

struct qw_cursor *qw_server_get_cursor(struct qw_server *server) { return server->cursor; }

static void qw_handle_activation_request(struct wl_listener *listener, void *data) {
    struct qw_server *server = wl_container_of(listener, server, request_activate);
    struct wlr_xdg_activation_v1_request_activate_event *event = data;

    if (event->token == NULL || event->token->data == NULL) {
        wlr_log(WLR_INFO, "Activation request has no token or token data");
        return;
    }

    struct qw_xdg_activation_token *token_data = event->token->data;

    struct wlr_xdg_surface *xdg_surface = wlr_xdg_surface_try_from_wlr_surface(event->surface);

    if (xdg_surface == NULL) {
        wlr_log(WLR_INFO, "Activation request for unknown surface");
        return;
    }

    // Get the view associated with the surface
    struct qw_xdg_view *view = xdg_surface->data;

    if (view == NULL) {
        wlr_log(WLR_INFO, "Not activating surface - no view attached");
        return;
    }

    if (!token_data->qw_valid_seat) {
        wlr_log(WLR_INFO, "Denying focus request, seat wasn't supplied");
        return;
    }

    struct wlr_surface *focused = server->seat->keyboard_state.focused_surface;

    if (focused != NULL && focused == event->surface) {
        wlr_log(WLR_INFO, "Ignoring activation request, surface is focused");
        return;
    }

    if (server->view_activation_cb != NULL) {
        wlr_log(WLR_DEBUG, "Activation token valid, focusing view");
        server->view_activation_cb((struct qw_view *)view, server->view_activation_cb_data);
    }
}

void qw_server_set_keymap(struct qw_server *server, const char *layout, const char *options,
                          const char *variant) {
    struct qw_keyboard *keyboard;
    wl_list_for_each(keyboard, &server->keyboards, link) {
        qw_keyboard_set_keymap(keyboard, layout, options, variant);
    }
}

static void qw_server_handle_request_set_selection(struct wl_listener *listener, void *data) {
    struct qw_server *server = wl_container_of(listener, server, request_set_selection);
    struct wlr_seat_request_set_selection_event *event = data;

    wlr_seat_set_selection(server->seat, event->source, event->serial);
}

static void qw_server_handle_request_set_primary_selection(struct wl_listener *listener,
                                                           void *data) {
    struct qw_server *server = wl_container_of(listener, server, request_set_primary_selection);
    struct wlr_seat_request_set_primary_selection_event *event = data;

    wlr_seat_set_primary_selection(server->seat, event->source, event->serial);
}

static void qw_server_handle_drag_icon_destroy(struct wl_listener *listener, void *data) {
    UNUSED(data);
    struct qw_drag_icon *drag_icon = wl_container_of(listener, drag_icon, destroy);
    struct qw_server *server = drag_icon->server;

    // Restore window focus
    server->focus_current_window_cb(server->cb_data);

    // Restore pointer focus
    double sx, sy;
    struct wlr_surface *surface = NULL;
    // We call this just to set sx and sy. We don't need the view.
    qw_server_view_at(server, server->cursor->cursor->x, server->cursor->cursor->y, &surface, &sx,
                      &sy);

    if (surface != NULL) {
        wlr_seat_pointer_notify_enter(server->seat, surface, sx, sy);
    } else {
        wlr_seat_pointer_clear_focus(server->seat);
    }

    // Tidy up
    wl_list_remove(&listener->link);
    free(drag_icon);
}

static void qw_server_handle_request_start_drag(struct wl_listener *listener, void *data) {
    struct qw_server *server = wl_container_of(listener, server, request_start_drag);
    struct wlr_seat_request_start_drag_event *event = data;

    if (wlr_seat_validate_pointer_grab_serial(server->seat, event->origin, event->serial)) {
        wlr_seat_start_pointer_drag(server->seat, event->drag, event->serial);
    } else {
        wlr_data_source_destroy(event->drag->source);
    }
}

static void qw_server_handle_start_drag(struct wl_listener *listener, void *data) {
    struct qw_server *server = wl_container_of(listener, server, start_drag);
    struct wlr_drag *drag = data;
    qw_cursor_release_implicit_grab(server->cursor, 0);
    if (drag->icon == NULL) {
        return;
    }

    struct qw_drag_icon *drag_icon = calloc(1, sizeof(*drag_icon));
    drag_icon->server = server;
    drag_icon->scene_icon = wlr_scene_drag_icon_create(server->drag_icon, drag->icon);
    drag_icon->destroy.notify = qw_server_handle_drag_icon_destroy;
    wl_signal_add(&drag->events.destroy, &drag_icon->destroy);
}

void qw_server_handle_new_pointer_constraint(struct wl_listener *listener, void *data) {
    struct qw_server *server = wl_container_of(listener, server, new_pointer_constraint);
    struct wlr_pointer_constraint_v1 *constraint = data;

    qw_cursor_pointer_constraint_new(server->cursor, constraint);
}

void qw_server_set_inhibited(struct qw_server *server, bool inhibited) {
    wlr_idle_notifier_v1_set_inhibited(server->idle_notifier, inhibited);
}

static void qw_server_handle_idle_inhibitor_destroy(struct wl_listener *listener, void *data) {
    UNUSED(data);
    struct qw_idle_inhibitor *inhibitor = wl_container_of(listener, inhibitor, destroy);
    struct qw_server *server = inhibitor->server;
    bool removed = server->remove_idle_inhibitor_cb(server->cb_data, inhibitor);
    if (!removed) {
        wlr_log(WLR_ERROR, "Unable to remove idle inhibitor.");
    }

    wl_list_remove(&inhibitor->link);
    wl_list_remove(&inhibitor->destroy.link);

    free(inhibitor);
}

static void qw_server_handle_new_idle_inhibitor(struct wl_listener *listener, void *data) {
    struct qw_server *server = wl_container_of(listener, server, new_idle_inhibitor);
    struct wlr_idle_inhibitor_v1 *wlr_inhibitor = data;

    struct qw_idle_inhibitor *inhibitor = calloc(1, sizeof(struct qw_idle_inhibitor));

    inhibitor->server = server;
    inhibitor->wlr_inhibitor = wlr_inhibitor;

    wl_list_insert(&server->idle_inhibitors, &inhibitor->link);

    inhibitor->destroy.notify = qw_server_handle_idle_inhibitor_destroy;
    wl_signal_add(&wlr_inhibitor->events.destroy, &inhibitor->destroy);

    struct wlr_surface *surface = wlr_inhibitor->surface;
    bool is_layer_surface, is_session_lock_surface;
    struct qw_view *view =
        qw_view_from_wlr_surface(surface, &is_layer_surface, &is_session_lock_surface);

    void *view_cb_data = NULL;

    if (view != NULL && view->cb_data) {
        view_cb_data = view->cb_data;
    }

    bool added = server->add_idle_inhibitor_cb(server->cb_data, inhibitor, view_cb_data,
                                               is_layer_surface, is_session_lock_surface);
    if (!added) {
        wlr_log(WLR_ERROR, "Unable to add idle inhibitor.");
    }
}

static void qw_server_handle_output_power_set_mode(struct wl_listener *listener, void *data) {
    struct qw_server *server = wl_container_of(listener, server, set_output_power_mode);
    struct wlr_output_power_v1_set_mode_event *event = data;

    struct wlr_output *wlr_output = event->output;
    struct qw_output *output = wlr_output->data;
    struct wlr_output_state state = {0};

    if (output == NULL) {
        wlr_log(WLR_ERROR, "Couldn't find qw_output for power management event.");
        return;
    }

    if (event->mode == ZWLR_OUTPUT_POWER_V1_MODE_ON) {
        // Only re-enable if compositor itself disabled output via power management
        if (output->disabled_by_opm) {

            wlr_output_state_set_enabled(&state, event->mode);

            if (!wlr_output_commit_state(wlr_output, &state)) {
                wlr_log(WLR_ERROR, "Failed to enable output %s.", wlr_output->name);
                return;
            }
            output->disabled_by_opm = false;
        }

    } else {
        if (wlr_output->enabled) {
            wlr_output_state_set_enabled(&state, event->mode);

            if (!wlr_output_commit_state(wlr_output, &state)) {
                wlr_log(WLR_ERROR, "Failed to disable output %s", wlr_output->name);
                return;
            }

            // Add flag to show that compositor disabled monitor via output power management
            if (!output->disabled_by_opm) {
                output->disabled_by_opm = true;
            }
        }
    }
}

// Create and initialize the server object with all components and listeners.
struct qw_server *qw_server_create() {
    struct qw_server *server = calloc(1, sizeof(*server));
    if (!server) {
        wlr_log(WLR_ERROR, "failed to create qw_server struct");
        return NULL;
    }

    server->display = wl_display_create();
    server->backend =
        wlr_backend_autocreate(wl_display_get_event_loop(server->display), &server->session);
    if (!server->backend) {
        wlr_log(WLR_ERROR, "failed to create wlr_backend");
        free(server);
        return NULL;
    }
    server->renderer = wlr_renderer_autocreate(server->backend);
    if (!server->renderer) {
        wlr_log(WLR_ERROR, "failed to create wlr_renderer");
        free(server);
        return NULL;
    }

    // TODO: do
    // https://codeberg.org/dwl/dwl/src/commit/bd59573f07f27fff7870a1e1a70e72493bb42453/dwl.c#L2473-L2479
    // instead?
    wlr_renderer_init_wl_display(server->renderer, server->display);
    server->allocator = wlr_allocator_autocreate(server->backend, server->renderer);
    if (!server->allocator) {
        wlr_log(WLR_ERROR, "failed to create wlr_allocator");
        free(server);
        return NULL;
    }

    server->compositor = wlr_compositor_create(server->display, 6, server->renderer);
    wlr_subcompositor_create(server->display);
    wlr_data_device_manager_create(server->display);
    wlr_export_dmabuf_manager_v1_create(server->display);
    wlr_screencopy_manager_v1_create(server->display);
    wlr_data_control_manager_v1_create(server->display);
    wlr_primary_selection_v1_device_manager_create(server->display);
    wlr_viewporter_create(server->display);
    wlr_single_pixel_buffer_manager_v1_create(server->display);
    wlr_fractional_scale_manager_v1_create(server->display, 1);
    wlr_presentation_create(server->display, server->backend, 2);
    wlr_alpha_modifier_v1_create(server->display);
    server->scene = wlr_scene_create();
    server->scene_wallpaper_tree = wlr_scene_tree_create(&server->scene->tree);
    server->scene_windows_tree = wlr_scene_tree_create(&server->scene->tree);
    for (int i = 0; i < LAYER_END; ++i) {
        server->scene_windows_layers[i] = wlr_scene_tree_create(server->scene_windows_tree);
    }

    wl_list_init(&server->outputs);
    server->output_layout = wlr_output_layout_create(server->display);
    server->output_layout_change.notify = qw_server_handle_output_layout_change;
    wlr_xdg_output_manager_v1_create(server->display, server->output_layout);
    wl_signal_add(&server->output_layout->events.change, &server->output_layout_change);
    server->scene_layout = wlr_scene_attach_output_layout(server->scene, server->output_layout);
    server->new_output.notify = qw_server_handle_new_output;
    wl_signal_add(&server->backend->events.new_output, &server->new_output);
    wl_list_init(&server->keyboards);
    wl_list_init(&server->input_devices);
    server->seat = wlr_seat_create(server->display, "seat0");
    server->cursor = qw_server_cursor_create(server);
    if (!server->cursor) {
        // already logged in the create if failed
        return NULL;
    }

    server->drag_icon = wlr_scene_tree_create(server->scene_windows_layers[LAYER_DRAG_ICON]);
    server->request_start_drag.notify = qw_server_handle_request_start_drag;
    wl_signal_add(&server->seat->events.request_start_drag, &server->request_start_drag);
    server->start_drag.notify = qw_server_handle_start_drag;
    wl_signal_add(&server->seat->events.start_drag, &server->start_drag);

    server->output_mgr = wlr_output_manager_v1_create(server->display);
    server->output_manager_apply.notify = qw_server_handle_output_manager_apply;
    wl_signal_add(&server->output_mgr->events.apply, &server->output_manager_apply);
    server->output_manager_test.notify = qw_server_handle_output_manager_test;
    wl_signal_add(&server->output_mgr->events.test, &server->output_manager_test);
    server->new_input.notify = qw_server_handle_new_input;
    wl_signal_add(&server->backend->events.new_input, &server->new_input);
    server->xdg_shell = wlr_xdg_shell_create(server->display, 3);
    server->new_xdg_toplevel.notify = qw_server_handle_new_xdg_toplevel;
    wl_signal_add(&server->xdg_shell->events.new_toplevel, &server->new_xdg_toplevel);

    wlr_server_decoration_manager_set_default_mode(
        wlr_server_decoration_manager_create(server->display),
        WLR_SERVER_DECORATION_MANAGER_MODE_SERVER);

    server->xdg_decoration_mgr = wlr_xdg_decoration_manager_v1_create(server->display);
    server->new_decoration.notify = qw_server_handle_new_decoration;
    wl_signal_add(&server->xdg_decoration_mgr->events.new_toplevel_decoration,
                  &server->new_decoration);

    server->layer_shell = wlr_layer_shell_v1_create(server->display, 3);
    server->new_layer_surface.notify = qw_server_handle_new_layer_surface;
    wl_signal_add(&server->layer_shell->events.new_surface, &server->new_layer_surface);
    server->renderer_lost.notify = qw_server_handle_renderer_lost;
    wl_signal_add(&server->renderer->events.lost, &server->renderer_lost);

    server->request_set_selection.notify = qw_server_handle_request_set_selection;
    wl_signal_add(&server->seat->events.request_set_selection, &server->request_set_selection);
    server->request_set_primary_selection.notify = qw_server_handle_request_set_primary_selection;
    wl_signal_add(&server->seat->events.request_set_primary_selection,
                  &server->request_set_primary_selection);

    server->virtual_keyboard = wlr_virtual_keyboard_manager_v1_create(server->display);
    server->virtual_keyboard_new.notify = qw_server_handle_virtual_keyboard;
    wl_signal_add(&server->virtual_keyboard->events.new_virtual_keyboard,
                  &server->virtual_keyboard_new);

    server->virtual_pointer = wlr_virtual_pointer_manager_v1_create(server->display);
    server->virtual_pointer_new.notify = qw_server_handle_virtual_pointer;
    wl_signal_add(&server->virtual_pointer->events.new_virtual_pointer,
                  &server->virtual_pointer_new);

    // Session lock setup
    qw_session_lock_init(server);

    server->ftl_mgr = wlr_foreign_toplevel_manager_v1_create(server->display);

    server->idle_inhibit_manager = wlr_idle_inhibit_v1_create(server->display);
    wl_list_init(&server->idle_inhibitors);
    server->new_idle_inhibitor.notify = qw_server_handle_new_idle_inhibitor;
    wl_signal_add(&server->idle_inhibit_manager->events.new_inhibitor, &server->new_idle_inhibitor);

    server->idle_notifier = wlr_idle_notifier_v1_create(server->display);

#if WLR_HAS_XWAYLAND
    server->xwayland = wlr_xwayland_create(server->display, server->compositor, true);
    wlr_xwayland_set_seat(server->xwayland, server->seat);
    server->new_xwayland_surface.notify = qw_server_handle_new_xwayland_surface;
    wl_signal_add(&server->xwayland->events.new_surface, &server->new_xwayland_surface);
    server->xwayland_ready.notify = qw_server_handle_xwayland_ready;
    wl_signal_add(&server->xwayland->events.ready, &server->xwayland_ready);
#endif

    // Initializes the interface used to implement urgency hints
    server->activation = wlr_xdg_activation_v1_create(server->display);
    server->request_activate.notify = qw_handle_activation_request;
    wl_signal_add(&server->activation->events.request_activate, &server->request_activate);
    server->new_token.notify = qw_xdg_activation_new_token;
    wl_signal_add(&server->activation->events.new_token, &server->new_token);

    wlr_scene_set_gamma_control_manager_v1(server->scene,
                                           wlr_gamma_control_manager_v1_create(server->display));

    server->relative_pointer_manager = wlr_relative_pointer_manager_v1_create(server->display);

    server->pointer_constraints = wlr_pointer_constraints_v1_create(server->display);
    server->new_pointer_constraint.notify = qw_server_handle_new_pointer_constraint;
    wl_signal_add(&server->pointer_constraints->events.new_constraint,
                  &server->new_pointer_constraint);

    server->output_power_manager = wlr_output_power_manager_v1_create(server->display);
    server->set_output_power_mode.notify = qw_server_handle_output_power_set_mode;
    wl_signal_add(&server->output_power_manager->events.set_mode, &server->set_output_power_mode);

    // TODO: setup listeners

    return server;
}

bool qw_server_change_vt(struct qw_server *server, int vt) {
    if (!server || !server->session) {
        return false;
    }
    return wlr_session_change_vt(server->session, vt);
}

static void qw_server_query_iterator(struct wlr_scene_buffer *buffer, int sx, int sy, void *data) {
    UNUSED(sx);
    UNUSED(sy);
    node_wid_cb_t cb = data;
    // Walk back up tree until we find a window or run out of parents
    struct wlr_scene_node *node = &buffer->node;
    while (node) {
        struct qw_view *view = node->data;
        if (view && node->enabled) {
            cb(view->wid);
            return;
        }
        if (!node->parent) {
            return;
        }
        node = &node->parent->node;
    }
}

// Iterate visible views in ascending Z order
void qw_server_loop_visible_views(struct qw_server *server, node_wid_cb_t cb) {
    wlr_scene_node_for_each_buffer(&server->scene->tree.node, qw_server_query_iterator, cb);
}

void qw_server_paint_wallpaper(struct qw_server *server, int x, int y, cairo_surface_t *source,
                               enum qw_wallpaper_mode mode) {
    struct wlr_output *output = wlr_output_layout_output_at(server->output_layout, x, y);

    if (output != NULL) {
        qw_output_paint_wallpaper(output->data, source, mode);
    }
}

void qw_server_paint_background_color(struct qw_server *server, int x, int y, float color[4]) {
    struct wlr_output *output = wlr_output_layout_output_at(server->output_layout, x, y);

    if (output != NULL) {
        qw_output_paint_background_color(output->data, color);
    }
}

void qw_server_loop_input_devices(struct qw_server *server, input_device_cb_t cb) {
    struct qw_input_device *input_device;
    wl_list_for_each(input_device, &server->input_devices, link) {
        struct wlr_input_device *device = input_device->device;

        int vendor = 0;
        int product = 0;
        if (wlr_input_device_is_libinput(device)) {
            struct libinput_device *libinput_device = wlr_libinput_get_device_handle(device);
            vendor = libinput_device_get_id_vendor(libinput_device);
            product = libinput_device_get_id_product(libinput_device);
        }

        cb(input_device, device->name, device->type, vendor, product);
    }
}
static char *LAYER_NAMES[] = {[LAYER_BACKGROUND] = "LAYER_BACKGROUND",
                              [LAYER_BOTTOM] = "LAYER_BOTTOM",
                              [LAYER_KEEPBELOW] = "LAYER_KEEPBELOW",
                              [LAYER_LAYOUT] = "LAYER_LAYOUT",
                              [LAYER_KEEPABOVE] = "LAYER_KEEPABOVE",
                              [LAYER_MAX] = "LAYER_MAX",
                              [LAYER_FULLSCREEN] = "LAYER_FULLSCREEN",
                              [LAYER_BRINGTOFRONT] = "LAYER_BRINGTOFRONT",
                              [LAYER_TOP] = "LAYER_TOP",
                              [LAYER_OVERLAY] = "LAYER_OVERLAY",
                              [LAYER_DRAG_ICON] = "LAYER_DRAG_ICON",
                              [LAYER_LOCK] = "LAYER_LOCK"};

static char *SCENE_NODE_TYPES[] = {[WLR_SCENE_NODE_TREE] = "tree",
                                   [WLR_SCENE_NODE_RECT] = "rect",
                                   [WLR_SCENE_NODE_BUFFER] = "buffer"};

// Helper function for qw_server_traverse_scene_graph()
static void qw_server_traverse_scene_node(struct wlr_scene_node *node,
                                          struct wlr_scene_tree *scene_windows_layers[],
                                          node_info_cb_t cb, void *parent) {
    struct scene_node_info info = {
        .name = "",
        .type = SCENE_NODE_TYPES[node->type],
        .enabled = node->enabled,
        .x = node->x,
        .y = node->y,
    };

    if (node->data != NULL) {
        // Node is associated with a window
        struct qw_view *view = (struct qw_view *)node->data;
        info.view_wid = view->wid;
        if (view->title != NULL) {
            info.name = view->title;
        }
    } else if (node->type == WLR_SCENE_NODE_TREE) {
        // Try and match with named layers
        for (int i = 0; i < LAYER_END; ++i) {
            if (scene_windows_layers[i] == wlr_scene_tree_from_node(node)) {
                if (LAYER_NAMES[i] != NULL) {
                    info.name = LAYER_NAMES[i];
                } else {
                    info.name = "UNKNOWN";
                }
            }
        }
    }

    cb((uintptr_t)node, (uintptr_t)parent, info);

    if (node->type == WLR_SCENE_NODE_TREE) {
        struct wlr_scene_tree *tree = wl_container_of(node, tree, node);
        struct wlr_scene_node *child;

        wl_list_for_each(child, &tree->children, link) {
            qw_server_traverse_scene_node(child, scene_windows_layers, cb, node);
        }
    }
}

void qw_server_traverse_scene_graph(struct qw_server *server, node_info_cb_t cb) {
    struct wlr_scene_node *root = &server->scene->tree.node;
    qw_server_traverse_scene_node(root, server->scene_windows_layers, cb, NULL);
}

struct wlr_output *qw_server_get_current_output(struct qw_server *server) {
    struct wlr_box current_output = server->get_current_output_dims_cb(server->cb_data);

    struct qw_output *output;
    wl_list_for_each(output, &server->outputs, link) {
        // Outputs alias if they have the same (x, y) and share the same Screen, so
        // we don't need to check the if the width and height match the Screen's.
        if (output->x == current_output.x && output->y == current_output.y) {
            return output->wlr_output;
        }
    }

    return NULL;
}

void qw_server_idle_notify_activity(struct qw_server *server) {
    if (server->idle_inhibit_manager != NULL) {
        wlr_idle_notifier_v1_notify_activity(server->idle_notifier, server->seat);
    }
}

// Idle inhibitors set by applications should only be active when the application is visible
// We can check this in python when the application is managed by qtile but, where that's not
// the case, we need to fall back to checking in the compositor.
// This should only be the case for session lock and layer surfaces.
bool qw_server_inhibitor_surface_visible(struct qw_idle_inhibitor *inhibitor,
                                         struct wlr_surface *surface) {
    if (surface == NULL) {
        surface = inhibitor->wlr_inhibitor->surface;
    }

    struct wlr_subsurface *subsurface;
    subsurface = wlr_subsurface_try_from_wlr_surface(surface);
    if (subsurface != NULL) {
        return qw_server_inhibitor_surface_visible(inhibitor, subsurface->parent);
    }

    struct wlr_layer_surface_v1 *layer_surface = wlr_layer_surface_v1_try_from_wlr_surface(surface);
    if (layer_surface != NULL) {
        return layer_surface->output && layer_surface->output->enabled && surface->mapped;
    }

    if (wlr_session_lock_surface_v1_try_from_wlr_surface(surface) != NULL) {
        return surface->mapped;
    }

    return false;
}
