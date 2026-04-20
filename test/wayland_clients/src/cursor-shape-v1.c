#include <errno.h>
#include <getopt.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
#include <wayland-client.h>

#include "cursor-shape-v1-client-protocol.h"
#include "xdg-shell-client-protocol.h"

/* ---------------- globals ---------------- */
static bool configured = false;
static uint32_t initial_configure_serial = 0;
static bool running = true;

static struct wl_display *display;
static struct wl_registry *registry;

static struct wl_compositor *compositor;
static struct xdg_wm_base *xdg_wm_base;
static struct wl_shm *shm;

static struct wl_surface *surface;
static struct xdg_toplevel *xdg_toplevel;

static struct wp_cursor_shape_manager_v1 *cursor_manager;
static struct wp_cursor_shape_device_v1 *cursor_device;

static uint32_t cursor_shape = WP_CURSOR_SHAPE_DEVICE_V1_SHAPE_CROSSHAIR;

/* ---------------- shm ---------------- */

static int create_shm_file(size_t size) {
    char name[] = "/tmp/wl-shm-XXXXXX";
    int fd = mkstemp(name);
    unlink(name);

    if (fd < 0)
        return -1;

    if (ftruncate(fd, size) == -1) {
        perror("ftruncate failed");
        exit(EXIT_FAILURE);
    }

    return fd;
}

static struct wl_buffer *create_buffer(struct wl_shm *shm, int width, int height, void **data_out) {
    int stride = width * 4;
    int size = stride * height;

    int fd = create_shm_file(size);
    void *data = mmap(NULL, size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);

    struct wl_shm_pool *pool = wl_shm_create_pool(shm, fd, size);
    struct wl_buffer *buf =
        wl_shm_pool_create_buffer(pool, 0, width, height, stride, WL_SHM_FORMAT_XRGB8888);

    wl_shm_pool_destroy(pool);
    close(fd);

    *data_out = data;
    return buf;
}

/* ---------------- xdg-shell ---------------- */

static void xdg_wm_base_ping(void *data, struct xdg_wm_base *wm_base, uint32_t serial) {
    xdg_wm_base_pong(wm_base, serial);
}

static const struct xdg_wm_base_listener xdg_wm_base_listener = {.ping = xdg_wm_base_ping};

static void xdg_surface_handle_configure(void *data, struct xdg_surface *xdg_surface,
                                         uint32_t serial) {
    if (configured) {
        xdg_surface_ack_configure(xdg_surface, serial);
        wl_surface_commit(surface);
    } else {
        initial_configure_serial = serial;
        configured = true;
    }
}

static const struct xdg_surface_listener xdg_surface_listener = {.configure =
                                                                     xdg_surface_handle_configure};

static void xdg_toplevel_handle_configure(void *data, struct xdg_toplevel *toplevel, int32_t width,
                                          int32_t height, struct wl_array *states) {
    // This event is sent before xdg_surface.configure. It specifies the
    // compositor's desired size and advertises active states for the toplevel.
    // A resizable client would store these, and resize itself when receiving
    // the xdg_surface.configure event.
}

static void xdg_toplevel_handle_close(void *data, struct xdg_toplevel *xdg_toplevel) {
    // Stop running if the user requests to close the toplevel
    running = false;
}

static const struct xdg_toplevel_listener xdg_toplevel_listener = {
    .configure = xdg_toplevel_handle_configure,
    .close = xdg_toplevel_handle_close,
};

/* ---------------- cursor ---------------- */

static uint32_t parse_cursor_shape(const char *name) {
    if (strcmp(name, "default") == 0)
        return WP_CURSOR_SHAPE_DEVICE_V1_SHAPE_DEFAULT;
    if (strcmp(name, "crosshair") == 0)
        return WP_CURSOR_SHAPE_DEVICE_V1_SHAPE_CROSSHAIR;
    if (strcmp(name, "pointer") == 0)
        return WP_CURSOR_SHAPE_DEVICE_V1_SHAPE_POINTER;
    if (strcmp(name, "grab") == 0)
        return WP_CURSOR_SHAPE_DEVICE_V1_SHAPE_GRAB;
    if (strcmp(name, "text") == 0)
        return WP_CURSOR_SHAPE_DEVICE_V1_SHAPE_TEXT;
    if (strcmp(name, "wait") == 0)
        return WP_CURSOR_SHAPE_DEVICE_V1_SHAPE_WAIT;
    if (strcmp(name, "help") == 0)
        return WP_CURSOR_SHAPE_DEVICE_V1_SHAPE_HELP;

    fprintf(stderr, "Unknown cursor shape: %s\n", name);
    fprintf(stderr, "Available shapes: default, crosshair, pointer, hand, text, wait, help\n");
    exit(EXIT_FAILURE);
}

static void set_cursor(uint32_t serial) {
    if (!cursor_device)
        return;

    wp_cursor_shape_device_v1_set_shape(cursor_device, serial, cursor_shape);
}

/* ---------------- pointer ---------------- */

static void pointer_enter(void *data, struct wl_pointer *pointer, uint32_t serial,
                          struct wl_surface *surface, wl_fixed_t x, wl_fixed_t y) {
    (void)data;
    (void)pointer;
    (void)surface;
    (void)x;
    (void)y;

    set_cursor(serial);
}

static void pointer_motion(void *data, struct wl_pointer *pointer, uint32_t time, wl_fixed_t x,
                           wl_fixed_t y) {
    (void)data;
    (void)pointer;
    (void)time;
    (void)x;
    (void)y;
}

static void pointer_leave(void *data, struct wl_pointer *pointer, uint32_t serial,
                          struct wl_surface *surface) {
    (void)data;
    (void)pointer;
    (void)serial;
    (void)surface;
}

static void pointer_handle_button(void *data, struct wl_pointer *pointer, uint32_t serial,
                                  uint32_t time, uint32_t button, uint32_t state) {}

static void pointer_handle_axis(void *data, struct wl_pointer *pointer, uint32_t time_ms,
                                uint32_t axis, wl_fixed_t value) {}

static const struct wl_pointer_listener pointer_listener = {.enter = pointer_enter,
                                                            .leave = pointer_leave,
                                                            .motion = pointer_motion,
                                                            .button = pointer_handle_button,
                                                            .axis = pointer_handle_axis};

static void seat_handle_capabilities(void *data, struct wl_seat *seat, uint32_t capabilities) {
    // If the wl_seat has the pointer capability, start listening to pointer
    // events
    if (capabilities & WL_SEAT_CAPABILITY_POINTER) {
        struct wl_pointer *pointer = wl_seat_get_pointer(seat);
        wl_pointer_add_listener(pointer, &pointer_listener, seat);

        cursor_device = wp_cursor_shape_manager_v1_get_pointer(cursor_manager, pointer);
    }
}

static const struct wl_seat_listener seat_listener = {
    .capabilities = seat_handle_capabilities,
};

/* ---------------- registry ---------------- */

static void handle_global(void *data, struct wl_registry *registry, uint32_t name,
                          const char *interface, uint32_t version) {
    (void)data;
    (void)version;

    if (strcmp(interface, wl_compositor_interface.name) == 0)
        compositor = wl_registry_bind(registry, name, &wl_compositor_interface, 4);

    if (strcmp(interface, xdg_wm_base_interface.name) == 0) {
        xdg_wm_base = wl_registry_bind(registry, name, &xdg_wm_base_interface, 1);
        xdg_wm_base_add_listener(xdg_wm_base, &xdg_wm_base_listener, NULL);
    }

    if (strcmp(interface, wl_seat_interface.name) == 0) {
        struct wl_seat *seat = wl_registry_bind(registry, name, &wl_seat_interface, 1);
        wl_seat_add_listener(seat, &seat_listener, NULL);
    }

    if (strcmp(interface, wl_shm_interface.name) == 0)
        shm = wl_registry_bind(registry, name, &wl_shm_interface, 1);

    if (strcmp(interface, wp_cursor_shape_manager_v1_interface.name) == 0)
        cursor_manager = wl_registry_bind(registry, name, &wp_cursor_shape_manager_v1_interface, 1);
}

static void handle_global_remove(void *data, struct wl_registry *registry, uint32_t name) {}

static const struct wl_registry_listener registry_listener = {
    .global = handle_global, .global_remove = handle_global_remove};

/* ---------------- main ---------------- */

int main(int argc, char *argv[]) {
    // Parse command line arguments
    int opt;
    while ((opt = getopt(argc, argv, "c:h")) != -1) {
        switch (opt) {
        case 'c':
            cursor_shape = parse_cursor_shape(optarg);
            break;
        case 'h':
            printf("Usage: %s [-c cursor_shape]\n", argv[0]);
            printf(
                "  -c: Set cursor shape (default, crosshair, pointer, grab, text, wait, help)\n");
            return 0;
        default:
            fprintf(stderr, "Usage: %s [-c cursor_shape]\n", argv[0]);
            return 1;
        }
    }

    display = wl_display_connect(NULL);
    if (!display) {
        fprintf(stderr, "failed to connect wayland\n");
        return 1;
    }

    registry = wl_display_get_registry(display);
    wl_registry_add_listener(registry, &registry_listener, NULL);
    if (wl_display_roundtrip(display) == -1) {
        return 1;
    };

    if (!compositor || !xdg_wm_base || !shm || !cursor_manager) {
        fprintf(stderr, "missing required globals\n");
        return 1;
    }

    /* surface */
    surface = wl_compositor_create_surface(compositor);
    struct xdg_surface *xdg_surface = xdg_wm_base_get_xdg_surface(xdg_wm_base, surface);
    xdg_toplevel = xdg_surface_get_toplevel(xdg_surface);

    xdg_surface_add_listener(xdg_surface, &xdg_surface_listener, NULL);
    xdg_toplevel_add_listener(xdg_toplevel, &xdg_toplevel_listener, NULL);

    // Perform the initial commit and wait for the first configure event
    wl_surface_commit(surface);
    while (!configured) {
        if (wl_display_dispatch(display) == -1) {
            return 1;
        }
    }

    /* buffer */
    void *pixels;
    struct wl_buffer *buffer = create_buffer(shm, 300, 300, &pixels);
    // Fill buffer with grey
    memset(pixels, 0x80, 300 * 300 * 4);

    wl_surface_attach(surface, buffer, 0, 0);
    xdg_surface_ack_configure(xdg_surface, initial_configure_serial);
    wl_surface_commit(surface);

    printf("running...\n");

    while (wl_display_dispatch(display) != -1 && running) {
    }

    xdg_toplevel_destroy(xdg_toplevel);
    xdg_surface_destroy(xdg_surface);
    wl_surface_destroy(surface);
    wl_buffer_destroy(buffer);

    return 0;
}
