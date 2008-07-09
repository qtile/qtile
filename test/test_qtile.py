import subprocess, os, time, sys
import Xlib.display, Xlib.X
import libpry
import libqtile

class XNest(libpry.TestContainer):
    def __init__(self, xinerama, display):
        libpry.TestContainer.__init__(self)
        self.xinerama = xinerama
        self["display"] = display

    def setUp(self):
        args = [ "Xnest", "-geometry", "800x600", self["display"], "-ac", "-sync"]
        if self.xinerama:
            args.extend(["+xinerama", "-scrns", "2"])

        self.sub = subprocess.Popen(
                        args,
                        stdout = subprocess.PIPE,
                        stderr = subprocess.PIPE,
                    )

    def tearDown(self):
        os.kill(self.sub.pid, 9)
                

class _QTileTruss(libpry.TmpDirMixin, libpry.AutoTree):
    def setUp(self):
        libpry.TmpDirMixin.setUp(self)
        # Try until XNest is up
        for i in range(20):
            try:
                d = Xlib.display.Display(self["display"])
                break
            except (Xlib.error.DisplayConnectionError, Xlib.error.ConnectionClosedError):
                time.sleep(0.1)
        else:
            raise AssertionError, "Could not connect to display."
        d.close()
        
        # Now start for real
        self["fname"] = os.path.join(self["tmpdir"], "qtilesocket")
        pid = os.fork()
        if pid == 0:
            q = libqtile.QTile(self["display"], self["fname"])
            q.loop()
        else:
            self.qtilepid = pid
            time.sleep(0.1)

    def testWindow(self, name):
        c = libqtile.ipc.Client(self["fname"])
        groups = c.call("clientmap")
        start = sum([len(i) for i in groups.values()])
        if os.fork() == 0:
            os.execv("scripts/window", ["scripts/window", self["display"], name])
        for i in range(20):
            groups = c.call("clientmap")
            new = sum([len(i) for i in groups.values()])
            if new > start:
                break
            time.sleep(0.1)
        else:
            raise AssertionError("Window never appeared...")
            
    def tearDown(self):
        libpry.TmpDirMixin.tearDown(self)
        os.kill(self.qtilepid, 9)


class uQTile(_QTileTruss):
    def test_events(self):
        c = libqtile.ipc.Client(self["fname"])
        assert c.call("status") == "OK"

    def test_window(self):
        c = libqtile.ipc.Client(self["fname"])
        self.testWindow("one")
        groups = c.call("clientmap")
        assert "one" in groups["a"]


tests = [
    XNest(xinerama=True, display=":1"), [
        uQTile()
    ],
    XNest(xinerama=False, display=":2"), [
        uQTile()
    ]
]
