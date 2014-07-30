#!/usr/bin/env python2
"""
    This program is carefully crafted to exercise a number of corner-cases in
    Qtile.
"""
import sys
import time
import struct
import xcb
import xcb.xproto


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
        conn = xcb.xcb.connect(display=sys.argv[1])
    except xcb.ConnectException:
        time.sleep(0.1)
        continue
    except Exception as v:
        print >> sys.stderr, "Error opening test window: ", type(v), v
        sys.exit(1)
    break
else:
    print >> sys.stderr, "Could not open window on display %s" % (sys.argv[1])
    sys.exit(1)


screen = conn.get_setup().roots[conn.pref_screen]

window = conn.generate_id()
background = conn.core.AllocColor(screen.default_colormap, 0x2828, 0x8383, 0xCECE).reply().pixel # Color "#2883ce"
conn.core.CreateWindow(xcb.CopyFromParent, window, screen.root,
        100, 100, 100, 100, 1,
        xcb.xproto.WindowClass.InputOutput, screen.root_visual,
        xcb.xproto.CW.BackPixel | xcb.xproto.CW.EventMask,
        [background, xcb.xproto.EventMask.StructureNotify | xcb.xproto.EventMask.Exposure])

conn.core.ChangeProperty(xcb.xproto.PropMode.Replace,
        window, xcb.xproto.Atom.WM_NAME,
        xcb.xproto.Atom.STRING, 8, len(sys.argv[2]),
        sys.argv[2])

wm_protocols = conn.core.InternAtom(0, len("WM_PROTOCOLS"), "WM_PROTOCOLS").reply().atom
delete_window = conn.core.InternAtom(0, len("WM_DELETE_WINDOW"), "WM_DELETE_WINDOW").reply().atom
conn.core.ChangeProperty(xcb.xproto.PropMode.Replace,
        window, wm_protocols,
        xcb.xproto.Atom.ATOM, 32, 1,
        struct.pack("=L", delete_window))

conn.core.ConfigureWindow(window,
        xcb.xproto.ConfigWindow.X | xcb.xproto.ConfigWindow.Y |
        xcb.xproto.ConfigWindow.Width | xcb.xproto.ConfigWindow.Height |
        xcb.xproto.ConfigWindow.BorderWidth,
        [0, 0, 100, 100, 1])
conn.core.MapWindow(window)
conn.flush()
conn.core.ConfigureWindow(window,
        xcb.xproto.ConfigWindow.X | xcb.xproto.ConfigWindow.Y |
        xcb.xproto.ConfigWindow.Width | xcb.xproto.ConfigWindow.Height |
        xcb.xproto.ConfigWindow.BorderWidth,
        [0, 0, 100, 100, 1])

try:
    while 1:
        event = conn.wait_for_event()
        if event.__class__ == xcb.xproto.ClientMessageEvent:
            if str(conn.core.GetAtomName(event.data.data32[0]).reply().name.buf()) == "WM_DELETE_WINDOW":
                sys.exit(1)
except (IOError, xcb.Exception):
    pass
