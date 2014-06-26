#!/usr/bin/env python
"""
    This program is carefully crafted to exercise a number of corner-cases in
    Qtile.
"""
from __future__ import print_function
import sys
import time
from Xlib import display, error, X, protocol
try:
    from StringIO import StringIO # Python 2
except ImportError:
    from io import StringIO # Python 3


def configure(window):
    window.configure(
        width=100,
        height=100,
        x=0,
        y=0,
        border_width=1,
    )

for i in range(20):
    try:
        # Remove useless lib print
        stdout, sys.stdout = sys.stdout, StringIO()
        d = display.Display(sys.argv[1])
        sys.stdout = stdout

    except error.DisplayConnectionError:
        time.sleep(0.1)
        continue
    except Exception as v:
        print("Error opening test window: ", type(v), v, file=sys.stderr)
        sys.exit(1)
    break
else:
    print("Could not open window on display %s" % (sys.argv[1]), file=sys.stderr)
    sys.exit(1)


root = d.screen().root
colormap = d.screen().default_colormap
background = colormap.alloc_named_color("#2883CE").pixel
window = root.create_window(100, 100, 100, 100, 1,
                            X.CopyFromParent, X.InputOutput,
                            X.CopyFromParent,
                            background_pixel=background,
                            event_mask=X.StructureNotifyMask | X.ExposureMask)
window.set_wm_name(sys.argv[2])
window.set_wm_protocols([d.intern_atom("WM_DELETE_WINDOW")])

configure(window)
window.map()
d.sync()
configure(window)


try:
    while 1:
        event = d.next_event()
        if event.__class__ == protocol.event.ClientMessage:
            if d.get_atom_name(event.data[1][0]) == "WM_DELETE_WINDOW":
                sys.exit(1)
except error.ConnectionClosedError:
    pass
