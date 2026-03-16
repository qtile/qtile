#import <Cocoa/Cocoa.h>

@interface AppDelegate : NSObject <NSApplicationDelegate>
@property(strong, nonatomic) NSWindow *window;
@end

@implementation AppDelegate

- (void)applicationDidFinishLaunching:(NSNotification *)aNotification {
    NSRect contentRect = NSMakeRect(100, 100, 400, 200);
    self.window =
        [[NSWindow alloc] initWithContentRect:contentRect
                                    styleMask:NSWindowStyleMaskTitled | NSWindowStyleMaskResizable |
                                              NSWindowStyleMaskClosable
                                      backing:NSBackingStoreBuffered
                                        defer:NO];
    [self.window setTitle:@"Test Window"];
    [self.window makeKeyAndOrderFront:nil];
}

@end

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        NSApplication *application = [NSApplication sharedApplication];
        AppDelegate *appDelegate = [[AppDelegate alloc] init];
        [application setDelegate:appDelegate];

        dispatch_async(dispatch_get_main_queue(), ^{
            [application run];
        });

        // Keep the process alive
        [[NSRunLoop mainRunLoop] run];
    }
    return 0;
}
