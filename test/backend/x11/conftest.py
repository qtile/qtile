import contextlib
import os
import subprocess
import tempfile

import pytest
import xcffib
import xcffib.testing
import xcffib.xproto

from libqtile.backend.x11.core import Core
from libqtile.resources import default_config
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
def can_connect_x11(disp=':0', *, ok=None):
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


class Xephyr:
    """Spawn Xephyr instance

    Set-up a Xephyr instance with the given parameters.  The Xephyr instance
    must be started, and then stopped.
    """
    def __init__(self,
                 xinerama=True,
                 two_screens=True,
                 width=WIDTH,
                 height=HEIGHT,
                 xoffset=None):
        self.xinerama = xinerama
        self.two_screens = two_screens

        self.width = width
        self.height = height
        if xoffset is None:
            self.xoffset = width
        else:
            self.xoffset = xoffset

        self.proc = None  # Handle to Xephyr instance, subprocess.Popen object
        self.display = None
        self.display_file = None

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
        display, self.display_file = xcffib.testing.find_display()
        self.display = ":{}".format(display)

        # build up arguments
        args = [
            "Xephyr",
            "-name",
            "qtile_test",
            self.display,
            "-ac",
            "-screen",
            "{}x{}".format(self.width, self.height),
        ]
        if self.two_screens:
            args.extend(["-origin", "%s,0" % self.xoffset, "-screen",
                         "%sx%s" % (SECOND_WIDTH, SECOND_HEIGHT)])
        if self.xinerama:
            args.extend(["+xinerama"])

        self.proc = subprocess.Popen(args)

        if can_connect_x11(self.display, ok=lambda: self.proc.poll() is None):
            return

        # we weren't able to get a display up
        if self.proc.poll() is None:
            raise AssertionError("Unable to connect to running Xephyr")
        else:
            raise AssertionError(
                "Unable to start Xephyr, quit with return code "
                f"{self.proc.returncode}"
            )

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

        # clean up the lock file for the display we allocated
        try:
            self.display_file.close()
            os.remove(xcffib.testing.lock_path(int(self.display[1:])))
        except OSError:
            pass


@contextlib.contextmanager
def x11_environment(**kwargs):
    """This backend needs a Xephyr instance running"""
    with xvfb():
        with Xephyr(**kwargs) as x:
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

    for attr in dir(default_config):
        if not hasattr(config, attr):
            setattr(config, attr, getattr(default_config, attr))

    backend = Backend(Core, [xephyr.display], {"DISPLAY": xephyr.display})

    with tempfile.NamedTemporaryFile() as f:
        sockfile = f.name
        try:
            manager = TestManager(
                sockfile, backend, request.config.getoption("--debuglog")
            )
            manager.display = xephyr.display
            manager.start(config)

            yield manager
        finally:
            manager.terminate()
