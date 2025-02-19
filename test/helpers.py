"""
This file contains various helpers and basic variables for the test suite.

Defining them here rather than in conftest.py avoids issues with circular imports
between test/conftest.py and test/backend/<backend>/conftest.py files.
"""

import faulthandler
import functools
import logging
import multiprocessing
import os
import signal
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
from libqtile.log_utils import init_log, logger
from libqtile.resources import default_config

# the sizes for outputs
WIDTH = 800
HEIGHT = 600
SECOND_WIDTH = 640
SECOND_HEIGHT = 480

LOG_PIPE_BUFFER_SIZE = 128 * 1024

max_sleep = 5.0
sleep_time = 0.1


class Retry:
    def __init__(
        self,
        ignore_exceptions=(),
        dt=sleep_time,
        tmax=max_sleep,
        return_on_fail=False,
    ):
        self.ignore_exceptions = ignore_exceptions
        self.dt = dt
        self.tmax = tmax
        self.return_on_fail = return_on_fail
        self.last_failure = None

    def __call__(self, fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            tmax = time.time() + self.tmax
            dt = self.dt
            ignore_exceptions = self.ignore_exceptions

            while time.time() <= tmax:
                try:
                    return fn(*args, **kwargs)
                except ignore_exceptions as e:
                    self.last_failure = e
                except AssertionError:
                    break
                time.sleep(dt)
                dt *= 1.5
            if self.return_on_fail:
                return False
            else:
                raise self.last_failure

        return wrapper


class BareConfig(Config):
    auto_fullscreen = True
    groups = [config.Group("a"), config.Group("b"), config.Group("c"), config.Group("d")]
    layouts = [layout.stack.Stack(num_stacks=1), layout.stack.Stack(num_stacks=2)]
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

    @abstractmethod
    def fake_click(self, x, y):
        """Click at the specified coordinates"""

    @abstractmethod
    def get_all_windows(self):
        """Get a list of all windows in ascending order of Z position"""


@Retry(ignore_exceptions=(ipc.IPCError,), return_on_fail=True)
def can_connect_qtile(socket_path, *, ok=None):
    if ok is not None and not ok():
        raise AssertionError()

    ipc_client = ipc.Client(socket_path)
    ipc_command = command.interface.IPCCommandInterface(ipc_client)
    client = command.client.InteractiveCommandClient(ipc_command)
    val = client.status()
    if val == "OK":
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
        self.logspipe = None

    def __enter__(self):
        """Set up resources"""
        faulthandler.enable(all_threads=True)
        faulthandler.register(signal.SIGUSR2, all_threads=True)
        self._sockfile = tempfile.NamedTemporaryFile()
        self.sockfile = self._sockfile.name
        return self

    def __exit__(self, _exc_type, _exc_value, _exc_tb):
        """Clean up resources"""
        self.terminate()
        self._sockfile.close()
        if self.logspipe is not None:
            os.close(self.logspipe)

    def get_log_buffer(self):
        """Returns any logs that have been written to qtile's log buffer up to this point."""
        # default pipe size on linux is 64k. we probably won't write
        # 64k of logs, but in the event that we do, qtile will hang in
        # write(). but thanks to e1d2dab16903 ("switch semantics of sigusr2
        # to stack dumping") hopefully we will see it's hung in a log write and
        # look at this. if we do write 64k of logs, we can do some F_SETPIPE_SZ
        # fiddling with the buffer size to grow it to whatever github allows.
        return os.read(self.logspipe, 64 * 1024).decode("utf-8")

    def start(self, config_class, no_spawn=False, state=None):
        readlogs, writelogs = os.pipe()
        rpipe, wpipe = multiprocessing.Pipe()

        def run_qtile():
            try:
                os.environ.pop("DISPLAY", None)
                os.environ.pop("WAYLAND_DISPLAY", None)
                kore = self.backend.create()
                os.environ.update(self.backend.env)

                init_log(self.log_level)
                os.close(readlogs)
                formatter = logging.Formatter("%(levelname)s - %(message)s")
                handler = logging.StreamHandler(os.fdopen(writelogs, "w"))
                handler.setFormatter(formatter)
                logger.addHandler(handler)

                Qtile(
                    kore,
                    config_class(),
                    socket_path=self.sockfile,
                    no_spawn=no_spawn,
                    state=state,
                ).loop()
            except Exception:
                wpipe.send(traceback.format_exc())

        self.proc = multiprocessing.Process(target=run_qtile)
        self.proc.start()
        os.close(writelogs)
        self.logspipe = readlogs

        # First, wait for socket to appear
        if can_connect_qtile(self.sockfile, ok=lambda: not rpipe.poll()):
            ipc_client = ipc.Client(self.sockfile)
            ipc_command = command.interface.IPCCommandInterface(ipc_client)
            self.c = command.client.InteractiveCommandClient(ipc_command)
            self.backend.configure(self)
            return
        if rpipe.poll(0.1):
            error = rpipe.recv()
            raise AssertionError(f"Error launching qtile, traceback:\n{error}")
        raise AssertionError("Error launching qtile")

    def create_manager(self, config_class):
        """Create a Qtile manager instance in this thread

        This should only be used when it is known that the manager will throw
        an error and the returned manager should not be started, otherwise this
        will likely block the thread.
        """
        init_log(self.log_level)
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
                # uh oh, we're hung somewhere. give it another second to print
                # some stack traces
                os.kill(self.proc.pid, signal.SIGUSR2)
                self.proc.join(1)
                print("Killing qtile forcefully", file=sys.stderr)
                # desperate times... this probably messes with multiprocessing...
                try:
                    os.kill(self.proc.pid, signal.SIGKILL)
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

        @Retry(ignore_exceptions=(RuntimeError,))
        def success():
            while failed is None or not failed():
                if len(client.windows()) > start:
                    return True
            raise RuntimeError("window has not appeared yet")

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
            raise ValueError("window is still in client list!")

        if not success():
            raise AssertionError("Window could not be killed...")

    def test_window(
        self,
        name,
        floating=False,
        wm_type="normal",
        new_title="",
        urgent_hint=False,
        export_sni=False,
    ):
        """
        Create a simple window in X or Wayland. If `floating` is True then the wmclass
        is set to "dialog", which triggers auto-floating based on `default_float_rules`.
        `wm_type` can be changed from "normal" to "notification", which creates a window
        that not only floats but does not grab focus.

        Setting `export_sni` to True will publish a simplified StatusNotifierItem interface
        on DBus.

        Windows created with this method must have their process killed explicitly, no
        matter what type they are.
        """
        os.environ.pop("GDK_BACKEND", None)
        python = sys.executable
        path = Path(__file__).parent / "scripts" / "window.py"
        wmclass = "dialog" if floating else "TestWindow"
        args = [python, path, "--name", wmclass, name, wm_type, new_title]
        if urgent_hint:
            args.append("urgent_hint")
            # GTK urgent hint is only available for x11
            os.environ["GDK_BACKEND"] = "x11"
        if export_sni:
            args.append("export_sni_interface")
        return self._spawn_window(*args)

    def test_notification(self, name="notification"):
        return self.test_window(name, wm_type="notification")

    def groupconsistency(self):
        groups = self.c.get_groups()
        screens = self.c.get_screens()
        seen = set()
        for g in groups.values():
            scrn = g["screen"]
            if scrn is not None:
                if scrn in seen:
                    raise AssertionError("Screen referenced from more than one group.")
                seen.add(scrn)
                assert screens[scrn]["group"] == g["name"]
        assert len(seen) == len(screens), "Not all screens had an attached group."


@Retry(ignore_exceptions=(AssertionError,))
def assert_window_died(client, window_info):
    client.sync()
    wid = window_info["id"]
    assert wid not in set([x["id"] for x in client.windows()]), f"window {wid} still here"
