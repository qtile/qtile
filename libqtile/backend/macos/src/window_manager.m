#include "window_manager.h"
#import <AppKit/NSRunningApplication.h>
#import <AppKit/NSWorkspace.h>
#import <ApplicationServices/ApplicationServices.h>
#import <Foundation/Foundation.h>
#include <inttypes.h>
#include <signal.h>

// Private CoreGraphics SPI: obtain the stable CGWindowID from an AXUIElementRef.
// Declared here to avoid linking against private frameworks; falls back to the
// AX element pointer if the symbol is not available at runtime.
extern AXError _AXUIElementGetWindow(AXUIElementRef element, CGWindowID *windowID);

// Return a stable window identifier for winRef.  Prefers the CGWindowID obtained
// via the private _AXUIElementGetWindow SPI (used by yabai and others).  Falls
// back to the raw pointer value when that SPI is unavailable.
static uintptr_t stable_wid(AXUIElementRef winRef) {
    CGWindowID windowID = 0;
    if (_AXUIElementGetWindow(winRef, &windowID) == kAXErrorSuccess && windowID != 0) {
        return (uintptr_t)windowID;
    }
    return (uintptr_t)winRef;
}

static ax_observer_cb g_observer_cb = NULL;
static void *g_observer_userdata = NULL;
static NSMutableDictionary *g_observers = nil;

void mac_window_retain(struct mac_window *win) {
    if (win && win->ptr) {
        CFRetain((AXUIElementRef)win->ptr);
    }
}

void mac_window_release(struct mac_window *win) {
    if (win && win->ptr) {
        CFRelease((AXUIElementRef)win->ptr);
    }
}

static void axCallback(AXObserverRef observer, AXUIElementRef element, CFStringRef notification,
                       void *refcon) {
    if (g_observer_cb) {
        g_observer_cb((void *)element, (char *)[(__bridge NSString *)notification UTF8String],
                      g_observer_userdata);
    }
}

static void addObserverForApp(NSRunningApplication *app) {
    if (app.activationPolicy == NSApplicationActivationPolicyProhibited)
        return;

    pid_t pid = app.processIdentifier;
    AXObserverRef observer;
    AXError err = AXObserverCreate(pid, axCallback, &observer);
    if (err != kAXErrorSuccess)
        return;

    AXUIElementRef appRef = AXUIElementCreateApplication(pid);

    // Notifications we care about
    CFStringRef notifications[] = {
        kAXWindowCreatedNotification,        kAXUIElementDestroyedNotification,
        kAXFocusedWindowChangedNotification, kAXWindowMovedNotification,
        kAXWindowResizedNotification,        kAXTitleChangedNotification};

    for (int i = 0; i < (int)(sizeof(notifications) / sizeof(notifications[0])); i++) {
        AXObserverAddNotification(observer, appRef, notifications[i], NULL);
    }

    CFRunLoopAddSource(CFRunLoopGetCurrent(), AXObserverGetRunLoopSource(observer),
                       kCFRunLoopDefaultMode);

    if (!g_observers)
        g_observers = [NSMutableDictionary dictionary];
    // Use __bridge_transfer so ARC takes ownership of the +1 retain from
    // AXObserverCreate.  The dictionary now owns the object; mac_observer_stop
    // must NOT call CFRelease on values retrieved from g_observers.
    [g_observers setObject:(__bridge_transfer id)observer forKey:@(pid)];
    CFRelease(appRef);
}

int mac_observer_start(ax_observer_cb callback, void *userdata) {
    g_observer_cb = callback;
    g_observer_userdata = userdata;
    g_observers = [NSMutableDictionary dictionary];

    for (NSRunningApplication *app in [[NSWorkspace sharedWorkspace] runningApplications]) {
        addObserverForApp(app);
    }

    // Also listen for new apps
    [[[NSWorkspace sharedWorkspace] notificationCenter]
        addObserverForName:NSWorkspaceDidLaunchApplicationNotification
                    object:nil
                     queue:[NSOperationQueue mainQueue]
                usingBlock:^(NSNotification *_Nonnull note) {
                    NSRunningApplication *app = note.userInfo[NSWorkspaceApplicationKey];
                    addObserverForApp(app);
                }];

    // Remove the observer entry when an app terminates to avoid leaking the
    // AXObserverRef and its run-loop source for every app that quits.
    [[[NSWorkspace sharedWorkspace] notificationCenter]
        addObserverForName:NSWorkspaceDidTerminateApplicationNotification
                    object:nil
                     queue:[NSOperationQueue mainQueue]
                usingBlock:^(NSNotification *_Nonnull note) {
                    NSRunningApplication *app = note.userInfo[NSWorkspaceApplicationKey];
                    if (!app || !g_observers)
                        return;
                    pid_t pid = app.processIdentifier;
                    NSNumber *key = @(pid);
                    id obj = g_observers[key];
                    if (obj) {
                        AXObserverRef observer = (__bridge AXObserverRef)obj;
                        CFRunLoopRemoveSource(CFRunLoopGetCurrent(),
                                              AXObserverGetRunLoopSource(observer),
                                              kCFRunLoopDefaultMode);
                        // Removing from the dictionary releases ARC ownership
                        // (object was stored with __bridge_transfer).
                        [g_observers removeObjectForKey:key];
                    }
                }];

    return 0;
}

void mac_observer_stop(void) {
    for (id key in g_observers) {
        // The dictionary owns the +1 retain (transferred via __bridge_transfer in
        // addObserverForApp), so do NOT call CFRelease here — ARC will release the
        // object when it is removed from the dictionary below.
        AXObserverRef observer = (__bridge AXObserverRef)[g_observers objectForKey:key];
        CFRunLoopRemoveSource(CFRunLoopGetCurrent(), AXObserverGetRunLoopSource(observer),
                              kCFRunLoopDefaultMode);
    }
    [g_observers removeAllObjects];
    g_observers = nil;
}

int mac_get_windows(struct mac_window **windows, size_t *count) {
    if (!AXIsProcessTrusted()) {
        return 1;
    }

    NSMutableArray *results = [NSMutableArray array];

    for (NSRunningApplication *app in [[NSWorkspace sharedWorkspace] runningApplications]) {
        @autoreleasepool {
            if (app.activationPolicy == NSApplicationActivationPolicyProhibited)
                continue;

            pid_t pid = app.processIdentifier;
            AXUIElementRef appRef = AXUIElementCreateApplication(pid);

            CFArrayRef windowList;
            AXError err = AXUIElementCopyAttributeValue(appRef, kAXWindowsAttribute,
                                                        (CFTypeRef *)&windowList);

            if (err == kAXErrorSuccess && windowList != NULL) {
                CFIndex winCount = CFArrayGetCount(windowList);
                for (CFIndex i = 0; i < winCount; i++) {
                    AXUIElementRef winRef = CFArrayGetValueAtIndex(windowList, i);
                    if (!winRef)
                        continue;

                    CFRetain(winRef);

                    struct mac_window win;
                    win.ptr = (void *)winRef;
                    win.wid = stable_wid(winRef);

                    NSData *data = [NSData dataWithBytes:&win length:sizeof(struct mac_window)];
                    [results addObject:data];
                }
                CFRelease(windowList);
            }
            CFRelease(appRef);
        } // @autoreleasepool
    }

    *count = results.count;
    if (results.count == 0) {
        *windows = NULL;
        return 0;
    }
    *windows = malloc(sizeof(struct mac_window) * results.count);
    if (!*windows) {
        return 1;
    }
    for (size_t i = 0; i < results.count; i++) {
        [results[i] getBytes:&((*windows)[i]) length:sizeof(struct mac_window)];
    }

    return 0;
}

void mac_free_windows(struct mac_window *windows, size_t count) {
    for (size_t i = 0; i < count; i++) {
        if (windows[i].ptr)
            CFRelease((AXUIElementRef)windows[i].ptr);
    }
    free(windows);
}

int mac_get_focused_window(struct mac_window *win) {
    AXUIElementRef systemWide = AXUIElementCreateSystemWide();
    AXUIElementRef focusedApp;
    AXError err = AXUIElementCopyAttributeValue(systemWide, kAXFocusedApplicationAttribute,
                                                (CFTypeRef *)&focusedApp);
    CFRelease(systemWide);

    if (err != kAXErrorSuccess)
        return 1;

    AXUIElementRef focusedWin;
    err = AXUIElementCopyAttributeValue(focusedApp, kAXFocusedWindowAttribute,
                                        (CFTypeRef *)&focusedWin);
    CFRelease(focusedApp);

    if (err != kAXErrorSuccess)
        return 1;

    win->ptr = (void *)(uintptr_t)focusedWin;
    win->wid = stable_wid(focusedWin);
    return 0;
}

bool mac_is_window(void *ptr) {
    if (!ptr)
        return false;
    CFStringRef role;
    AXError err =
        AXUIElementCopyAttributeValue((AXUIElementRef)ptr, kAXRoleAttribute, (CFTypeRef *)&role);
    if (err != kAXErrorSuccess || !role)
        return false;
    bool result = [(__bridge NSString *)role isEqualToString:(__bridge NSString *)kAXWindowRole];
    CFRelease(role);
    return result;
}

char *mac_window_get_name(struct mac_window *win) {
    if (!win || !win->ptr)
        return strdup("Unknown");
    CFStringRef title;
    AXError err = AXUIElementCopyAttributeValue((AXUIElementRef)win->ptr, kAXTitleAttribute,
                                                (CFTypeRef *)&title);
    if (err == kAXErrorSuccess && title != NULL) {
        char *result = strdup([(__bridge NSString *)title UTF8String]);
        CFRelease(title);
        return result;
    }
    return strdup("Unknown");
}

char *mac_window_get_role(struct mac_window *win) {
    if (!win || !win->ptr)
        return strdup("Unknown");
    CFStringRef role;
    AXError err = AXUIElementCopyAttributeValue((AXUIElementRef)win->ptr, kAXRoleAttribute,
                                                (CFTypeRef *)&role);
    if (err == kAXErrorSuccess && role != NULL) {
        char *result = strdup([(__bridge NSString *)role UTF8String]);
        CFRelease(role);
        return result;
    }
    return strdup("Unknown");
}

char *mac_window_get_app_name(struct mac_window *win) {
    if (!win || !win->ptr)
        return strdup("Unknown");
    pid_t pid = 0;
    AXUIElementGetPid((AXUIElementRef)win->ptr, &pid);
    NSRunningApplication *app = [NSRunningApplication runningApplicationWithProcessIdentifier:pid];
    if (app && app.localizedName) {
        return strdup([app.localizedName UTF8String]);
    }
    return strdup("Unknown");
}

char *mac_window_get_bundle_id(struct mac_window *win) {
    if (!win || !win->ptr)
        return strdup("Unknown");
    pid_t pid = 0;
    AXUIElementGetPid((AXUIElementRef)win->ptr, &pid);
    NSRunningApplication *app = [NSRunningApplication runningApplicationWithProcessIdentifier:pid];
    if (app && app.bundleIdentifier) {
        return strdup([app.bundleIdentifier UTF8String]);
    }
    return strdup("Unknown");
}

void mac_window_get_position(struct mac_window *win, int *x, int *y) {
    if (!AXIsProcessTrusted())
        return;
    if (!win || !win->ptr)
        return;

    CFTypeRef position = NULL;
    AXError err =
        AXUIElementCopyAttributeValue((AXUIElementRef)win->ptr, kAXPositionAttribute, &position);

    if (err == kAXErrorSuccess && position != NULL) {
        CGPoint point;
        if (AXValueGetValue(position, kAXValueCGPointType, &point)) {
            *x = (int)point.x;
            *y = (int)point.y;
        }
        CFRelease(position);
    }
}

void mac_window_get_size(struct mac_window *win, int *width, int *height) {
    if (!AXIsProcessTrusted())
        return;
    if (!win || !win->ptr)
        return;

    CFTypeRef size;
    AXError err = AXUIElementCopyAttributeValue((AXUIElementRef)win->ptr, kAXSizeAttribute, &size);
    if (err == kAXErrorSuccess && size != NULL) {
        CGSize sz;
        AXValueGetValue(size, kAXValueCGSizeType, &sz);
        *width = (int)sz.width;
        *height = (int)sz.height;
        CFRelease(size);
    }
}

void mac_window_place(struct mac_window *win, int x, int y, int width, int height) {
    if (!AXIsProcessTrusted())
        return;
    if (!win || !win->ptr)
        return;

    // Wrap in an explicit @autoreleasepool so that ARC does not drain the pool
    // at an unpredictable time while AXUIElementSetAttributeValue is still
    // using the AXValueRef objects.
    @autoreleasepool {
        CGPoint point = CGPointMake(x, y);
        AXValueRef position = AXValueCreate(kAXValueCGPointType, &point);
        AXUIElementSetAttributeValue((AXUIElementRef)win->ptr, kAXPositionAttribute, position);
        CFRelease(position);

        CGSize sz = CGSizeMake(width, height);
        AXValueRef size = AXValueCreate(kAXValueCGSizeType, &sz);
        AXUIElementSetAttributeValue((AXUIElementRef)win->ptr, kAXSizeAttribute, size);
        CFRelease(size);
    }
}

void mac_window_focus(struct mac_window *win) {
    if (!AXIsProcessTrusted())
        return;
    if (!win || !win->ptr)
        return;

    AXUIElementSetAttributeValue((AXUIElementRef)win->ptr, kAXMainAttribute, kCFBooleanTrue);
    AXUIElementSetAttributeValue((AXUIElementRef)win->ptr, kAXFocusedAttribute, kCFBooleanTrue);

    pid_t pid = 0;
    AXUIElementGetPid((AXUIElementRef)win->ptr, &pid);
    NSRunningApplication *app = [NSRunningApplication runningApplicationWithProcessIdentifier:pid];
    // activateWithOptions: is deprecated in macOS 14+ but is the only
    // activate API that compiles reliably against all SDK versions.
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wdeprecated-declarations"
    [app activateWithOptions:NSApplicationActivateIgnoringOtherApps];
#pragma clang diagnostic pop
}

void mac_window_bring_to_front(struct mac_window *win) {
    if (!AXIsProcessTrusted())
        return;
    if (!win || !win->ptr)
        return;

    AXUIElementPerformAction((AXUIElementRef)win->ptr, kAXRaiseAction);
}

void mac_window_set_hidden(struct mac_window *win, bool hidden) {
    if (!AXIsProcessTrusted())
        return;
    if (!win || !win->ptr)
        return;

    AXUIElementSetAttributeValue((AXUIElementRef)win->ptr, kAXHiddenAttribute,
                                 hidden ? kCFBooleanTrue : kCFBooleanFalse);
}

void mac_window_kill(struct mac_window *win) {
    if (!win || !win->ptr)
        return;

    // Prefer pressing the close button — this is what clicking the red button does.
    AXUIElementRef closeButton = NULL;
    AXError err = AXUIElementCopyAttributeValue((AXUIElementRef)win->ptr, kAXCloseButtonAttribute,
                                                (CFTypeRef *)&closeButton);
    if (err == kAXErrorSuccess && closeButton != NULL) {
        AXUIElementPerformAction(closeButton, kAXPressAction);
        CFRelease(closeButton);
        return;
    }

    // Fallback: send SIGTERM to the owning process.
    pid_t pid = 0;
    AXUIElementGetPid((AXUIElementRef)win->ptr, &pid);
    if (pid > 0) {
        kill(pid, SIGTERM);
    }
}

int mac_window_get_pid(struct mac_window *win) {
    if (!win || !win->ptr)
        return 0;
    pid_t pid = 0;
    AXUIElementGetPid((AXUIElementRef)win->ptr, &pid);
    return (int)pid;
}

bool mac_window_is_visible(struct mac_window *win) {
    if (!win || !win->ptr)
        return true;
    CFBooleanRef hidden = NULL;
    AXError err = AXUIElementCopyAttributeValue((AXUIElementRef)win->ptr, kAXHiddenAttribute,
                                                (CFTypeRef *)&hidden);
    if (err == kAXErrorSuccess && hidden != NULL) {
        bool result = !CFBooleanGetValue(hidden);
        CFRelease(hidden);
        return result;
    }
    return true;
}

int mac_window_get_parent(struct mac_window *win, struct mac_window *parent_out) {
    if (!win || !win->ptr || !parent_out)
        return 1;

    AXUIElementRef parentRef = NULL;
    AXError err = AXUIElementCopyAttributeValue((AXUIElementRef)win->ptr, kAXParentAttribute,
                                                (CFTypeRef *)&parentRef);
    if (err != kAXErrorSuccess || !parentRef)
        return 1;

    // Check that the parent is a window element, not the application element.
    CFStringRef role = NULL;
    AXError roleErr =
        AXUIElementCopyAttributeValue(parentRef, kAXRoleAttribute, (CFTypeRef *)&role);
    bool isWindow = false;
    if (roleErr == kAXErrorSuccess && role) {
        isWindow = [(__bridge NSString *)role isEqualToString:(__bridge NSString *)kAXWindowRole];
        CFRelease(role);
    }
    if (!isWindow) {
        CFRelease(parentRef);
        return 1;
    }

    parent_out->ptr = (void *)parentRef; // caller owns the +1 retain from Copy
    parent_out->wid = stable_wid(parentRef);
    return 0;
}

void mac_window_set_fullscreen(struct mac_window *win, bool fullscreen) {
    if (!AXIsProcessTrusted())
        return;
    if (!win || !win->ptr)
        return;

    AXUIElementSetAttributeValue((AXUIElementRef)win->ptr, CFSTR("AXFullScreen"),
                                 fullscreen ? kCFBooleanTrue : kCFBooleanFalse);
}

void mac_window_set_maximized(struct mac_window *win, bool maximized) {
    if (!AXIsProcessTrusted())
        return;
    if (!win || !win->ptr)
        return;

    AXUIElementSetAttributeValue((AXUIElementRef)win->ptr, CFSTR("AXZoomed"),
                                 maximized ? kCFBooleanTrue : kCFBooleanFalse);
}

void mac_window_set_minimized(struct mac_window *win, bool minimized) {
    if (!AXIsProcessTrusted())
        return;
    if (!win || !win->ptr)
        return;

    AXUIElementSetAttributeValue((AXUIElementRef)win->ptr, kAXMinimizedAttribute,
                                 minimized ? kCFBooleanTrue : kCFBooleanFalse);
}
