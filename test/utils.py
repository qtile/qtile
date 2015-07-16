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

import libqtile
import libqtile.ipc
from libqtile.manager import Qtile, init_log

import logging
import multiprocessing
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import xcffib
import xcffib.xproto
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

        # Handle to Qtile instance, multiprocessing.Process object
        self.qtile = None
        # Handle to Xephyr instance, subprocess.Popen object
        self.xephyr = None
        self.display = ":{}".format(_find_display())

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
            self.logfile = os.path.join(self.tempdir, 'qtile.log')

            self.testwindows = []

            # Setup Xephyr
            try:
                self._startXephyr()
            except AssertionError:
                teardown()
                raise

        @attr('xephyr')
        @with_setup(setup, teardown)
        @wraps(function)
        def wrapped_fun():
            try:
                if self.start_qtile:
                    self.startQtile(self.config)
                return function(self)
            finally:
                if os.path.exists(self.logfile):
                    with open(self.logfile) as f:
                        log_output = f.read().strip()
                    if log_output:
                        print("------------------------ >> begin log file << ------------------------")
                        print(log_output)
                        print("------------------------- >> end log file << -------------------------")
                    else:
                        print("------------------------ >> log file empty << ------------------------")
                # If we started qtile, we should be sure to take it down
                if self.start_qtile:
                    self.stopQtile()
                # If we didn't start qtile, make sure the user took it down if needed
                if self.qtile and not self.start_qtile:
                    raise AssertionError("Stop qtile!")

        return wrapped_fun

    def _startXephyr(self, restart=True):
        args = [
            "Xephyr", "-name", "qtile_test",
            self.display, "-ac",
            "-screen", "%sx%s" % (self.width, self.height)]
        if self.two_screens:
            args.extend(
                [
                    "-origin", "%s,0" % self.xoffset, "-screen",
                    "%sx%s" % (SECOND_WIDTH, SECOND_HEIGHT)
                ]
            )

        if self.xinerama:
            args.extend(["+xinerama"])
        if self.randr:
            args.extend(["+extension", "RANDR"])

        self.xephyr = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        try:
            self._waitForXephyr()
        except AssertionError:
            # We'll try to get a new display and try one more time...
            if restart:
                self.display = ":{}".format(_find_display())
                self._startXephyr(restart=False)
            else:
                raise

    def _stopXephyr(self):
        assert self.xephyr is not None, "Xephyr must be started first"

        # Complain if qtile or windows are running, but still kill xephyr
        try:
            assert self.qtile is None, "Kill Qtile before stopping Xephyr"
            assert self.testwindows == [], "Kill all test windows before stopping Xephyr"
        finally:
            # Kill xephyr only if it is running
            if self.xephyr.poll() is None:
                self._kill(self.xephyr)
            self.xephyr = None

    def _waitForXephyr(self):
        # Wait until Xephyr process dies
        while self.xephyr.poll() is None:
            try:
                conn = xcffib.connect(self.display)
                break
            except xcffib.ConnectionException:
                pass
            time.sleep(0.1)
        else:
            (stdout_data, stderr_data) = self.xephyr.communicate()
            raise AssertionError(
                "Error launching Xephyr, quit with return code: {:d}\n"
                "stderr: {}\n"
                "stdout: {}".format(
                    self.xephyr.returncode,
                    stderr_data.decode(),
                    stdout_data.decode()
                )
            )

        conn.disconnect()
        del conn

    def startQtile(self, config):
        rpipe, wpipe = multiprocessing.Pipe()

        def runQtile():
            try:
                q = Qtile(config, self.display, self.sockfile,
                          log=init_log(logging.INFO, log_path=self.logfile))
                q.loop()
            except Exception:
                wpipe.send(traceback.format_exc())
                print("--------------------- >> begin qtile traceback << --------------------")
                print(traceback.format_exc())
                print("-------------------- >> begin qtile traceback << ---------------------")

        self.qtile = multiprocessing.Process(target=runQtile)
        self.qtile.start()

        self._waitForQtile(rpipe)

    def stopQtile(self):
        assert self.qtile is not None, "Qtile must be started first"

        self.qtile.terminate()
        self.qtile.join(10)

        if self.qtile.is_alive():
            # desparate times... this probably messes with multiprocessing...
            try:
                os.kill(self.qtile.pid, 9)
                os.waitpid(self.qtile.pid, 0)
            except OSError:
                # The process may have died due to some other error
                pass

        if self.qtile.exitcode:
            print("Qtile exited with exitcode: %d" % self.qtile.exitcode)

        self.qtile = None

        # Kill all the windows
        for proc in self.testwindows[:]:
            self._kill(proc)

    def _waitForQtile(self, errpipe):
        # First, wait for socket to appear
        start = time.time()
        while time.time() < start + 10:
            if os.path.exists(self.sockfile):
                break

            if errpipe.poll(0.1):
                error = errpipe.recv()
                raise AssertionError("Error launching Qtile, traceback:\n%s" % error)
        else:
            raise AssertionError("Error launching Qtile, socket never came up")

        self.c = libqtile.command.Client(self.sockfile)

        # Next, wait for server to come up
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
            raise AssertionError("Error launching Qtile, quit without exception")

    def _testProc(self, args):
        if not args:
            raise AssertionError("Trying to run nothing! (missing arguments)")
        start = len(self.c.windows())

        proc = subprocess.Popen(args, env={"DISPLAY": self.display})

        while proc.poll() is None:
            try:
                if len(self.c.windows()) > start:
                    break
            except RuntimeError:
                pass
            time.sleep(0.1)
        else:
            raise AssertionError("Window never appeared...")

        self.testwindows.append(proc)
        return proc

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
        assert_raises(exc, Qtile,
                      config, self.display, self.sockfile)

    def testWindow(self, name):
        python = sys.executable
        d = os.path.dirname(os.path.realpath(__file__))
        python = sys.executable
        path = os.path.join(d, "scripts", "window.py")
        return self._testProc(
            [python, path, self.display, name]
        )

    def testXclock(self):
        path = whereis("xclock")
        return self._testProc(
            [path]
        )

    def testXeyes(self):
        path = whereis("xeyes")
        return self._testProc(
            [path]
        )

    def testGkrellm(self):
        path = whereis("gkrellm")
        return self._testProc(
            [path]
        )

    def testXterm(self):
        path = whereis("xterm")
        return self._testProc(
            [path]
        )

    def _kill(self, proc):
        proc.kill()
        proc.wait()
        if proc in self.testwindows:
            self.testwindows.remove(proc)

    def kill(self, proc):
        start = len(self.c.windows())
        self._kill(proc)
        for i in range(20):
            if len(self.c.windows()) < start:
                break
            time.sleep(0.1)
        else:
            raise AssertionError("Window could not be killed...")
