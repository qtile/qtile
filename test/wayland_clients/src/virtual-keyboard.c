/*
 * virtual-keyboard.c
 *
 * Test client for the zwp_virtual_keyboard_v1 protocol. It ships a
 * client-provided xkb keymap (e.g. layouts "us,ru") to the compositor, lets the
 * test select the active layout group, and injects raw evdev key presses. This
 * exercises the C backend's keybinding keysym resolution
 * (qw_keyboard_handle_key) under a non-primary active layout.
 *
 * Line protocol commands:
 *   keymap <layouts>   build "us,ru"-style keymap and attach it to the keyboard
 *   group <n>          make layout index <n> the active group (modifiers request)
 *   press <evdev>      send a key press for the given evdev keycode (KEY_R = 19)
 *   release <evdev>    send a key release for the given evdev keycode
 */

#define _POSIX_C_SOURCE 200809L

#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <time.h>
#include <unistd.h>

#include <xkbcommon/xkbcommon.h>

#include "client-base.h"

#include "virtual-keyboard-unstable-v1-client-protocol.h"

struct test_state {
    struct client_state base;

    struct zwp_virtual_keyboard_manager_v1 *vkbd_manager;
    struct zwp_virtual_keyboard_v1 *vkbd;
    bool has_keymap;
    uint32_t time_msec;
};

static uint32_t next_time(struct test_state *state) {
    /* wlroots only requires monotonically increasing event timestamps. */
    return ++state->time_msec;
}

static int write_keymap_fd(const char *keymap, size_t size) {
    char template[] = "/tmp/qtile-vkbd-keymap-XXXXXX";
    int fd = mkstemp(template);
    if (fd < 0) {
        return -1;
    }
    unlink(template);

    if (ftruncate(fd, (off_t)size) < 0) {
        close(fd);
        return -1;
    }

    void *data = mmap(NULL, size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    if (data == MAP_FAILED) {
        close(fd);
        return -1;
    }

    memcpy(data, keymap, size);
    munmap(data, size);

    return fd;
}

static void cmd_keymap(struct test_state *state, const char *arg) {
    if (state->vkbd_manager == NULL) {
        test_error("zwp_virtual_keyboard_manager_v1 not advertised by compositor");
        return;
    }
    if (state->base.seat == NULL) {
        test_error("wl_seat not available");
        return;
    }
    if (arg == NULL) {
        test_error("usage: keymap <layouts>");
        return;
    }

    struct xkb_context *context = xkb_context_new(XKB_CONTEXT_NO_FLAGS);
    if (context == NULL) {
        test_error("failed to create xkb context");
        return;
    }

    struct xkb_rule_names names = {.layout = arg};
    struct xkb_keymap *keymap =
        xkb_keymap_new_from_names(context, &names, XKB_KEYMAP_COMPILE_NO_FLAGS);
    if (keymap == NULL) {
        xkb_context_unref(context);
        test_error("failed to compile keymap for layouts '%s'", arg);
        return;
    }

    char *keymap_str = xkb_keymap_get_as_string(keymap, XKB_KEYMAP_FORMAT_TEXT_V1);
    xkb_keymap_unref(keymap);
    xkb_context_unref(context);

    if (keymap_str == NULL) {
        test_error("failed to serialize keymap");
        return;
    }

    size_t size = strlen(keymap_str) + 1;
    int fd = write_keymap_fd(keymap_str, size);
    free(keymap_str);

    if (fd < 0) {
        test_error("failed to create keymap fd");
        return;
    }

    if (state->vkbd == NULL) {
        state->vkbd = zwp_virtual_keyboard_manager_v1_create_virtual_keyboard(state->vkbd_manager,
                                                                              state->base.seat);
    }

    zwp_virtual_keyboard_v1_keymap(state->vkbd, WL_KEYBOARD_KEYMAP_FORMAT_XKB_V1, fd,
                                   (uint32_t)size);
    close(fd);

    do_roundtrip(&state->base);
    state->has_keymap = true;
    test_ok();
}

static void cmd_group(struct test_state *state, const char *arg) {
    if (state->vkbd == NULL || !state->has_keymap) {
        test_error("keymap not set");
        return;
    }
    if (arg == NULL) {
        test_error("usage: group <n>");
        return;
    }

    uint32_t group = (uint32_t)atoi(arg);
    zwp_virtual_keyboard_v1_modifiers(state->vkbd, 0, 0, 0, group);
    do_roundtrip(&state->base);
    test_ok();
}

static void cmd_key(struct test_state *state, const char *arg, uint32_t key_state) {
    if (state->vkbd == NULL || !state->has_keymap) {
        test_error("keymap not set");
        return;
    }
    if (arg == NULL) {
        test_error("usage: press/release <evdev-keycode>");
        return;
    }

    uint32_t keycode = (uint32_t)atoi(arg);
    zwp_virtual_keyboard_v1_key(state->vkbd, next_time(state), keycode, key_state);
    do_roundtrip(&state->base);
    test_ok();
}

static void registry_handler(struct client_state *base, struct wl_registry *registry, uint32_t name,
                             const char *interface, uint32_t version) {
    struct test_state *state = (struct test_state *)base;

    if (strcmp(interface, zwp_virtual_keyboard_manager_v1_interface.name) == 0) {
        state->vkbd_manager = wl_registry_bind(
            registry, name, &zwp_virtual_keyboard_manager_v1_interface, version < 1 ? version : 1);
    }
}

static bool dispatch_command(struct client_state *base, const char *cmd, const char *arg) {
    struct test_state *state = (struct test_state *)base;

    if (strcmp(cmd, "keymap") == 0)
        cmd_keymap(state, arg);
    else if (strcmp(cmd, "group") == 0)
        cmd_group(state, arg);
    else if (strcmp(cmd, "press") == 0)
        cmd_key(state, arg, WL_KEYBOARD_KEY_STATE_PRESSED);
    else if (strcmp(cmd, "release") == 0)
        cmd_key(state, arg, WL_KEYBOARD_KEY_STATE_RELEASED);
    else
        test_error("unknown command '%s'", cmd);

    return true;
}

static void cleanup(struct client_state *base) {
    struct test_state *state = (struct test_state *)base;

    if (state->vkbd) {
        zwp_virtual_keyboard_v1_destroy(state->vkbd);
    }
    if (state->vkbd_manager) {
        zwp_virtual_keyboard_manager_v1_destroy(state->vkbd_manager);
    }
}

int main(void) {
    struct test_state state = {0};

    const struct client_ops ops = {
        .registry_global = registry_handler,
        .dispatch_command = dispatch_command,
        .cleanup = cleanup,
    };

    return client_run(&state.base, &ops);
}
