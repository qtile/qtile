#include "drawing.h"
#import <AppKit/NSColor.h>
#import <AppKit/NSGraphicsContext.h>
#import <AppKit/NSView.h>
#import <AppKit/NSWindow.h>

@interface QtileView : NSView {
    struct mac_internal *_internal;
}
@property(nonatomic, assign) struct mac_internal *internal;
@end

@implementation QtileView
@synthesize internal = _internal;

- (void)drawRect:(NSRect)dirtyRect {
    if (!_internal || !_internal->buffer)
        return;

    CGContextRef context = [[NSGraphicsContext currentContext] CGContext];
    CGColorSpaceRef colorSpace = CGColorSpaceCreateDeviceRGB();

    CGDataProviderRef provider = CGDataProviderCreateWithData(
        NULL, _internal->buffer, _internal->width * _internal->height * 4, NULL);

    CGImageRef image =
        CGImageCreate(_internal->width, _internal->height, 8, 32, _internal->width * 4, colorSpace,
                      kCGImageAlphaPremultipliedLast | kCGBitmapByteOrder32Host, provider, NULL, NO,
                      kCGRenderingIntentDefault);

    CGContextDrawImage(context, CGRectMake(0, 0, _internal->width, _internal->height), image);

    CGImageRelease(image);
    CGDataProviderRelease(provider);
    CGColorSpaceRelease(colorSpace);
}
@end

struct mac_internal *mac_internal_new(int x, int y, int width, int height) {
    struct mac_internal *internal = malloc(sizeof(struct mac_internal));
    if (!internal)
        return NULL;
    internal->width = width;
    internal->height = height;
    internal->buffer = calloc((size_t)width * height, 4);
    if (!internal->buffer) {
        free(internal);
        return NULL;
    }

    void (^block)(void) = ^{
        NSRect contentRect = NSMakeRect(x, y, width, height);
        NSWindow *window = [[NSWindow alloc] initWithContentRect:contentRect
                                                       styleMask:NSWindowStyleMaskBorderless
                                                         backing:NSBackingStoreBuffered
                                                           defer:NO];
        [window setOpaque:NO];
        [window setBackgroundColor:[NSColor clearColor]];
        [window setLevel:NSMainMenuWindowLevel + 1];
        [window setHasShadow:NO];

        QtileView *view = [[QtileView alloc] initWithFrame:NSMakeRect(0, 0, width, height)];
        view.internal = internal;
        [window setContentView:view];
        // Use orderFront: instead of makeKeyAndOrderFront: to avoid stealing
        // keyboard focus from the currently active application (issues 0048, 0055).
        [window orderFront:nil];

        internal->win = (void *)CFBridgingRetain(window);
        internal->view = (void *)CFBridgingRetain(view);
    };

    if ([NSThread isMainThread]) {
        block();
    } else {
        dispatch_sync(dispatch_get_main_queue(), block);
    }

    return internal;
}

void mac_internal_free(struct mac_internal *internal) {
    void (^block)(void) = ^{
        NSWindow *window = CFBridgingRelease(internal->win);
        [window orderOut:nil];
        CFBridgingRelease(internal->view);
    };

    if ([NSThread isMainThread]) {
        block();
    } else {
        dispatch_sync(dispatch_get_main_queue(), block);
    }

    free(internal->buffer);
    free(internal);
}

void mac_internal_place(struct mac_internal *internal, int x, int y, int width, int height) {
    void (^block)(void) = ^{
        NSWindow *window = (__bridge NSWindow *)internal->win;
        [window setFrame:NSMakeRect(x, y, width, height) display:YES];

        if (width != internal->width || height != internal->height) {
            // Reallocate buffer for the new dimensions. Use a temporary pointer
            // so that the old buffer is only freed if allocation succeeds; this
            // keeps the old buffer intact and avoids a NULL-pointer crash when
            // the system is under memory pressure.
            void *new_buf = calloc((size_t)width * height, 4);
            if (new_buf) {
                free(internal->buffer);
                internal->buffer = new_buf;
                internal->width = width;
                internal->height = height;
            }
            // If new_buf is NULL, keep the old buffer and dimensions to avoid crash.
        }
    };

    // Use dispatch_sync (not dispatch_async) so that the frame resize and buffer
    // reallocation complete before this function returns. Python may call draw()
    // immediately after place(), and an async dispatch would leave it writing to
    // the old-sized buffer while the resize block is still pending.
    if ([NSThread isMainThread]) {
        block();
    } else {
        dispatch_sync(dispatch_get_main_queue(), block);
    }
}

void *mac_internal_get_buffer(struct mac_internal *internal) { return internal->buffer; }

void mac_internal_draw(struct mac_internal *internal) {
    // Use dispatch_sync so the draw completes before this function returns.
    // This prevents a pending async block from accessing internal->view after
    // mac_internal_free has freed the struct (use-after-free, issue 0025).
    if ([NSThread isMainThread]) {
        QtileView *view = (__bridge QtileView *)internal->view;
        [view setNeedsDisplay:YES];
    } else {
        dispatch_sync(dispatch_get_main_queue(), ^{
            QtileView *view = (__bridge QtileView *)internal->view;
            [view setNeedsDisplay:YES];
        });
    }
}

void mac_internal_set_visible(struct mac_internal *internal, bool visible) {
    // Use dispatch_sync to avoid a use-after-free: an async block could run
    // after mac_internal_free has freed internal (issue 0025).
    // Use orderFront: instead of makeKeyAndOrderFront: to avoid stealing focus
    // (issue 0055).
    void (^block)(void) = ^{
        NSWindow *window = (__bridge NSWindow *)internal->win;
        if (visible) {
            [window orderFront:nil];
        } else {
            [window orderOut:nil];
        }
    };
    if ([NSThread isMainThread]) {
        block();
    } else {
        dispatch_sync(dispatch_get_main_queue(), block);
    }
}

void mac_internal_bring_to_front(struct mac_internal *internal) {
    if ([NSThread isMainThread]) {
        NSWindow *window = (__bridge NSWindow *)internal->win;
        [window orderFront:nil];
    } else {
        dispatch_sync(dispatch_get_main_queue(), ^{
            NSWindow *window = (__bridge NSWindow *)internal->win;
            [window orderFront:nil];
        });
    }
}
