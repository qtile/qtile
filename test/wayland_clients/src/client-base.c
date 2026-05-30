/* client-base.c */

#define _POSIX_C_SOURCE 200809L

#include "client-base.h"

#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>

static const struct client_ops *ops_ptr;

void test_ok(void) {
    puts("OK");
    fflush(stdout);
}

void test_error(const char *fmt, ...) {
    printf("ERROR: ");

    va_list args;
    va_start(args, fmt);
    vprintf(fmt, args);
    va_end(args);

    printf("\n");
    fflush(stdout);
}

void test_message(const char *fmt, ...) {
    va_list args;
    va_start(args, fmt);
    vprintf(fmt, args);
    va_end(args);

    printf("\n");
    fflush(stdout);
}

void do_roundtrip(struct client_state *state) { wl_display_roundtrip(state->display); }

static void registry_global(void *data, struct wl_registry *registry, uint32_t name,
                            const char *interface, uint32_t version) {
    struct client_state *state = data;

    /* Common globals */
    if (strcmp(interface, wl_compositor_interface.name) == 0) {
        state->compositor =
            wl_registry_bind(registry, name, &wl_compositor_interface, version < 4 ? version : 4);

    } else if (strcmp(interface, wl_seat_interface.name) == 0) {
        state->seat =
            wl_registry_bind(registry, name, &wl_seat_interface, version < 7 ? version : 7);

    } else if (strcmp(interface, wl_shm_interface.name) == 0) {
        state->shm = wl_registry_bind(registry, name, &wl_shm_interface, 1);
    }

    if (ops_ptr->registry_global) {
        ops_ptr->registry_global(state, registry, name, interface, version);
    }
}

static void registry_global_remove(void *data, struct wl_registry *registry, uint32_t name) {
    if (ops_ptr->registry_global_remove) {
        ops_ptr->registry_global_remove(data, registry, name);
    }
}

static const struct wl_registry_listener registry_listener = {
    .global = registry_global,
    .global_remove = registry_global_remove,
};

static bool dispatch_line(struct client_state *state, char *line) {
    size_t len = strlen(line);

    while (len > 0 && (line[len - 1] == '\n' || line[len - 1] == '\r')) {
        line[--len] = '\0';
    }

    if (len == 0) {
        return true;
    }

    char *verb = line;
    char *arg = NULL;

    char *sp = strchr(line, ' ');
    if (sp) {
        *sp = '\0';
        arg = sp + 1;
    }

    if (strcmp(verb, "quit") == 0) {
        return false;
    }

    if (ops_ptr->dispatch_command != NULL) {
        return ops_ptr->dispatch_command(state, verb, arg);
    }
}

static void client_state_cleanup(struct client_state *state) {
    if (state->seat) {
        wl_seat_destroy(state->seat);
    }

    if (state->compositor) {
        wl_compositor_destroy(state->compositor);
    }

    if (state->registry) {
        wl_registry_destroy(state->registry);
    }

    if (state->display) {
        wl_display_disconnect(state->display);
    }
}

int client_run(struct client_state *state, const struct client_ops *ops) {
    ops_ptr = ops;

    state->display = wl_display_connect(NULL);
    if (!state->display) {
        fprintf(stderr, "ERROR: failed to connect to display: %s\n", strerror(errno));
        return 1;
    }

    if (ops->setup != NULL) {
        ops->setup(state);
    }

    state->registry = wl_display_get_registry(state->display);

    wl_registry_add_listener(state->registry, &registry_listener, state);

    wl_display_roundtrip(state->display);

    int stdin_flags = fcntl(STDIN_FILENO, F_GETFL, 0);

    fcntl(STDIN_FILENO, F_SETFL, stdin_flags | O_NONBLOCK);

    fprintf(stderr, "ready\n");
    fflush(stderr);

    char line[256];
    size_t pos = 0;

    struct pollfd fds[2] = {
        {
            .fd = STDIN_FILENO,
            .events = POLLIN,
        },
        {
            .fd = wl_display_get_fd(state->display),
            .events = POLLIN,
        },
    };

    bool running = true;

    while (running) {
        wl_display_flush(state->display);

        int ret = poll(fds, 2, -1);

        if (ret < 0) {
            if (errno == EINTR) {
                continue;
            }

            perror("poll");
            break;
        }

        if (fds[1].revents & POLLIN) {
            wl_display_dispatch(state->display);
        }

        if (fds[0].revents & POLLIN) {
            ssize_t n = read(STDIN_FILENO, line + pos, sizeof(line) - pos - 1);

            if (n <= 0) {
                if (n == 0) {
                    break;
                }

                if (errno == EAGAIN) {
                    continue;
                }

                perror("read");
                break;
            }

            pos += (size_t)n;
            line[pos] = '\0';

            char *start = line;
            char *nl;

            while ((nl = strchr(start, '\n')) != NULL) {
                *nl = '\0';

                running = dispatch_line(state, start);

                if (!running) {
                    break;
                }

                start = nl + 1;
            }

            size_t remaining = (size_t)((line + pos) - start);

            memmove(line, start, remaining);

            pos = remaining;
        }
    }

    if (ops->cleanup != NULL) {
        ops->cleanup(state);
    }

    client_state_cleanup(state);

    return 0;
}

/*
Common SHM buffer code
*/

static int create_shm_file(size_t size) {
    char template[] = "/tmp/wayland-test-shm-XXXXXX";
    int fd = mkstemp(template);
    if (fd < 0) {
        return -1;
    }

    unlink(template);

    if (ftruncate(fd, (off_t)size) < 0) {
        close(fd);
        return -1;
    }

    return fd;
}

struct buffer *create_buffer(struct client_state *state, uint32_t width, uint32_t height,
                             uint32_t colour) {
    const uint32_t stride = width * 4;
    const uint32_t size = stride * height;

    int fd = create_shm_file(size);
    if (fd < 0) {
        return NULL;
    }

    void *data = mmap(NULL, size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);

    if (data == MAP_FAILED) {
        close(fd);
        return NULL;
    }

    struct wl_shm_pool *pool = wl_shm_create_pool(state->shm, fd, size);

    struct wl_buffer *buffer =
        wl_shm_pool_create_buffer(pool, 0, width, height, stride, WL_SHM_FORMAT_XRGB8888);

    wl_shm_pool_destroy(pool);
    close(fd);

    if (buffer == NULL) {
        munmap(data, size);
        return NULL;
    }

    /* Fill with given colour */
    uint32_t *pixels = data;
    for (uint32_t i = 0; i < width * height; i++) {
        pixels[i] = colour;
    }

    struct buffer *buf = calloc(1, sizeof(*buf));
    buf->wl_buffer = buffer;
    buf->data = data;
    buf->size = size;

    return buf;
}
