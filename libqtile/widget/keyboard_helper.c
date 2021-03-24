#include <stdio.h>
#include <string.h>
#include <ctype.h>
#include <X11/XKBlib.h>
#include <X11/extensions/XKBrules.h>

Display* display = NULL;

void close_display();

int open_display(char* display_name) {
    XkbIgnoreExtension(False);
    close_display();  // if display is not a null pointer, give libX11 a chance
                      // to free some memory.
    int event_code, error_return, status;
    int major_version = XkbMajorVersion;
    int minor_version = XkbMinorVersion;
    display = XkbOpenDisplay(display_name, &event_code, &error_return,
                             &major_version, &minor_version, &status);
    return status;
}
int display_is_open() {
    return display != NULL;
}
void close_display() {
    if (display != NULL)
        XCloseDisplay(display);
}
XkbRF_VarDefsRec _get_layouts_variants() {
    XkbRF_VarDefsRec vdrec;
    char* tmp = NULL;
    XkbRF_GetNamesProp(display, &tmp, &vdrec);  // returns Bool
    return vdrec;
}
int _select_events() {
    return XkbSelectEventDetails(display, XkbUseCoreKbd, XkbStateNotify,
                                 XkbAllStateComponentsMask,
                                 XkbGroupStateMask);
}
int _get_group() {
    XkbStateRec xkb_state;
    XkbGetState(display, XkbUseCoreKbd, &xkb_state);
    return (int)xkb_state.group;
}
int _set_group(int group_num) {
    XkbLockGroup(display, XkbUseCoreKbd, group_num);  // returns Bool=True
    XFlush(display);
    return _get_group() == group_num;
}
