#include <stdlib.h>
#include <wlr/types/wlr_output_management_v1.h>
#include <wlr/types/wlr_server_decoration.h>
#include <wlr/types/wlr_xdg_output_v1.h>

#include "cursor.h"
#include "keyboard.h"
#include "output.h"
#include "server.h"
#include "wayland-server-protocol.h"
#include "xdg-view.h"

int qw_server_get_event_loop_fd(struct qw_server *server) {
    return wl_event_loop_get_fd(server->event_loop);
}

void qw_server_poll(struct qw_server *server) {
    if (!server->display) {
        return;
    }
    wl_display_flush_clients(server->display);
    wl_event_loop_dispatch(server->event_loop, 0);
    wl_display_flush_clients(server->display);
}

void qw_server_finalize(struct qw_server *server) {
    // TODO: what else to finalize?
    wl_display_destroy_clients(server->display);
    wlr_scene_node_destroy(&server->scene->tree.node);
    qw_cursor_destroy(server->cursor);
    wlr_allocator_destroy(server->allocator);
    wlr_renderer_destroy(server->renderer);
    wlr_backend_destroy(server->backend);
    wl_display_destroy(server->display);
}

void qw_server_loop_output_dims(struct qw_server *server, output_dims_cb_t cb) {
    struct qw_output *o;
    wl_list_for_each(o, &server->outputs, link) {
        if (!o->wlr_output || !o->wlr_output->enabled) {
            continue;
        }
        int width, height;
        wlr_output_effective_resolution(o->wlr_output, &width, &height);
        cb(o->x, o->y, width, height);
    }
}

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

const char *qw_server_get_sym_from_code(struct qw_server *server, int code) { return NULL; }

static void qw_server_handle_new_output(struct wl_listener *listener, void *data) {
    struct qw_server *server = wl_container_of(listener, server, new_output);
    struct wlr_output *output = data;

    qw_server_output_new(server, output);
}

static void qw_server_handle_output_layout_change(struct wl_listener *listener, void *data) {
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
        // TODO: update current output
    }
    wl_list_for_each(o, &server->outputs, link) {
        if (o->wlr_output->enabled && !wlr_output_layout_get(server->output_layout, o->wlr_output))
            wlr_output_layout_add_auto(server->output_layout, o->wlr_output);
    }

    wl_list_for_each(o, &server->outputs, link) {
        if (!o->wlr_output->enabled)
            continue;
        config_head = wlr_output_configuration_head_v1_create(config, o->wlr_output);

        struct wlr_box box;
        wlr_output_layout_get_box(server->output_layout, o->wlr_output, &box);
        config_head->state.x = o->x = box.x;
        config_head->state.y = o->y = box.y;

        wlr_scene_output_set_position(o->scene, o->x, o->y);
    }

    wlr_output_manager_v1_set_configuration(server->output_mgr, config);
    server->on_screen_change_cb(server->cb_data);
}

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

static void qw_server_handle_output_manager_apply(struct wl_listener *listener, void *data) {
    struct qw_server *server = wl_container_of(listener, server, output_manager_apply);
    struct wlr_output_configuration_v1 *config = (struct wlr_output_configuration_v1 *)data;
    qw_server_output_manager_reconfigure(server, config, true);
}

static void qw_server_handle_output_manager_test(struct wl_listener *listener, void *data) {
    struct qw_server *server = wl_container_of(listener, server, output_manager_test);
    struct wlr_output_configuration_v1 *config = (struct wlr_output_configuration_v1 *)data;
    qw_server_output_manager_reconfigure(server, config, false);
}

static void qw_server_new_pointer(struct qw_server *server, struct wlr_input_device *device) {
    wlr_cursor_attach_input_device(server->cursor->cursor, device);
}

static void qw_server_handle_new_input(struct wl_listener *listener, void *data) {
    struct qw_server *server = wl_container_of(listener, server, new_input);
    struct wlr_input_device *device = data;
    switch (device->type) {
    case WLR_INPUT_DEVICE_KEYBOARD:
        qw_server_keyboard_new(server, device);
        break;
    case WLR_INPUT_DEVICE_POINTER:
        qw_server_new_pointer(server, device);
        break;
    default:
        break;
    }
    uint32_t caps = WL_SEAT_CAPABILITY_POINTER;
    if (!wl_list_empty(&server->keyboards)) {
        caps |= WL_SEAT_CAPABILITY_KEYBOARD;
    }
    wlr_seat_set_capabilities(server->seat, caps);
}

static void qw_server_handle_new_xdg_toplevel(struct wl_listener *listener, void *data) {
    struct qw_server *server = wl_container_of(listener, server, new_xdg_toplevel);
    struct wlr_xdg_toplevel *xdg_toplevel = data;
    qw_server_xdg_view_new(server, xdg_toplevel);
}

static void qw_server_handle_new_decoration(struct wl_listener *listener, void *data) {
    struct wlr_xdg_toplevel_decoration_v1 *decoration = data;
    qw_xdg_view_decoration_new(decoration->toplevel->base->data, decoration);
}

struct qw_view *qw_server_view_at(struct qw_server *server, double lx, double ly,
                                  struct wlr_surface **surface, double *sx, double *sy) {
    struct wlr_scene_node *node = wlr_scene_node_at(&server->scene->tree.node, lx, ly, sx, sy);
    if (!node || node->type != WLR_SCENE_NODE_BUFFER) {
        return NULL;
    }
    struct wlr_scene_buffer *scene_buffer = wlr_scene_buffer_from_node(node);
    struct wlr_scene_surface *scene_surface = wlr_scene_surface_try_from_buffer(scene_buffer);
    if (!scene_surface) {
        return NULL;
    }

    // TODO: fix when we have internal windows working
    *surface = scene_surface->surface;
    struct wlr_scene_tree *tree = node->parent;
    while (!tree && !tree->node.data) {
        tree = tree->node.parent;
    }
    return tree->node.data;
}

struct qw_server *qw_server_create() {
    wlr_log_init(WLR_INFO, NULL);
    struct qw_server *server = calloc(1, sizeof(*server));
    if (!server) {
        wlr_log(WLR_ERROR, "failed to create qw_server struct");
        return NULL;
    }

    server->display = wl_display_create();
    server->backend = wlr_backend_autocreate(wl_display_get_event_loop(server->display), NULL);
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

    wl_list_init(&server->outputs);
    server->output_layout = wlr_output_layout_create(server->display);
    server->output_layout_change.notify = qw_server_handle_output_layout_change;
    wlr_xdg_output_manager_v1_create(server->display, server->output_layout);
    wl_signal_add(&server->output_layout->events.change, &server->output_layout_change);
    server->scene_layout = wlr_scene_attach_output_layout(server->scene, server->output_layout);
    server->new_output.notify = qw_server_handle_new_output;
    wl_signal_add(&server->backend->events.new_output, &server->new_output);
    wl_list_init(&server->keyboards);
    server->seat = wlr_seat_create(server->display, "seat0");
    server->cursor = qw_server_cursor_create(server);
    if (!server->cursor) {
        // already logged in the create if failed
        return NULL;
    }
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

    // TODO: XDG activation, gamma control, power manager
    // TODO: handle GPU resets

    // TODO: setup listeners

    return server;
}
