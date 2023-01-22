import contextlib
import fcntl
import os
import subprocess
from pathlib import Path

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


def xdist_find_display(worker):
    lock_path = Path("/tmp") / worker
    lock_path.mkdir(exist_ok=True)
    worker_id = int(worker[2:])
    display = 1337*(worker_id+1)
    while True:
        try:
            lock_path = lock_path / f".X{display}-lock"
            f = open(lock_path, "w+")
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                f.close()
                raise
        except OSError:
            display += 1
            continue
        return display, f

def xvfb_command(cls, outputs, xoffset):
    args = [
        "Xvfb",
        os.environ['DISPLAY'],
        "-screen",
        "0",
        "{}x{}x{}".format(WIDTH, HEIGHT, cls.depth),
    ]
    if xoffset is None:
        xoffset = WIDTH
    if outputs == 2:
        args.extend(
            [
                "-screen",
                "1",
                "{}x{}x{}@{},0".format(SECOND_WIDTH, SECOND_HEIGHT, cls.depth, xoffset),
            ]
        )
        args.extend(["+xinerama"])
    return args

@contextlib.contextmanager
def xvfb(outputs, xoffset):
    xcffib.testing.XvfbTest._xvfb_command = lambda cls: xvfb_command(cls, outputs, xoffset)
    if worker := os.environ.get("PYTEST_XDIST_WORKER", None):
        xcffib.testing.find_display = lambda: xdist_find_display(worker)
    with xcffib.testing.XvfbTest() as x:
        display = os.environ["DISPLAY"]
        if not can_connect_x11(display):
            raise OSError("Xvfb did not come up")

        yield x


@pytest.fixture(scope="session")
def display():  # noqa: F841
    with xvfb():
        yield os.environ["DISPLAY"]


@contextlib.contextmanager
def x11_environment(outputs, xoffset, **kwargs):
    """This backend needs a Xephyr instance running"""
    with xvfb(outputs, xoffset) as x:
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
