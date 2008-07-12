import subprocess, os, time, sys, socket, traceback
import Xlib.display, Xlib.X
import libpry
import libqtile


class XNest(libpry.TestContainer):
    def __init__(self, xinerama, display=":1"):
        libpry.TestContainer.__init__(self)
        self.xinerama = xinerama
        if xinerama:
            self.name = "XNestXinerama"
        self["display"] = display

    def setUp(self):
        args = [ "Xnest", "+kb", "-geometry", "800x600", self["display"], "-ac", "-sync"]
        if self.xinerama:
            args.extend(["+xinerama", "-scrns", "2"])
        self.sub = subprocess.Popen(
                        args,
                        stdout = subprocess.PIPE,
                        stderr = subprocess.PIPE,
                    )

    def tearDown(self):
        os.kill(self.sub.pid, 9)
        os.waitpid(self.sub.pid, 0)
                

class _QTileTruss(libpry.TmpDirMixin, libpry.AutoTree):
    qtilepid = None
    def setUp(self):
        libpry.TmpDirMixin.setUp(self)
        self.testwindows = []

    def tearDown(self):
        libpry.TmpDirMixin.tearDown(self)

    def startQtile(self):
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
        del d
        
        # Now start for real
        self["fname"] = os.path.join(self["tmpdir"], "qtilesocket")
        pid = os.fork()
        if pid == 0:
            # Run this in a sandbox...
            try:
                q = libqtile.QTile(self["display"], self["fname"])
                q.testing = True
                q.loop()
            except Exception, e:
                traceback.print_exc(file=sys.stderr)
            sys.exit(0)
        else:
            self.qtilepid = pid
            c = libqtile.command.Client(self["fname"], libqtile.command.Command)
            # Wait until qtile is up before continuing
            for i in range(20):
                try:
                    if c.status() == "OK":
                        break
                except socket.error:
                    pass
                time.sleep(0.1)
            else:
                raise AssertionError, "Timeout waiting for Qtile"
        self.c = libqtile.command.Client(self["fname"], libqtile.command.Command)

    def stopQtile(self):
        if self.qtilepid:
            try:
                self._kill(self.qtilepid)
            except OSError:
                # The process may have died due to some other error
                pass
        for pid in self.testwindows[:]:
            self._kill(pid)

    def testWindow(self, name):
        c = libqtile.command.Client(self["fname"], libqtile.command.Command)
        start = c.clientcount()
        pid = os.fork()
        if pid == 0:
            os.execv("scripts/window", ["scripts/window", self["display"], name])
        for i in range(20):
            if c.clientcount() > start:
                break
            time.sleep(0.1)
        else:
            raise AssertionError("Window never appeared...")
        self.testwindows.append(pid)
        return pid

    def _kill(self, pid):
        os.kill(pid, 9)
        os.waitpid(pid, 0)
        if pid in self.testwindows:
            self.testwindows.remove(pid)

    def kill(self, pid):
        c = libqtile.command.Client(self["fname"], libqtile.command.Command)
        start = c.clientcount()
        self._kill(pid)
        for i in range(20):
            if c.clientcount() < start:
                break
            time.sleep(0.1)
        else:
            raise AssertionError("Window could not be killed...")


class uQTile(_QTileTruss):
    def setUp(self):
        _QTileTruss.setUp(self)
        self.startQtile()

    def tearDown(self):
        _QTileTruss.tearDown(self)
        self.stopQtile()

    def test_events(self):
        assert self.c.status() == "OK"

    def test_mapRequest(self):
        self.testWindow("one")
        info = self.c.groupinfo("a")
        assert "one" in info["clients"]
        assert info["focus"] == "one"

        self.testWindow("two")
        info = self.c.groupinfo("a")
        assert "two" in info["clients"]
        assert info["focus"] == "two"

    def test_unmap(self):
        one = self.testWindow("one")
        two = self.testWindow("two")
        three = self.testWindow("three")
        info = self.c.groupinfo("a")
        assert info["focus"] == "three"

        assert self.c.clientcount() == 3
        self.kill(three)

        assert self.c.clientcount() == 2
        info = self.c.groupinfo("a")
        assert info["focus"] == "two"

        self.kill(two)
        assert self.c.clientcount() == 1
        info = self.c.groupinfo("a")
        assert info["focus"] == "one"

        self.kill(one)
        assert self.c.clientcount() == 0
        info = self.c.groupinfo("a")
        assert info["focus"] == None

    def test_focus(self):
        self.testWindow("one")
        self.testWindow("two")
        self.testWindow("three")

        info = self.c.groupinfo("a")
        assert info["focus"] == "three"
        self.c.focusnext()
        info = self.c.groupinfo("a")
        assert info["focus"] == "two"
        self.c.focusnext()
        info = self.c.groupinfo("a")
        assert info["focus"] == "one"

        self.c.focusnext()
        info = self.c.groupinfo("a")
        assert info["focus"] == "three"

    def test_setgroup(self):
        self.testWindow("one")
        assert self.c.pullgroup("nonexistent") == "No such group"
        self.c.pullgroup("b")
        if self.c.screencount() == 1:
            assert self.c.groupinfo("a")["screen"] == None
        else:
            assert self.c.groupinfo("a")["screen"] == 1
        assert self.c.groupinfo("b")["screen"] == 0
        self.c.pullgroup("c")
        assert self.c.groupinfo("c")["screen"] == 0

    def test_unmap_noscreen(self):
        self.testWindow("one")
        pid = self.testWindow("two")
        assert self.c.clientcount() == 2
        self.c.pullgroup("c")
        assert self.c.clientcount() == 2
        self.kill(pid)
        assert self.c.clientcount() == 1
        assert self.c.groupinfo("a")["focus"] == "one"

    def test_keypress(self):
        self.testWindow("one")
        self.testWindow("two")
        v = self.c.simulate_keypress(["unknown"], "j")
        assert v.startswith("Unknown modifier")
        assert self.c.groupinfo("a")["focus"] == "two"
        self.c.simulate_keypress(["control"], "j")
        assert self.c.groupinfo("a")["focus"] == "one"


class uKey(libpry.AutoTree):
    def test_init(self):
        libpry.raises(
            "unknown key",
            libqtile.Key,
            [], "unknown", None
        )
        libpry.raises(
            "unknown modifier",
            libqtile.Key,
            ["unknown"], "x", None
        )

class uQTileScan(_QTileTruss):
    def test_events(self):
        for i in range(2):
            pid = os.fork()
            if pid == 0:
                os.execv("scripts/window", ["scripts/window", self["display"], str(i)])
            time.sleep(0.1)
        self.startQtile()
        assert self.c.clientcount() == 2

    def tearDown(self):
        _QTileTruss.tearDown(self)
        self.stopQtile()


tests = [
    XNest(xinerama=True), [
        uQTile(),
        uQTileScan(),
    ],
    XNest(xinerama=False), [
        uQTile()
    ],
    uKey()
]
