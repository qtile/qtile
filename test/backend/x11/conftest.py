import contextlib
import os
import subprocess

import pytest
import xcffib
import xcffib.testing
import xcffib.xproto
import xcffib.xtest

from libqtile.backend.x11.core import Core
from libqtile.backend.x11.xcbq import Connection
from test.helpers import (
    HEIGHT,
    SECOND_HEIGHT,
    SECOND_WIDTH,
    WIDTH,
    Backend,
    BareConfig,
    Retry,
    TestManager,
)


@Retry(ignore_exceptions=(xcffib.ConnectionException,), return_on_fail=True)
def can_connect_x11(disp=":0", *, ok=None):
    if ok is not None and not ok():
        raise AssertionError()

    conn = xcffib.connect(display=disp)
    conn.disconnect()
    return True


@contextlib.contextmanager
def xvfb():
    with xcffib.testing.XvfbTest():
        display = os.environ["DISPLAY"]
        if not can_connect_x11(display):
            raise OSError("Xvfb did not come up")

        yield


@pytest.fixture(scope="session")
def display():  # noqa: F841
    with xvfb():
        yield os.environ["DISPLAY"]


def start_x11_and_poll_connection(args, display):
    proc = subprocess.Popen(args)

    if can_connect_x11(display, ok=lambda: proc.poll() is None):
        return proc

    # we weren't able to get a display up
    if proc.poll() is None:
        raise AssertionError(f"Unable to connect to running {args[0]}")
    else:
        raise AssertionError(
            f"Unable to start {args[0]}, quit with return code {proc.returncode}"
        )


def stop_x11(proc, display, display_file):
    # Kill xephyr only if it is running
    if proc is not None:
        if proc.poll() is None:
            proc.kill()
        proc.wait()

    # clean up the lock file for the display we allocated
    try:
        display_file.close()
        os.remove(xcffib.testing.lock_path(int(display[1:])))
    except OSError:
        pass


class Xephyr:
    """Spawn Xephyr instance

    Set-up a Xephyr instance with the given parameters.  The Xephyr instance
    must be started, and then stopped.
    """

    def __init__(self, outputs, xoffset=None, xtrace=False):
        self.outputs = outputs
        if xoffset is None:
            self.xoffset = WIDTH
        else:
            self.xoffset = xoffset

        self.proc = None  # Handle to Xephyr instance, subprocess.Popen object
        self.display = None
        self.xephyr_display_file = None

        self.xtrace = xtrace
        self.xtrace_proc = None
        self.xtrace_display = None
        self.xtrace_display_file = None
        self.xephyr_display = None

    def __enter__(self):
        try:
            self.start_xephyr()
        except:  # noqa: E722
            self.stop_xephyr()
            raise

        return self

    def __exit__(self, _exc_type, _exc_val, _exc_tb):
        self.stop_xephyr()

    def start_xephyr(self):
        """Start Xephyr instance

        Starts the Xephyr instance and sets the `self.display` to the display
        which is used to setup the instance.
        """
        # get a new display
        display, self.xephyr_display_file = xcffib.testing.find_display()
        self.display = f":{display}"
        self.xephyr_display = self.display

        # build up arguments
        args = [
            "Xephyr",
            "-name",
            "qtile_test",
            self.xephyr_display,
            "-ac",
            "-screen",
            f"{WIDTH}x{HEIGHT}",
        ]
        if self.outputs == 2:
            args.extend(
                [
                    "-origin",
                    f"{self.xoffset},0",
                    "-screen",
                    f"{SECOND_WIDTH}x{SECOND_HEIGHT}",
                ]
            )
            args.extend(["+xinerama"])
            args.extend(["-extension", "RANDR"])

        start_x11_and_poll_connection(args, self.xephyr_display)

        if self.xtrace:
            # because we run Xephyr without auth and xtrace requires auth, we
            # need to add some x11 auth here for the Xephyr display our xtrace
            # will fail:
            subprocess.check_call(["xauth", "generate", self.xephyr_display])
            display, self.xtrace_display_file = xcffib.testing.find_display()
            self.xtrace_display = f":{display}"
            self.display = self.xtrace_display
            args = [
                "xtrace",
                "--timestamps",
                "-k",
                "-d",
                self.xephyr_display,
                "-D",
                self.xtrace_display,
            ]
            start_x11_and_poll_connection(args, self.xtrace_display)

    def stop_xephyr(self):
        stop_x11(self.proc, self.xephyr_display, self.xephyr_display_file)
        if self.xtrace:
            stop_x11(self.xtrace_proc, self.xtrace_display, self.xtrace_display_file)


@contextlib.contextmanager
def x11_environment(outputs, **kwargs):
    """This backend needs a Xephyr instance running"""
    with xvfb():
        with Xephyr(outputs, **kwargs) as x:
            yield x


@pytest.fixture(scope="function")
def xmanager(request, xephyr):
    """
    This replicates the `manager` fixture except that the x11 backend is hard-coded. We
    cannot simply parametrize the `backend_name` fixture module-wide because it gets
    parametrized by `pytest_generate_tests` in test/conftest.py and only one of these
    parametrize calls can be used.
    """
    config = getattr(request, "param", BareConfig)
    backend = XBackend({"DISPLAY": xephyr.display}, args=[xephyr.display])

    with TestManager(backend, request.config.getoption("--debuglog")) as manager:
        manager.display = xephyr.display
        manager.start(config)
        yield manager


@pytest.fixture(scope="function")
def xmanager_nospawn(request, xephyr):
    """
    This replicates the `manager` fixture except that the x11 backend is hard-coded. We
    cannot simply parametrize the `backend_name` fixture module-wide because it gets
    parametrized by `pytest_generate_tests` in test/conftest.py and only one of these
    parametrize calls can be used.
    """
    backend = XBackend({"DISPLAY": xephyr.display}, args=[xephyr.display])

    with TestManager(backend, request.config.getoption("--debuglog")) as manager:
        manager.display = xephyr.display
        yield manager


@pytest.fixture(scope="function")
def conn(xmanager):
    conn = Connection(xmanager.display)
    yield conn
    conn.finalize()


class XBackend(Backend):
    name = "x11"

    def __init__(self, env, args=()):
        self.env = env
        self.args = args
        self.core = Core
        self.manager = None

    def fake_click(self, x, y):
        """Click at the specified coordinates"""
        conn = Connection(self.env["DISPLAY"])
        root = conn.default_screen.root.wid
        xtest = conn.conn(xcffib.xtest.key)
        xtest.FakeInput(6, 0, xcffib.xproto.Time.CurrentTime, root, x, y, 0)
        xtest.FakeInput(4, 1, xcffib.xproto.Time.CurrentTime, root, 0, 0, 0)
        xtest.FakeInput(5, 1, xcffib.xproto.Time.CurrentTime, root, 0, 0, 0)
        conn.conn.flush()
        self.manager.c.sync()
        conn.finalize()

    def get_all_windows(self):
        """Get a list of all windows in ascending order of Z position"""
        conn = Connection(self.env["DISPLAY"])
        root = conn.default_screen.root.wid
        q = conn.conn.core.QueryTree(root).reply()
        wins = list(q.children)
        conn.finalize()
        return wins
