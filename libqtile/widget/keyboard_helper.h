#include <stdio.h>
#include <string.h>
#include <ctype.h>
#include <X11/XKBlib.h>
#include <X11/extensions/XKBrules.h>

int open_display(char* display_name);
int display_is_open();
void close_display();
XkbRF_VarDefsRec _get_layouts_variants();
int _select_events();
int _get_group();
int _set_group(int group_num);
