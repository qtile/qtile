#ifndef MAC_DISPLAY_H
#define MAC_DISPLAY_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

// Must be called before any AppKit API (NSWindow, NSView, etc.).
// Initialises [NSApplication sharedApplication] and sets the activation policy
// to accessory (no dock icon, no menu bar).
void mac_init_app(void);

struct mac_output {
    char *name;
    int x;
    int y;
    int width;
    int height;
};

int mac_get_outputs(struct mac_output **outputs, size_t *count);
void mac_free_outputs(struct mac_output *outputs, size_t count);
void mac_get_mouse_position(int *x, int *y);
void mac_warp_pointer(int x, int y);
void mac_poll_runloop(void);
void mac_simulate_keypress(uint32_t keycode, uint64_t flags);
void mac_inhibit_idle(bool inhibit);

#endif
