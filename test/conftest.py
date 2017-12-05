# Copyright (c) 2011 Florian Mounier
# Copyright (c) 2011 Anshuman Bhaduri
# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014-2015 Tycho Andersen
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from __future__ import print_function

import libqtile
import libqtile.ipc
from libqtile.manager import Qtile as QtileManager
from libqtile.log_utils import init_log

import logging
import multiprocessing
import os
import pytest
import subprocess
import sys
import tempfile
import time
import traceback

import xcffib
import xcffib.xproto

# the default sizes for the Xephyr windows
WIDTH = 800
HEIGHT = 600
SECOND_WIDTH = 640
SECOND_HEIGHT = 480

max_sleep = 20.0
sleep_time = 0.1
class retry:
    def __init__(self, fail_msg='retry failed!', ignore_exceptions=(),
                 dt=sleep_time, tmax=max_sleep):
        self.fail_msg = fail_msg
        self.ignore_exceptions = ignore_exceptions
        self.dt = dt
        self.tmax = tmax

    def __call__(self, fn):
        import time
        from functools import wraps

        @wraps(fn)
        def wrapper(*args, **kwargs):
            _time, _sleep = time.time, time.sleep
            tmax = self.tmax
            tmax += _time()
            dt = self.dt
            ignore_exceptions = self.ignore_exceptions

            while _time() <= tmax:
                try:
                    return fn(*args, **kwargs)
                except ignore_exceptions:
                    pass
                _sleep(dt)
                dt *= 1.5
            raise AssertionError(self.fail_msg)
        return wrapper


@retry(ignore_exceptions=(xcffib.ConnectionException,))
def can_connect_x11(disp=':0'):
    conn = xcffib.connect(display=disp)
    conn.disconnect()
    return True

@retry(ignore_exceptions=(libqtile.ipc.IPCError,))
def can_connect_qtile(socket_path):
    client = libqtile.command.Client(socket_path)
    val = client.status()
    if val == 'OK':
        return True
    return False

def _find_display():
    """Returns the next available display"""
    from xvfbwrapper import Xvfb
    xvfb = Xvfb()
    return xvfb._get_next_unused_display()

def whereis(program):
    """Search PATH for executable"""
    for path in os.environ.get('PATH', '').split(':'):
        if os.path.exists(os.path.join(path, program)) and \
           not os.path.isdir(os.path.join(path, program)):
            return os.path.join(path, program)
    return None


class BareConfig(object):
    auto_fullscreen = True
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
        libqtile.config.Group("c"),
        libqtile.config.Group("d")
    ]
    layouts = [
        libqtile.layout.stack.Stack(num_stacks=1),
        libqtile.layout.stack.Stack(num_stacks=2)
    ]
    floating_layout = libqtile.layout.floating.Floating()
    keys = [
        libqtile.config.Key(
            ["control"],
            "k",
            libqtile.command._Call([("layout", None)], "up")
        ),
        libqtile.config.Key(
            ["control"],
            "j",
            libqtile.command._Call([("layout", None)], "down")
        ),
    ]
    mouse = []
    screens = [libqtile.config.Screen()]
    main = None
    follow_mouse_focus = False


class Xephyr(object):
    """Spawn Xephyr instance

    Set-up a Xephyr instance with the given parameters.  The Xephyr instance
    must be started, and then stopped.
    """
    def __init__(self, xinerama=True, randr=False, two_screens=True,
                 width=WIDTH, height=HEIGHT, xoffset=None):
        self.xinerama, self.randr = xinerama, randr
        self.two_screens = two_screens

        self.width = width
        self.height = height
        if xoffset is None:
            self.xoffset = width
        else:
            self.xoffset = xoffset

        self.proc = None  # Handle to Xephyr instance, subprocess.Popen object
        self.display = None

    def start_xephyr(self):
        """Start Xephyr instance

        Starts the Xephyr instance and sets the `self.display` to the display
        which is used to setup the instance.
        """
        # we'll try twice to open Xephyr
        for _ in range(2):
            # get a new display
            self.display = ":{}".format(_find_display())

            # build up arguments
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

            self.proc = subprocess.Popen(args)

            start = time.time()
            # wait for X display to come up
            if can_connect_x11(self.display):
                return
        else:
            # we wern't able to get a display up
            self.display = None
            raise AssertionError("Unable to start Xephyr, quit with return code {:d}".format(
                self.proc.returncode
            ))

    def stop_xephyr(self):
        """Stop the Xephyr instance"""
        # Xephyr must be started first
        if self.proc is None:
            return

        # Kill xephyr only if it is running
        if self.proc.poll() is None:
            # We should always be able to kill xephyr nicely
            self.proc.terminate()
        self.proc.wait()

        self.proc = None


class Qtile(object):
    """Spawn a Qtile instance

    Setup a qtile server instance on the given display, with the given socket
    and log files.  The qtile server must be started, and then stopped when it
    is done.  Windows can be spawned for the qtile instance to interact with
    with various `.test_*` methods.
    """
    def __init__(self, sockfile, display):
        self.sockfile = sockfile
        self.display = display

        self.proc = None
        self.c = None
        self.testwindows = []

    def start(self, config_class):
        rpipe, wpipe = multiprocessing.Pipe()

        def run_qtile():
            try:
                init_log(logging.INFO, log_path=None, log_color=False)
                q = QtileManager(config_class(), self.display, self.sockfile)
                q.loop()
            except Exception:
                wpipe.send(traceback.format_exc())

        self.proc = multiprocessing.Process(target=run_qtile)
        self.proc.start()

        # First, wait for socket to appear
        if can_connect_qtile(self.sockfile):
            self.c = libqtile.command.Client(self.sockfile)
            return
        if rpipe.poll(sleep_time):
            error = rpipe.recv()
            raise AssertionError("Error launching Qtile, traceback:\n%s" % error)
        raise AssertionError("Error launching Qtile")

    def create_manager(self, config_class):
        """Create a Qtile manager instance in this thread

        This should only be used when it is known that the manager will throw
        an error and the returned manager should not be started, otherwise this
        will likely block the thread.
        """
        init_log(logging.INFO, log_path=None, log_color=False)
        return QtileManager(config_class(), self.display, self.sockfile)

    def terminate(self):
        if self.proc is None:
            print("Qtile is not alive", file=sys.stderr)
        else:
            # try to send SIGTERM and wait up to 10 sec to quit
            self.proc.terminate()
            self.proc.join(10)

            if self.proc.is_alive():
                # desperate times... this probably messes with multiprocessing...
                try:
                    os.kill(self.proc.pid, 9)
                    self.proc.join()
                except OSError:
                    # The process may have died due to some other error
                    pass

            if self.proc.exitcode:
                print("Qtile exited with exitcode: %d" % self.proc.exitcode, file=sys.stderr)

            self.proc = None

        for proc in self.testwindows[:]:
            proc.terminate()
            proc.wait()

            self.testwindows.remove(proc)

    def _spawn_window(self, *args):
        """Starts a program which opens a window

        Spawns a new subprocess for a command that opens a window, given by the
        arguments to this method.  Spawns the new process and checks that qtile
        maps the new window.
        """
        if not args:
            raise AssertionError("Trying to run nothing! (missing arguments)")
        client = self.c
        start = len(client.windows())
        proc = subprocess.Popen(args, env={"DISPLAY": self.display})
        @retry(ignore_exceptions=(RuntimeError,))
        def success():
            while proc.poll() is None:
                if len(client.windows()) > start:
                    return True
            return False
        if success():
            self.testwindows.append(proc)
        else:
            proc.terminate()
            proc.wait()
            raise AssertionError("Window never appeared...")
        return proc

    def _spawn_script(self, script, *args):
        python = sys.executable
        d = os.path.dirname(os.path.realpath(__file__))
        python = sys.executable
        path = os.path.join(d, "scripts", script)
        return self._spawn_window(python, path, *args)

    def kill_window(self, proc):
        """Kill a window and check that qtile unmaps it

        Kills a window created by calling one of the `self.test*` methods,
        ensuring that qtile removes it from the `windows` attribute.
        """
        assert proc in self.testwindows, "Given process is not a spawned window"
        start = len(self.c.windows())
        proc.terminate()
        proc.wait()
        self.testwindows.remove(proc)
        @retry(ignore_exceptions=(ValueError,))
        def success():
            if len(self.c.windows()) < start:
                return True
            raise ValueError('window is still in client list!')

        if not success():
            raise AssertionError("Window could not be killed...")

    def testWindow(self, name):
        return self._spawn_script("window.py", self.display, name)

    def testTkWindow(self, name, wm_type):
        return self._spawn_script("tkwindow.py", name, wm_type)

    def testDialog(self, name="dialog"):
        return self.testTkWindow(name, "dialog")

    def testNotification(self, name="notification"):
        """
        Simulate a notification window. Note that, for testing purposes, this
        process must be killed explicitly, unlike actual notifications which
        are sent to a notification server and then expire after a timeout.
        """
        # Don't use a real notification, e.g. notify-send or
        # zenity --notification, since we want to keep the process on until
        # explicitly killed
        return self.testTkWindow(name, "notification")

    def testXclock(self):
        path = whereis("xclock")
        return self._spawn_window(path)

    def testXeyes(self):
        path = whereis("xeyes")
        return self._spawn_window(path)

    def testGkrellm(self):
        path = whereis("gkrellm")
        return self._spawn_window(path)

    def testXcalc(self):
        path = whereis("xcalc")
        return self._spawn_window(path)

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


@pytest.yield_fixture(scope="session")
def xvfb():
    display = ":{:d}".format(_find_display())
    args = ["Xvfb", display, "-screen", "0", "800x600x16"]
    proc = subprocess.Popen(args)
    if not can_connect_x11(display):
        raise OSError("Xvfb did not come up")
    os.environ['DISPLAY'] = display
    yield
    proc.terminate()
    proc.wait()


@pytest.yield_fixture(scope="function")
def xephyr(request, xvfb):
    kwargs = getattr(request, "param", {})

    x = Xephyr(**kwargs)
    try:
        x.start_xephyr()

        yield x
    finally:
        x.stop_xephyr()


@pytest.yield_fixture(scope="function")
def qtile(request, xephyr):
    config = getattr(request, "param", BareConfig)

    with tempfile.NamedTemporaryFile() as f:
        sockfile = f.name
        q = Qtile(sockfile, xephyr.display)
        try:
            q.start(config)

            yield q
        finally:
            q.terminate()


@pytest.yield_fixture(scope="function")
def qtile_nospawn(request, xephyr):
    with tempfile.NamedTemporaryFile() as f:
        sockfile = f.name
        q = Qtile(sockfile, xephyr.display)

        try:
            yield q
        finally:
            q.terminate()


no_xinerama = pytest.mark.parametrize("xephyr", [{"xinerama": False}], indirect=True)
