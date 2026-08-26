#define _GNU_SOURCE

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
#include <xkbcommon/xkbcommon.h>

#include "client-base.h"
#include "virtual-keyboard-unstable-v1-client-protocol.h"

// Standard XKB modifier bitmasks for US QWERTY keymap
#define MOD_SHIFT (1U << 0)   // 0x01
#define MOD_CONTROL (1U << 2) // 0x04
#define MOD_ALT (1U << 3)     // 0x08
#define MOD_SUPER (1U << 6)   // 0x40

struct test_state {
    struct client_state base;
    struct zwp_virtual_keyboard_manager_v1 *vkeyboard_mgr;
    struct zwp_virtual_keyboard_v1 *vkeyboard;
    uint32_t active_mods;
};

// Standard US QWERTY keymap in XKB v1 format
static const char *default_xkb_keymap = "xkb_keymap {\n"
                                        "   xkb_keycodes  { include \"evdev+aliases(qwerty)\" };\n"
                                        "   xkb_types     { include \"complete\" };\n"
                                        "   xkb_compat    { include \"complete\" };\n"
                                        "   xkb_symbols   { include \"pc+us+inet(evdev)\" };\n"
                                        "   xkb_geometry  { include \"pc(pc105)\" };\n"
                                        "};\n";

static int create_memfd_with_data(const char *data, size_t size) {
    int fd = memfd_create("test-virtual-keyboard-keymap", MFD_CLOEXEC);
    if (fd < 0) {
        return -1;
    }

    // Expand memory size
    if (ftruncate(fd, size) < 0) {
        close(fd);
        return -1;
    }

    // Memory map and write the keymap string into the fd
    void *ptr = mmap(NULL, size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    if (ptr == MAP_FAILED) {
        close(fd);
        return -1;
    }

    memcpy(ptr, data, size);
    munmap(ptr, size);

    return fd;
}

int send_virtual_keyboard_keymap(struct zwp_virtual_keyboard_v1 *vkeyboard) {
    size_t keymap_size = strlen(default_xkb_keymap) + 1; // Include null terminator

    int fd = create_memfd_with_data(default_xkb_keymap, keymap_size);
    if (fd < 0) {
        return -1;
    }

    zwp_virtual_keyboard_v1_keymap(vkeyboard, WL_KEYBOARD_KEYMAP_FORMAT_XKB_V1, fd,
                                   (uint32_t)keymap_size);

    // Compositor duplicates/maps the fd upon receiving the request; we close our local fd
    close(fd);
    return 0;
}

static void registry_handler(struct client_state *base, struct wl_registry *registry, uint32_t name,
                             const char *interface, uint32_t version) {
    struct test_state *state = (struct test_state *)base;

    if (strcmp(interface, zwp_virtual_keyboard_manager_v1_interface.name) == 0) {
        state->vkeyboard_mgr =
            wl_registry_bind(registry, name, &zwp_virtual_keyboard_manager_v1_interface, 1);
    }

    if (state->vkeyboard == NULL && state->vkeyboard_mgr != NULL && state->base.seat != NULL) {
        state->vkeyboard = zwp_virtual_keyboard_manager_v1_create_virtual_keyboard(
            state->vkeyboard_mgr, state->base.seat);
        send_virtual_keyboard_keymap(state->vkeyboard);
    }
}

static void send_modifiers(struct test_state *state) {
    if (state->vkeyboard == NULL) {
        test_error("no virtual keyboard.");
        return;
    }

    // Send updated depressed modifiers mask to compositor
    zwp_virtual_keyboard_v1_modifiers(state->vkeyboard, state->active_mods, 0, 0, 0);
    do_roundtrip(&state->base);
    test_ok();
}

static void send_key(struct test_state *state, uint32_t keycode, uint32_t key_state) {
    if (state->vkeyboard == NULL) {
        test_error("no virtual keyboard.");
        return;
    }

    // Ensure compositor has active modifier state before sending keypress
    send_modifiers(state);

    uint32_t time_ms = 0;
    zwp_virtual_keyboard_v1_key(state->vkeyboard, time_ms, keycode, key_state);
    // wl_display_flush(client->display);
    do_roundtrip(&state->base);
    test_ok();
}

static bool dispatch_command(struct client_state *base, const char *cmd, const char *arg) {
    struct test_state *state = (struct test_state *)base;

    if (strcmp(cmd, "press") == 0) {
        if (arg == NULL) {
            test_error("press requires a keycode.");
        } else {
            send_key(state, atoi(arg), WL_KEYBOARD_KEY_STATE_PRESSED);
        }
    } else if (strcmp(cmd, "release") == 0) {
        if (arg == NULL) {
            test_error("release requires a keycode.");
        } else {
            send_key(state, atoi(arg), WL_KEYBOARD_KEY_STATE_RELEASED);
        }
    } else if (strcmp(cmd, "tap") == 0) {
        if (arg == NULL) {
            test_error("tap requires a keycode.");
        } else {
            send_key(state, atoi(arg), WL_KEYBOARD_KEY_STATE_PRESSED);
            send_key(state, atoi(arg), WL_KEYBOARD_KEY_STATE_RELEASED);
        }
    } else if (strcmp(cmd, "set_modifier") == 0) {
        if (arg == NULL) {
            test_error("set_modifier requires a modifier name.");
        } else if (strcmp(arg, "shift") == 0) {
            state->active_mods |= MOD_SHIFT;
            send_modifiers(state);
        } else if (strcmp(arg, "control") == 0) {
            state->active_mods |= MOD_CONTROL;
            send_modifiers(state);
        } else if (strcmp(arg, "alt") == 0) {
            state->active_mods |= MOD_ALT;
            send_modifiers(state);
        } else if (strcmp(arg, "super") == 0) {
            state->active_mods |= MOD_SUPER;
            send_modifiers(state);
        } else {
            test_error("Unknown modifier: %s", arg);
        }
    } else if (strcmp(cmd, "clear_modifiers") == 0) {
        state->active_mods = 0;
        send_modifiers(state);
    } else if (strcmp(cmd, "quit") == 0) {
        return false;
    }
    return true;
}

void cleanup(struct client_state *base) {
    struct test_state *state = (struct test_state *)base;

    if (state->vkeyboard) {
        zwp_virtual_keyboard_v1_destroy(state->vkeyboard);
    }
    if (state->vkeyboard_mgr) {
        zwp_virtual_keyboard_manager_v1_destroy(state->vkeyboard_mgr);
    }
}

int main(void) {
    struct test_state state = {0};

    const struct client_ops ops = {.registry_global = registry_handler,
                                   .dispatch_command = dispatch_command,
                                   .cleanup = cleanup};

    return client_run(&state.base, &ops);
}
