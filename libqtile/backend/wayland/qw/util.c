#include "util.h"
#include <string.h>
#include <wlr/types/wlr_keyboard.h>

int qw_util_get_button_code(uint32_t button) {
    // from linux/input-event-codes.h
    uint32_t mappings[] = {
        // BTN_LEFT
        0x110,
        // BTN_MIDDLE
        0x112,
        // BTN_RIGHT
        0x111,
        BUTTON_SCROLL_UP,
        BUTTON_SCROLL_DOWN,
        BUTTON_SCROLL_LEFT,
        BUTTON_SCROLL_RIGHT,
        // BTN_SIDE
        0x113,
        // BTN_EXTRA
        0x114,
    };
    // we don't use size_t as we're returning an int too
    int n = sizeof(mappings) / sizeof(mappings[0]);
    for (int i = 0; i < n; ++i) {
        if (button == mappings[i]) {
            return i + 1;
        }
    }
    return 0;
}

int qw_util_get_modifier_code(const char *codestr) {
    struct code_mapping {
        const char *name;
        enum wlr_keyboard_modifier mod;
    };

    // clang-format off
    struct code_mapping mappings[] = {
        {"shift", WLR_MODIFIER_SHIFT},
        {"lock", WLR_MODIFIER_CAPS},
        {"control", WLR_MODIFIER_CTRL},
        {"mod1", WLR_MODIFIER_ALT},
        {"mod2", WLR_MODIFIER_MOD2},
        {"mod3", WLR_MODIFIER_MOD3},
        {"mod4", WLR_MODIFIER_LOGO},
        {"mod5", WLR_MODIFIER_MOD5}
    };
    // clang-format on

    size_t n = sizeof(mappings) / sizeof(mappings[0]);
    for (size_t i = 0; i < n; ++i) {
        if (strcmp(codestr, mappings[i].name) == 0) {
            return mappings[i].mod;
        }
    }

    return -1;
}
