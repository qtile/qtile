import subprocess, os, time, sys, socket, traceback
import Xlib.display, Xlib.X
import libpry
import libqtile, libqtile.ipc

WIDTH = 800
HEIGHT = 600

class XNest(libpry.TestContainer):
    def __init__(self, xinerama, display=":1"):
        libpry.TestContainer.__init__(self)
        self.xinerama = xinerama
        if xinerama:
            self.name = "XNestXinerama"
        self["display"] = display
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
    def __init__(self, xinerama, display=":1"):
        libpry.TestContainer.__init__(self)
        self.xinerama = xinerama
        if xinerama:
            self.name = "XephyrXinerama"
        self["display"] = display
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


class _QTileTruss(libpry.TmpDirMixin, libpry.AutoTree):
    qtilepid = None
    def setUp(self):
        libpry.TmpDirMixin.setUp(self)
        self.testwindows = []

    def tearDown(self):
        libpry.TmpDirMixin.tearDown(self)

    def startQtile(self, config):
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
                q = libqtile.QTile(config, self["display"], self["fname"])
                q.testing = True
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
            # Wait until qtile is up before continuing
            for i in range(20):
                try:
                    if self.c.status() == "OK":
                        break
                except libqtile.ipc.IPCError:
                    pass
                time.sleep(0.1)
            else:
                raise AssertionError, "Timeout waiting for Qtile"

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
        start = len(self.c.clients())
        pid = os.fork()
        if pid == 0:
            os.execv("scripts/window", ["scripts/window", self["display"], name])
        for i in range(20):
            if len(self.c.clients()) > start:
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
        start = len(self.c.clients())
        self._kill(pid)
        for i in range(20):
            if len(self.c.clients()) < start:
                break
            time.sleep(0.1)
        else:
            raise AssertionError("Window could not be killed...")


class QTileTests(_QTileTruss):
    config = None
    def setUp(self):
        _QTileTruss.setUp(self)
        self.startQtile(self.config)

    def tearDown(self):
        _QTileTruss.tearDown(self)
        self.stopQtile()
