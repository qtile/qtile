#!/usr/bin/env python3
import os

from cffi import FFI

# XXX: This ugly piece of s**t is necessary to compile the module from the project root manually,
# with tox/packaging and when inside libqtile/widget.
curdir = os.path.realpath('.')
this_dirname = os.path.dirname(os.path.realpath(__file__))
if this_dirname.startswith(curdir) and len(this_dirname) > len(curdir):
    this_dirname = this_dirname[len(curdir) + 1:]
print(curdir)
ffibuilder = FFI()

ffibuilder.set_source(
    "_keyboard_helper",
    """
    #include <ctype.h>
    #include "keyboard_helper.h"
    """,
    sources=[os.path.join(this_dirname, 'keyboard_helper.c')],  # includes keyboard_helper.c
    include_dirs=[this_dirname],
    libraries=['X11', 'xkbfile']  # link to those libraries
)

ffibuilder.cdef("""
/* X11/extensions/XKBrules.h */
typedef struct {
    char * model;
    char * layout;
    char * variant;
    char * options;
    unsigned short sz_extra;
    unsigned short num_extra;
    char * extra_names;
    char ** extra_values;
} XkbRF_VarDefsRec, *XkbRF_VarDefsPtr;

/* X11/XKBlib.h */
const int XkbOD_BadLibraryVersion;
const int XkbOD_ConnectionRefused;
const int XkbOD_BadServerVersion;
const int XkbOD_NonXkbServer;
const int XkbOD_Success;

/* keyboard_helper.h */
int open_display(char* display_name);
int display_is_open();
void close_display();
XkbRF_VarDefsRec _get_layouts_variants();
int _select_events();
int _get_group();
int _set_group(int group_num);
""")

if __name__ == "__main__":
    ffibuilder.compile(verbose=True)
