#!/usr/bin/env python
"""
    This program is carefully crafted to exercise a number of corner-cases in
    Qtile.
"""
from __future__ import print_function
import sys
import time
import xcffib
import xcffib.xproto

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
        conn = xcffib.connect(display=sys.argv[1])
    except xcffib.ConnectionException:
        time.sleep(0.1)
        continue
    except Exception as v:
        print("Error opening test window: ", type(v), v, file=sys.stderr)
        sys.exit(1)
    break
else:
    print("Could not open window on display %s" % (sys.argv[1]), file=sys.stderr)
    sys.exit(1)

screen = conn.get_setup().roots[conn.pref_screen]

window = conn.generate_id()
background = conn.core.AllocColor(screen.default_colormap, 0x2828, 0x8383, 0xCECE).reply().pixel # Color "#2883ce"
conn.core.CreateWindow(xcffib.CopyFromParent, window, screen.root,
        100, 100, 100, 100, 1,
        xcffib.xproto.WindowClass.InputOutput, screen.root_visual,
        xcffib.xproto.CW.BackPixel | xcffib.xproto.CW.EventMask,
        [background, xcffib.xproto.EventMask.StructureNotify | xcffib.xproto.EventMask.Exposure])

conn.core.ChangeProperty(xcffib.xproto.PropMode.Replace,
        window, xcffib.xproto.Atom.WM_NAME,
        xcffib.xproto.Atom.STRING, 8, len(sys.argv[2]),
        sys.argv[2])

wm_protocols = "WM_PROTOCOLS"
wm_protocols = conn.core.InternAtom(0, len(wm_protocols), wm_protocols).reply().atom

wm_delete_window = "WM_DELETE_WINDOW"
wm_delete_window = conn.core.InternAtom(0, len(wm_delete_window), wm_delete_window).reply().atom

conn.core.ChangeProperty(xcffib.xproto.PropMode.Replace,
        window, wm_protocols,
        xcffib.xproto.Atom.ATOM, 32, 1,
        [wm_delete_window])

conn.core.ConfigureWindow(window,
        xcffib.xproto.ConfigWindow.X | xcffib.xproto.ConfigWindow.Y |
        xcffib.xproto.ConfigWindow.Width | xcffib.xproto.ConfigWindow.Height |
        xcffib.xproto.ConfigWindow.BorderWidth,
        [0, 0, 100, 100, 1])
conn.core.MapWindow(window)
conn.flush()
conn.core.ConfigureWindow(window,
        xcffib.xproto.ConfigWindow.X | xcffib.xproto.ConfigWindow.Y |
        xcffib.xproto.ConfigWindow.Width | xcffib.xproto.ConfigWindow.Height |
        xcffib.xproto.ConfigWindow.BorderWidth,
        [0, 0, 100, 100, 1])

try:
    while 1:
        event = conn.wait_for_event()
        if event.__class__ == xcffib.xproto.ClientMessageEvent:
            if conn.core.GetAtomName(event.type).reply().name.as_string() == "WM_DELETE_WINDOW":
                sys.exit(1)
except xcffib.XcffibException:
    pass
