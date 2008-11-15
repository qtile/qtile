import subprocess, os, time, sys, socket, traceback
import Xlib.display, Xlib.X
import libpry
import libqtile, libqtile.ipc

WIDTH = 800
HEIGHT = 600
DISPLAY = ":1"


class XNest(libpry.TestContainer):
    nestx = "xnest"
    def __init__(self, xinerama):
        libpry.TestContainer.__init__(self)
        self.xinerama = xinerama
        self["display"] = DISPLAY
        self["xinerama"] = xinerama

    def setUp(self):
        args = [
            "Xnest", "+kb",
            "-geometry", "%sx%s"%(WIDTH, HEIGHT),
            self["display"], "-ac", "-sync"
        ]
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
                

class Xephyr(libpry.TestContainer):
    nestx = "xephyr"
    def __init__(self, xinerama):
        libpry.TestContainer.__init__(self)
        self.xinerama = xinerama
        self["display"] = DISPLAY
        self["xinerama"] = xinerama

    def setUp(self):
        args = [
            "Xephyr", "+kb",
            "-screen", "%sx%s"%(WIDTH, HEIGHT),
            "-screen", "%sx%s+800+0"%(WIDTH, HEIGHT),
            self["display"], "-ac"
        ]
        if self.xinerama:
            args.extend(["+xinerama"])
        self.sub = subprocess.Popen(
                        args,
                        stdout = subprocess.PIPE,
                        stderr = subprocess.PIPE,
                    )

    def tearDown(self):
        os.kill(self.sub.pid, 9)
        os.waitpid(self.sub.pid, 0)


def xfactory(*args, **kwargs):
    if subprocess.call(["which", "Xephyr"], stdout=subprocess.PIPE):
        return XNest(*args, **kwargs)
    else:
        return Xephyr(*args, **kwargs)


class _QtileTruss(libpry.TmpDirMixin, libpry.AutoTree):
    qtilepid = None
    def setUp(self):
        libpry.TmpDirMixin.setUp(self)
        self.testwindows = []

    def tearDown(self):
        libpry.TmpDirMixin.tearDown(self)

    def _waitForXNest(self):
        # Try until XNest is up
        for i in range(20):
            try:
                d = Xlib.display.Display(self["display"])
                break
            except (Xlib.error.DisplayConnectionError, Xlib.error.ConnectionClosedError), v:
                time.sleep(0.1)
        else:
            raise AssertionError, "Could not connect to display."
        d.close()
        del d

    def _waitForQtile(self):
        for i in range(20):
            try:
                if self.c.status() == "OK":
                    break
            except libqtile.ipc.IPCError:
                pass
            time.sleep(0.1)
        else:
            raise AssertionError, "Timeout waiting for Qtile"

    def qtileRaises(self, exc, config):
        self._waitForXNest()
        self["fname"] = os.path.join(self["tmpdir"], "qtilesocket")
        libpry.raises(exc, libqtile.manager.Qtile, config, self["display"], self["fname"])

    def startQtile(self, config):
        self._waitForXNest()
        self["fname"] = os.path.join(self["tmpdir"], "qtilesocket")
        pid = os.fork()
        if pid == 0:
            try:
                q = libqtile.manager.Qtile(config, self["display"], self["fname"])
                q._testing = True
                # BEWARE: Xnest somehow stuffs up geometry detection for
                # multiple screens in xinerama. We poke into qtile to fix this.
                if self["xinerama"]:
                    q.screens[1].x = WIDTH
                q.loop()
            except Exception, e:
                traceback.print_exc(file=sys.stderr)
            sys.exit(0)
        else:
            self.qtilepid = pid
            self.c = libqtile.command.Client(self["fname"], config)
            self._waitForQtile()

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
        start = len(self.c.windows())
        pid = os.fork()
        if pid == 0:
            os.execv("scripts/window", ["scripts/window", self["display"], name])
        for i in range(20):
            if len(self.c.windows()) > start:
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
        start = len(self.c.windows())
        self._kill(pid)
        for i in range(20):
            if len(self.c.windows()) < start:
                break
            time.sleep(0.1)
        else:
            raise AssertionError("Window could not be killed...")


class QtileTests(_QtileTruss):
    config = None
    def setUp(self):
        _QtileTruss.setUp(self)
        self.startQtile(self.config)

    def tearDown(self):
        _QtileTruss.tearDown(self)
        self.stopQtile()

    def _groupconsistency(self):
        groups = self.c.groups()
        screens = self.c.screens()
        seen = set()
        for g in groups.values():
            scrn = g["screen"]
            if scrn is not None:
                if scrn in seen:
                    raise AssertionError, "Screen referenced from more than one group."
                seen.add(scrn)
                assert screens[scrn]["group"] == g["name"]
        assert len(seen) == len(screens), "Not all screens had an attached group."
