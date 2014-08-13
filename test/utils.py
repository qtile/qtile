import libqtile
import libqtile.hook
import libqtile.ipc

import logging
import multiprocessing
import os
import select
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import xcb
import xcb.xproto
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
                 width=WIDTH, height=HEIGHT, xoffset=None):
        self.xinerama, self.randr = xinerama, randr
        self.config = config
        self.start_qtile = start_qtile
        self.two_screens = two_screens

        self.width = width
        self.height = height
        if xoffset is None:
            self.xoffset = width
        else:
            self.xoffset = xoffset

        self.qtile = None # Handle to Qtile instance, multiprocessing.Process object
        self.xephyr = None # Handle to Xephyr instance, subprocess.Popen object
        self.display = DISPLAY

    def __call__(self, function):
        def teardown():
            # Remove temorary files
            if os.path.exists(self.tempdir):
                shutil.rmtree(self.tempdir)

            # Shutdown Xephyr
            self._stopXephyr()

        def setup():
            # Setup socket and log files
            self.tempdir = tempfile.mkdtemp()
            self.sockfile = os.path.join(self.tempdir, 'qtile.sock')

            # Setup Xephyr
            try:
                self._startXephyr()
            except AssertionError:
                teardown()
                raise

            self.testwindows = []

        @attr('xephyr')
        @with_setup(setup, teardown)
        @wraps(function)
        def wrapped_fun():
            try:
                if self.start_qtile:
                    self.startQtile(self.config)
                return function(self)
            finally:
                # If we started qtile, we should be sure to take it down
                if self.start_qtile:
                    libqtile.hook.clear()
                    self.stopQtile()
                # If we didn't start qtile, make sure the user took it down if needed
                if self.qtile and not self.start_qtile:
                    raise AssertionError("Stop qtile!")

        return wrapped_fun

    def _startXephyr(self):
        args = [
            "Xephyr", "-name", "qtile_test",
            self.display, "-ac",
            "-screen", "%sx%s" % (self.width, self.height)]
        if self.two_screens:
            args.extend(["-origin", "%s,0" % self.xoffset, "-screen",
                "%sx%s" % (SECOND_WIDTH, SECOND_HEIGHT)])

        if self.xinerama:
            args.extend(["+xinerama"])
        if self.randr:
            args.extend(["+extension", "RANDR"])

        self.xephyr = subprocess.Popen(args,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        self._waitForXephyr()

    def _stopXephyr(self):
        assert self.xephyr is not None, "Xephyr must be started first"

        # Complain if qtile or windows are running, but still kill xephyr
        try:
            assert self.qtile is None, "Kill Qtile before stopping Xephyr"
            assert self.testwindows == [], "Kill all test windows before stopping Xephyr"
        finally:
            self.xephyr.kill()
            self.xephyr.wait()

            self.xephyr = None

    def _waitForXephyr(self):
        start = time.time()
        while time.time() < start + 10:
            # Wait until Xephyr display is up...
            try:
                conn = xcb.xcb.connect(self.display)
                break
            except xcb.ConnectException:
                pass

            # or the Xephyr process ends...
            ret = self.xephyr.poll()
            if ret is not None:
                raise AssertionError("Xephyr quit with return code: %d" % proc.returncode)
        else:
            # or the setup timesout
            raise AssertionError("Xephyr did not come up")

        conn.disconnect()
        del conn

    def startQtile(self, config):
        rpipe, wpipe = multiprocessing.Pipe()

        def runQtile():
            try:
                q = libqtile.manager.Qtile(
                    config, self.display, self.sockfile,
                    log=libqtile.manager.init_log(logging.CRITICAL))
                q.loop()
            except Exception:
                wpipe.send(traceback.format_exc())

        self.qtile = multiprocessing.Process(target=runQtile)
        self.qtile.start()

        self.c = libqtile.command.Client(self.sockfile)
        self._waitForQtile(rpipe)

    def stopQtile(self):
        assert self.qtile is not None, "Qtile must be started first"

        self.qtile.terminate()
        self.qtile.join(10)

        if self.qtile.is_alive():
            # desparate times...
            try:
                self._kill(self.qtile.pid)
            except OSError:
                # The process may have died due to some other error
                pass

        self.qtile = None

        # Kill all the windows
        for pid in self.testwindows[:]:
            self._kill(pid)

    def _waitForQtile(self, errpipe):
        start = time.time()
        while time.time() < start + 10:
            try:
                if self.c.status() == "OK":
                    break
            except libqtile.ipc.IPCError:
                pass

            if errpipe.poll(0.1):
                error = errpipe.recv()
                raise AssertionError("Error launching Qtile, traceback:\n%s" % error)
        else:
            raise AssertionError("Qtile quit without exception")

    def _testProc(self, path, args):
        if path is None:
            raise AssertionError("Trying to run None! (missing executable)")
        start = len(self.c.windows())
        pid = os.fork()
        if pid == 0:
            try:
                os.execve(path, args, {"DISPLAY": self.display})
            finally:
                os._exit(1)
        for i in range(20):
            if len(self.c.windows()) > start:
                break
            time.sleep(0.1)
        else:
            raise AssertionError("Window never appeared...")
        self.testwindows.append(pid)
        return pid

    def groupconsistency(self):
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

    def qtileRaises(self, exc, config):
        assert_raises(exc, libqtile.manager.Qtile,
                      config, self.display, self.sockfile)

    def testWindow(self, name):
        python = sys.executable
        d = os.path.dirname(os.path.realpath(__file__))
        path = os.path.join(d, "scripts", "window.py")
        return self._testProc(
                    python,
                    [python, path, self.display, name]
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
