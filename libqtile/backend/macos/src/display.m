#include "display.h"
#import <ApplicationServices/ApplicationServices.h>
#import <Foundation/Foundation.h>
#import <IOKit/pwr_mgt/IOPMLib.h>

static IOPMAssertionID g_idle_assertion = kIOPMNullAssertionID;

void mac_inhibit_idle(bool inhibit) {
    if (inhibit && g_idle_assertion == kIOPMNullAssertionID) {
        // Prevent display sleep and system idle sleep while qtile inhibits idle.
        IOPMAssertionCreateWithName(kIOPMAssertionTypeNoDisplaySleep, kIOPMAssertionLevelOn,
                                    CFSTR("qtile idle inhibitor"), &g_idle_assertion);
    } else if (!inhibit && g_idle_assertion != kIOPMNullAssertionID) {
        IOPMAssertionRelease(g_idle_assertion);
        g_idle_assertion = kIOPMNullAssertionID;
    }
}

int mac_get_outputs(struct mac_output **outputs, size_t *count) {
    uint32_t displayCount = 0;
    if (CGGetActiveDisplayList(0, NULL, &displayCount) != kCGErrorSuccess)
        return 1;

    CGDirectDisplayID *displays = malloc(sizeof(CGDirectDisplayID) * displayCount);
    if (!displays) {
        return 1;
    }
    CGGetActiveDisplayList(displayCount, displays, &displayCount);

    *count = displayCount;
    *outputs = malloc(sizeof(struct mac_output) * displayCount);
    if (!*outputs) {
        free(displays);
        return 1;
    }

    for (uint32_t i = 0; i < displayCount; i++) {
        // CGDisplayBounds returns coordinates in the macOS global screen
        // coordinate space, where the primary display's top-left is (0, 0).
        // Secondary displays positioned above or to the left of the primary
        // may have negative X or Y origins (macOS uses a flipped Y-axis).
        // Callers must handle negative values when computing window positions
        // or layout geometry.
        //
        // CGDisplayBounds returns logical points, not physical pixels.  On
        // Retina/HiDPI displays the returned dimensions are half the physical
        // resolution (e.g. 1440x900 for a 2880x1800 panel).  Use
        // CGDisplayPixelsWide / CGDisplayPixelsHigh if physical pixel counts
        // are needed instead.
        CGRect rect = CGDisplayBounds(displays[i]);
        (*outputs)[i].x = (int)rect.origin.x;
        (*outputs)[i].y = (int)rect.origin.y;
        (*outputs)[i].width = (int)rect.size.width;
        (*outputs)[i].height = (int)rect.size.height;

        // Use CGDisplayUnitNumber to produce a stable, hardware-tied name
        // that survives display reconnections and enumeration-order changes,
        // unlike a loop index which shifts when displays are added or removed.
        char buf[32];
        snprintf(buf, sizeof(buf), "display-%u", CGDisplayUnitNumber(displays[i]));
        (*outputs)[i].name = strdup(buf);
    }

    free(displays);
    return 0;
}

void mac_free_outputs(struct mac_output *outputs, size_t count) {
    for (size_t i = 0; i < count; i++) {
        free(outputs[i].name);
    }
    free(outputs);
}

void mac_get_mouse_position(int *x, int *y) {
    CGEventRef event = CGEventCreate(NULL);
    if (!event) {
        *x = 0;
        *y = 0;
        return;
    }
    CGPoint point = CGEventGetLocation(event);
    CFRelease(event);
    *x = (int)point.x;
    *y = (int)point.y;
}

void mac_warp_pointer(int x, int y) {
    CGPoint point = CGPointMake(x, y);
    CGWarpMouseCursorPosition(point);
}

void mac_poll_runloop(void) { CFRunLoopRunInMode(kCFRunLoopDefaultMode, 0, true); }

void mac_simulate_keypress(uint32_t keycode, uint64_t flags) {
    CGEventSourceRef source = CGEventSourceCreate(kCGEventSourceStateHIDSystemState);
    if (!source)
        return;

    CGEventRef down = CGEventCreateKeyboardEvent(source, (CGKeyCode)keycode, true);
    if (down) {
        CGEventSetFlags(down, (CGEventFlags)flags);
        CGEventPost(kCGHIDEventTap, down);
        CFRelease(down);
    }

    CGEventRef up = CGEventCreateKeyboardEvent(source, (CGKeyCode)keycode, false);
    if (up) {
        CGEventSetFlags(up, (CGEventFlags)flags);
        CGEventPost(kCGHIDEventTap, up);
        CFRelease(up);
    }

    CFRelease(source);
}
