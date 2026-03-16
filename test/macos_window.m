#import <AppKit/NSApplication.h>
#import <AppKit/NSScreen.h>
#import <AppKit/NSWindow.h>
#import <Foundation/Foundation.h>

@interface AppDelegate : NSObject <NSApplicationDelegate>
@end

@implementation AppDelegate
- (void)applicationDidFinishLaunching:(NSNotification *)aNotification {
    NSRect rect = NSMakeRect(100, 100, 200, 200);
    NSWindow *window =
        [[NSWindow alloc] initWithContentRect:rect
                                    styleMask:NSWindowStyleMaskTitled | NSWindowStyleMaskClosable |
                                              NSWindowStyleMaskResizable
                                      backing:NSBackingStoreBuffered
                                        defer:NO];
    NSString *title = [[NSProcessInfo processInfo] arguments].lastObject;
    if ([title hasSuffix:@"macos_window"])
        title = @"TestWindow";
    [window setTitle:title];
    [window makeKeyAndOrderFront:nil];
}

- (BOOL)applicationShouldTerminateAfterLastWindowClosed:(NSApplication *)sender {
    return YES;
}
@end

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        NSApplication *app = [NSApplication sharedApplication];
        AppDelegate *delegate = [[AppDelegate alloc] init];
        [app setDelegate:delegate];
        [app setActivationPolicy:NSApplicationActivationPolicyRegular];
        [app run];
    }
    return 0;
}
