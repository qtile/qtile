#ifndef UTIL_H
#define UTIL_H

#include <stdint.h>

// The base is 0x299 defined at linux/input-event-codes.h
enum BUTTON_SCROLL {
    BUTTON_SCROLL_UP = 0x300,
    BUTTON_SCROLL_DOWN = 0x301,
    BUTTON_SCROLL_LEFT = 0x302,
    BUTTON_SCROLL_RIGHT = 0x303,
};

int qw_util_get_button_code(uint32_t button);
int qw_util_get_modifier_code(const char *codestr);

#endif /* UTIL_H */
