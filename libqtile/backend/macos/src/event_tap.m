#include "event_tap.h"
#import <ApplicationServices/ApplicationServices.h>
#import <Foundation/Foundation.h>

static CFMachPortRef eventTap = NULL;
static CFRunLoopSourceRef runLoopSource = NULL;
static CFRunLoopRef g_event_loop = NULL;
static event_tap_cb g_callback = NULL;
static void *g_userdata = NULL;

static CGEventRef eventTapCallback(CGEventTapProxy proxy, CGEventType type, CGEventRef event,
                                   void *refcon) {
    if (g_callback) {
        CGEventFlags flags = CGEventGetFlags(event);
        uint64_t keycode = 0;

        if (type == kCGEventKeyDown || type == kCGEventKeyUp || type == kCGEventFlagsChanged) {
            keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode);
        } else if (type == kCGEventScrollWheel) {
            // Vertical axis: positive delta = scroll up (button 4), negative = down (button 5).
            int64_t delta1 = CGEventGetIntegerValueField(event, kCGScrollWheelEventDeltaAxis1);
            uint32_t vbutton = (delta1 != 0) ? ((delta1 > 0) ? 4 : 5) : 0;
            // Horizontal axis: positive delta = scroll left (button 6), negative = right (7).
            int64_t delta2 = CGEventGetIntegerValueField(event, kCGScrollWheelEventDeltaAxis2);
            uint32_t hbutton = (delta2 != 0) ? ((delta2 > 0) ? 6 : 7) : 0;
            // Pack both into keycode: upper 16 bits = horizontal button, lower 16 = vertical.
            keycode = ((uint64_t)hbutton << 16) | vbutton;
        }

        if (g_callback((uint32_t)type, (uint64_t)flags, (uint32_t)keycode, g_userdata)) {
            // Swallow event
            return NULL;
        }
    }
    return event;
}

int mac_event_tap_start(event_tap_cb callback, void *userdata) {
    g_callback = callback;
    g_userdata = userdata;

    CGEventMask eventMask =
        (1 << kCGEventKeyDown) | (1 << kCGEventKeyUp) | (1 << kCGEventFlagsChanged) |
        (1 << kCGEventLeftMouseDown) | (1 << kCGEventLeftMouseUp) | (1 << kCGEventRightMouseDown) |
        (1 << kCGEventRightMouseUp) | (1 << kCGEventOtherMouseDown) | (1 << kCGEventOtherMouseUp) |
        (1 << kCGEventScrollWheel) | (1 << kCGEventMouseMoved) | (1 << kCGEventLeftMouseDragged) |
        (1 << kCGEventRightMouseDragged);

    eventTap = CGEventTapCreate(kCGSessionEventTap, kCGHeadInsertEventTap, 0, eventMask,
                                eventTapCallback, NULL);

    if (!eventTap) {
        NSLog(@"Failed to create event tap");
        return 1;
    }

    runLoopSource = CFMachPortCreateRunLoopSource(kCFAllocatorDefault, eventTap, 0);
    CGEventTapEnable(eventTap, true);

    // Add the source and run the loop on the same background thread so that
    // eventTapCallback is actually invoked.  CFRunLoopAddSource must use the
    // same CFRunLoopRef that CFRunLoopRun will spin.
    dispatch_async(dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_DEFAULT, 0), ^{
        g_event_loop = CFRunLoopGetCurrent();
        CFRunLoopAddSource(g_event_loop, runLoopSource, kCFRunLoopCommonModes);
        CFRunLoopRun();
        g_event_loop = NULL;
    });

    return 0;
}

void mac_event_tap_stop(void) {
    if (g_event_loop) {
        CFRunLoopStop(g_event_loop);
        g_event_loop = NULL;
    }
    if (eventTap) {
        CGEventTapEnable(eventTap, false);
        CFMachPortInvalidate(eventTap);
        CFRelease(eventTap);
        eventTap = NULL;
    }
    if (runLoopSource) {
        CFRelease(runLoopSource);
        runLoopSource = NULL;
    }
}

double mac_get_idle_time(void) {
    return CGEventSourceSecondsSinceLastEventType(kCGEventSourceStateHIDSystemState,
                                                  kCGAnyInputEventType);
}
