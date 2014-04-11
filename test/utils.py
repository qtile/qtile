import libqtile
import libqtile.hook
import libqtile.ipc
import logging
import os
import subprocess
import sys
import time
import traceback
import Xlib.X
import Xlib.display
from nose.tools import with_setup, assert_raises
from nose.plugins.attrib import attr
from functools import wraps
WIDTH = 800
HEIGHT = 600
SECOND_WIDTH = 640
SECOND_HEIGHT = 480


def _find_display():
    """
        Returns the next available display
    """
    display = 1
    while os.path.exists("/tmp/.X%s-lock" % display):
        display += 1
    return display

DISPLAY = ":%s" % _find_display()


def whereis(program):
    for path in os.environ.get('PATH', '').split(':'):
        if os.path.exists(os.path.join(path, program)) and \
           not os.path.isdir(os.path.join(path, program)):
            return os.path.join(path, program)
    return None


class Xephyr(object):
    def __init__(self, xinerama, config, start_qtile=True,
                 randr=False, two_screens=True,
                 width=WIDTH, height=HEIGHT):
        self.xinerama, self.randr = xinerama, randr
        self.config = config
        self.start_qtile = start_qtile
        self.name = "xephyr"
        if xinerama:
            self.name += "_xinerama"
        if randr:
            self.name += "_randr"
        self.two_screens = two_screens
        self.display = DISPLAY
        self.xinerama = xinerama
        self.width = width
        self.height = height
        self.fname = '/tmp/qtilesocket'

    def __call__(self, function):
        def setup():
            args = [
                "Xephyr", "-keybd", "evdev",
                "-name", "qtile_test",
                self.display, "-ac",
                "-screen", "%sx%s" % (self.width, self.height)]
            if self.two_screens:
                args.extend(["-origin", "800,0", "-screen", "%sx%s" % (
                    SECOND_WIDTH, SECOND_HEIGHT)])

            if self.xinerama:
                args.extend(["+xinerama"])
            if self.randr:
                args.extend(["+extension", "RANDR"])
            self.sub = subprocess.Popen(
                            args,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                        )
            time.sleep(0.05)
            self.testwindows = []
            if self.start_qtile:
                self.startQtile(self.config)

        def teardown():
            if self.start_qtile:
                libqtile.hook.clear()
                self.stopQtile()
            os.kill(self.sub.pid, 9)
            os.waitpid(self.sub.pid, 0)

        @wraps(function)
        def wrapped_fun():
            return function(self)

        return attr('xephyr')(with_setup(setup, teardown)(wrapped_fun))

    def _groupconsistency(self):
        groups = self.c.groups()
        screens = self.c.screens()
        seen = set()
        for g in groups.values():
            scrn = g["screen"]
            if scrn is not None:
                if scrn in seen:
                    raise AssertionError(
                        "Screen referenced from more than one group.")
                seen.add(scrn)
                assert screens[scrn]["group"] == g["name"]
        assert len(seen) == len(screens), "Not all screens \
        had an attached group."

    def _waitForXephyr(self):
        # Try until Xephyr is up
        for i in range(50):
            try:
                d = Xlib.display.Display(self.display)
                break
            except (Xlib.error.DisplayConnectionError,
                    Xlib.error.ConnectionClosedError):
                time.sleep(0.1)
        else:
            raise AssertionError("Could not connect to display.")
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
            raise AssertionError("Timeout waiting for Qtile")

    def startQtile(self, config):
        self._waitForXephyr()
        pid = os.fork()
        if pid == 0:
            try:
                q = libqtile.manager.Qtile(
                    config, self.display, self.fname,
                    log=libqtile.manager.init_log(logging.CRITICAL))
                q.loop()
            except Exception:
                traceback.print_exc(file=sys.stderr)
            sys.exit(0)
        else:
            self.qtilepid = pid
            self.c = libqtile.command.Client(self.fname)
            self._waitForQtile()

    def stopQtile(self):
        assert self.c.status()
        if self.qtilepid:
            try:
                self._kill(self.qtilepid)
            except OSError:
                # The process may have died due to some other error
                pass
        for pid in self.testwindows[:]:
            self._kill(pid)

    def _testProc(self, path, args):
        if path is None:
            raise AssertionError("Trying to run None! (missing executable)")
        start = len(self.c.windows())
        pid = os.fork()
        if pid == 0:
            os.putenv("DISPLAY", self.display)
            os.execv(path, args)
        for i in range(20):
            if len(self.c.windows()) > start:
                break
            time.sleep(0.1)
        else:
            raise AssertionError("Window never appeared...")
        self.testwindows.append(pid)
        return pid

    def qtileRaises(self, exc, config):
        self._waitForXephyr()
        assert_raises(exc, libqtile.manager.Qtile,
                      config, self.display, self.fname)

    def testWindow(self, name):
        d = os.path.dirname(os.path.realpath(__file__))
        path = os.path.join(d, "scripts", "window.py")
        return self._testProc(
                    path,
                    [path, self.display, name]
                )

    def testXclock(self):
        path = whereis("xclock")
        return self._testProc(
                    path,
                    [path, "-display", self.display]
                )

    def testXeyes(self):
        path = whereis("xeyes")
        return self._testProc(
                    path,
                    [path, "-display", self.display]
                )

    def testGkrellm(self):
        path = whereis("gkrellm")
        return self._testProc(
                    path,
                    [path]
                )

    def testXterm(self):
        path = whereis("xterm")
        return self._testProc(
                    path,
                    [path, "-display", self.display]
                )

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
