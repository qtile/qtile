#ifndef CLIENT_BASE_H
#define CLIENT_BASE_H

#include <stdbool.h>
#include <stdint.h>
#include <wayland-client.h>

struct buffer {
    struct wl_buffer *wl_buffer;
    void *data;
    size_t size;
};
struct client_state {
    struct wl_display *display;
    struct wl_registry *registry;
    struct wl_compositor *compositor;
    struct wl_seat *seat;
    struct wl_shm *shm;
};

struct client_ops {
    void (*setup)(struct client_state *state);

    void (*registry_global)(struct client_state *state, struct wl_registry *registry, uint32_t name,
                            const char *interface, uint32_t version);

    void (*registry_global_remove)(struct client_state *state, struct wl_registry *registry,
                                   uint32_t name);

    bool (*dispatch_command)(struct client_state *state, const char *command, const char *arg);

    void (*cleanup)(struct client_state *state);
};

void do_roundtrip(struct client_state *state);

int client_run(struct client_state *state, const struct client_ops *ops);

void test_ok(void);
void test_error(const char *fmt, ...);
void test_message(const char *fmt, ...);
void test_true(void);
void test_false(void);

struct buffer *create_buffer(struct client_state *state, uint32_t width, uint32_t height,
                             uint32_t colour);
void destroy_buffer(struct buffer *buf);

#endif /* CLIENT_BASE_H */
