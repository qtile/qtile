"""
This file contains various helpers and basic variables for the test suite.

Defining them here rather than in conftest.py avoids issues with circular imports
between test/conftest.py and test/backend/<backend>/conftest.py files.
"""

import functools
import logging
import multiprocessing
import os
import subprocess
import sys
import tempfile
import time
import traceback
from abc import ABCMeta, abstractmethod
from pathlib import Path

from libqtile import command, config, ipc, layout
from libqtile.confreader import Config
from libqtile.core.manager import Qtile
from libqtile.lazy import lazy
from libqtile.log_utils import init_log
from libqtile.resources import default_config

# the sizes for outputs
WIDTH = 800
HEIGHT = 600
SECOND_WIDTH = 640
SECOND_HEIGHT = 480

max_sleep = 5.0
sleep_time = 0.1


class Retry:
    def __init__(self, fail_msg='retry failed!', ignore_exceptions=(),
                 dt=sleep_time, tmax=max_sleep, return_on_fail=False):
        self.fail_msg = fail_msg
        self.ignore_exceptions = ignore_exceptions
        self.dt = dt
        self.tmax = tmax
        self.return_on_fail = return_on_fail

    def __call__(self, fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            tmax = time.time() + self.tmax
            dt = self.dt
            ignore_exceptions = self.ignore_exceptions

            while time.time() <= tmax:
                try:
                    return fn(*args, **kwargs)
                except ignore_exceptions:
                    pass
                except AssertionError:
                    break
                time.sleep(dt)
                dt *= 1.5
            if self.return_on_fail:
                return False
            else:
                raise AssertionError(self.fail_msg)
        return wrapper


class BareConfig(Config):
    auto_fullscreen = True
    groups = [
        config.Group("a"),
        config.Group("b"),
        config.Group("c"),
        config.Group("d")
    ]
    layouts = [
        layout.stack.Stack(num_stacks=1),
        layout.stack.Stack(num_stacks=2)
    ]
    floating_layout = default_config.floating_layout
    keys = [
        config.Key(
            ["control"],
            "k",
            lazy.layout.up(),
        ),
        config.Key(
            ["control"],
            "j",
            lazy.layout.down(),
        ),
    ]
    mouse = []
    screens = [config.Screen()]
    follow_mouse_focus = False
    reconfigure_screens = False


class Backend(metaclass=ABCMeta):
    """A base class to help set up backends passed to TestManager"""
    def __init__(self, env, args=()):
        self.env = env
        self.args = args

    def create(self):
        """This is used to instantiate the Core"""
        return self.core(*self.args)

    def configure(self, manager):
        """This is used to do any post-startup configuration with the manager"""
        pass

    @abstractmethod
    def fake_click(self, x, y):
        """Click at the specified coordinates"""
        pass

    @abstractmethod
    def get_all_windows(self):
        """Get a list of all windows in ascending order of Z position"""
        pass


@Retry(ignore_exceptions=(ipc.IPCError,), return_on_fail=True)
def can_connect_qtile(socket_path, *, ok=None):
    if ok is not None and not ok():
        raise AssertionError()

    ipc_client = ipc.Client(socket_path)
    ipc_command = command.interface.IPCCommandInterface(ipc_client)
    client = command.client.InteractiveCommandClient(ipc_command)
    val = client.status()
    if val == 'OK':
        return True
    return False


class TestManager:
    """Spawn a Qtile instance

    Setup a Qtile server instance on the given display, with the given socket
    and log files.  The Qtile server must be started, and then stopped when it
    is done.  Windows can be spawned for the Qtile instance to interact with
    with various `.test_*` methods.
    """
    def __init__(self, backend, debug_log):
        self.backend = backend
        self.log_level = logging.DEBUG if debug_log else logging.INFO
        self.backend.manager = self

        self.proc = None
        self.c = None
        self.testwindows = []

    def __enter__(self):
        """Set up resources"""
        self._sockfile = tempfile.NamedTemporaryFile()
        self.sockfile = self._sockfile.name
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        """Clean up resources"""
        self.terminate()
        self._sockfile.close()

    def start(self, config_class, no_spawn=False):
        rpipe, wpipe = multiprocessing.Pipe()

        def run_qtile():
            try:
                os.environ.pop("DISPLAY", None)
                os.environ.pop("WAYLAND_DISPLAY", None)
                kore = self.backend.create()
                os.environ.update(self.backend.env)
                init_log(self.log_level, log_path=None, log_color=False)
                Qtile(
                    kore,
                    config_class(),
                    socket_path=self.sockfile,
                    no_spawn=no_spawn,
                ).loop()
            except Exception:
                wpipe.send(traceback.format_exc())

        self.proc = multiprocessing.Process(target=run_qtile)
        self.proc.start()

        # First, wait for socket to appear
        if can_connect_qtile(self.sockfile, ok=lambda: not rpipe.poll()):
            ipc_client = ipc.Client(self.sockfile)
            ipc_command = command.interface.IPCCommandInterface(ipc_client)
            self.c = command.client.InteractiveCommandClient(ipc_command)
            self.backend.configure(self)
            return
        if rpipe.poll(0.1):
            error = rpipe.recv()
            raise AssertionError("Error launching qtile, traceback:\n%s" % error)
        raise AssertionError("Error launching qtile")

    def create_manager(self, config_class):
        """Create a Qtile manager instance in this thread

        This should only be used when it is known that the manager will throw
        an error and the returned manager should not be started, otherwise this
        will likely block the thread.
        """
        init_log(self.log_level, log_path=None, log_color=False)
        kore = self.backend.create()
        config = config_class()
        for attr in dir(default_config):
            if not hasattr(config, attr):
                setattr(config, attr, getattr(default_config, attr))

        return Qtile(kore, config, socket_path=self.sockfile)

    def terminate(self):
        if self.proc is None:
            print("qtile is not alive", file=sys.stderr)
        else:
            # try to send SIGTERM and wait up to 10 sec to quit
            self.proc.terminate()
            self.proc.join(10)

            if self.proc.is_alive():
                print("Killing qtile forcefully", file=sys.stderr)
                # desperate times... this probably messes with multiprocessing...
                try:
                    os.kill(self.proc.pid, 9)
                    self.proc.join()
                except OSError:
                    # The process may have died due to some other error
                    pass

            if self.proc.exitcode:
                print("qtile exited with exitcode: %d" % self.proc.exitcode, file=sys.stderr)

            self.proc = None

        for proc in self.testwindows[:]:
            proc.terminate()
            proc.wait()

            self.testwindows.remove(proc)

    def create_window(self, create, failed=None):
        """
        Uses the function `create` to create a window.

        Waits until qtile actually maps the window and then returns.
        """
        client = self.c
        start = len(client.windows())
        create()

        @Retry(ignore_exceptions=(RuntimeError,), fail_msg='Window never appeared...')
        def success():
            while failed is None or not failed():
                if len(client.windows()) > start:
                    return True
            raise RuntimeError("not here yet")
        return success()

    def _spawn_window(self, *args):
        """Starts a program which opens a window

        Spawns a new subprocess for a command that opens a window, given by the
        arguments to this method.  Spawns the new process and checks that qtile
        maps the new window.
        """
        if not args:
            raise AssertionError("Trying to run nothing! (missing arguments)")

        proc = None

        def spawn():
            nonlocal proc
            # Ensure the client only uses the test display
            env = os.environ.copy()
            env.pop("DISPLAY", None)
            env.pop("WAYLAND_DISPLAY", None)
            env.update(self.backend.env)
            proc = subprocess.Popen(args, env=env)

        def failed():
            if proc.poll() is not None:
                return True
            return False

        self.create_window(spawn, failed=failed)
        self.testwindows.append(proc)
        return proc

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

        @Retry(ignore_exceptions=(ValueError,))
        def success():
            if len(self.c.windows()) < start:
                return True
            raise ValueError('window is still in client list!')

        if not success():
            raise AssertionError("Window could not be killed...")

    def test_window(self, name, floating=False, wm_type="normal"):
        """
        Create a simple window in X or Wayland. If `floating` is True then the wmclass
        is set to "dialog", which triggers auto-floating based on `default_float_rules`.
        `wm_type` can be changed from "normal" to "notification", which creates a window
        that not only floats but does not grab focus.

        Windows created with this method must have their process killed explicitly, no
        matter what type they are.
        """
        python = sys.executable
        path = Path(__file__).parent / "scripts" / "window.py"
        wmclass = "dialog" if floating else "TestWindow"
        return self._spawn_window(python, path, "--name", wmclass, name, wm_type)

    def test_notification(self, name="notification"):
        return self.test_window(name, wm_type="notification")

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
        assert len(seen) == len(screens), "Not all screens had an attached group."


@Retry(ignore_exceptions=(AssertionError,), fail_msg='Window did not die!')
def assert_window_died(client, window_info):
    client.sync()
    wid = window_info['id']
    assert wid not in set([x['id'] for x in client.windows()])
