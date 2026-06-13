import contextlib
import fcntl
import os
import select
import subprocess
import time
from pathlib import Path

import pytest

from test.helpers import BareConfig, TestManager

try:
    from libqtile.backend.wayland.core import Core

    has_wayland = True
except ImportError:
    has_wayland = False
from test.helpers import Backend

wlr_env = {
    "WLR_BACKENDS": "headless",
    "WLR_LIBINPUT_NO_DEVICES": "1",
    "WLR_RENDERER_ALLOW_SOFTWARE": "1",
    "WLR_RENDERER": "pixman",
    "XDG_RUNTIME_DIR": "/tmp",
}


@contextlib.contextmanager
def wayland_environment(outputs):
    """This backend just needs some environmental variables set"""
    env = wlr_env.copy()
    env["WLR_HEADLESS_OUTPUTS"] = str(outputs)
    yield env


@pytest.fixture(scope="function")
def wmanager(request, wayland_session):
    """
    This replicates the `manager` fixture except that the Wayland backend is hard-coded.
    We cannot parametrize the `backend_name` fixture module-wide because it gets
    parametrized by `pytest_generate_tests` in test/conftest.py and only one of these
    parametrize calls can be used.
    """
    config = getattr(request, "param", BareConfig)
    backend = WaylandBackend(wayland_session)

    with TestManager(backend, request.config.getoption("--debuglog")) as manager:
        manager.start(config)
        yield manager


class WaylandBackend(Backend):
    name = "wayland"

    def __init__(self, env, args=()):
        self.env = env
        self.args = args
        self.core = Core
        self.manager = None

    def create(self):
        """This is used to instantiate the Core"""
        os.environ.update(self.env)
        core = self.core(*self.args)
        core.add_dummy_input_devices()
        return core

    def configure(self, manager):
        """This backend needs to get WAYLAND_DISPLAY variable."""
        self.env["WAYLAND_DISPLAY"] = manager.c.eval("self.core.display_name")
        # Optionally for XWayland tests get the DISPLAY variable
        self.env["DISPLAY"] = manager.c.eval('os.environ.get("DISPLAY", "")')

    def fake_motion(self, x, y):
        """Move pointer to the specified coordinates"""
        self.manager.c.eval(f"self.core.warp_pointer({x}, {y}, motion=True)")

    def fake_click(self, x, y):
        """Click at the specified coordinates"""
        self.fake_motion(x, y)
        self.manager.c.eval("self.core.fake_click()")

    def get_all_windows(self):
        """Get a list of all windows in ascending order of Z position"""
        tree = self.manager.c.core.stacking_info()
        stack = [tree]
        windows = []
        while stack:
            node = stack.pop()
            if node.get("wid") is not None:
                windows.append(node["wid"])
            stack.extend(reversed(node.get("children", [])))

        return windows


def new_xdg_client(wmanager, name="xdg"):
    """Helper to create 'regular' windows in the XDG shell"""
    pid = wmanager.test_window(name)
    wmanager.c.sync()
    return pid


def new_layer_client(wmanager, name="layer"):
    """Helper to create layer shell windows, which are always static"""
    pid = wmanager.test_notification(name)
    wmanager.c.sync()
    return pid


CLIENT_PATH = Path(__file__) / ".." / ".." / ".." / "wayland_clients" / "bin"


def make_test_env(mgr):
    """Generate environment variables to ensure client connects to test server."""
    env = os.environ.copy()
    env.pop("DISPLAY", None)
    env.pop("WAYLAND_DISPLAY", None)
    env.update(mgr.backend.env)
    return env


class ScriptError(Exception):
    pass


class ClientHandler:
    def __init__(self, cmd, manager):
        if Path(cmd).is_absolute():
            cmd_path = Path(cmd)
        else:
            cmd_path = (CLIENT_PATH / cmd).resolve()

        if not cmd_path.exists():
            assert False, f"{cmd_path.as_posix()} not found."

        self.cmd = cmd_path.as_posix()

        self.process = None
        self.manager = manager

    def __enter__(self):
        self._run()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def _run(self):
        if self.cmd is None:
            assert False, "No command defined."

        if self.process is not None and self.process.poll() is None:
            return

        self.process = subprocess.Popen(
            [self.cmd],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=make_test_env(self.manager),
        )

        fcntl.fcntl(self.process.stdout.fileno(), fcntl.F_SETFL, os.O_NONBLOCK)

    def stop(self):
        try:
            if self.process and self.process.poll() is None:
                self.process.stdin.write("quit\n")
                self.process.stdin.flush()
                self.process.wait(timeout=2)

        except subprocess.TimeoutExpired:
            self.process.kill()

        finally:
            if self.process:
                self.process.stdin.close()
                self.process.stdout.close()
                self.process.stderr.close()
                self.process = None

    def _send(self, command: str) -> None:
        if self.process is None:
            raise ScriptError("Process not started")

        if self.process.poll() is not None:
            raise ScriptError("Process has exited")
        self.flush_manager()
        self.process.stdin.write(command + "\n")
        self.process.stdin.flush()
        self.flush_manager()

    def send(self, command: str) -> str:
        """
        Send a command and wait for one-line response.
        Expected responses:
            OK
            ERROR: message
        """
        self._send(command)

        while True:
            response = self.process.stdout.readline()

            if response == "":
                if self.process.poll() is None:
                    continue

                stderr = self.process.stderr.read().strip()
                raise ScriptError(f"Process closed stdout. stderr={stderr}")

            break

        return response.strip()

    def assert_no_text(self, timeout_ms=200):
        """
        Verifies that no next is output by the client during a specified time period.

        Useful if you want to demonstrate that no text is output by the clien
        e.g. responding to a message from the compositor.
        """
        self.assert_line("", timeout_ms=timeout_ms, assert_timeout=True)

    def assert_line(self, line, timeout_ms=1000, assert_timeout=False) -> None:
        """
        Waits for the client to output a specific line.
        NB client only reads the first line available.
        """
        poll_obj = select.poll()
        poll_obj.register(self.process.stdout, select.POLLIN)
        poll_result = poll_obj.poll(timeout_ms)
        if poll_result:
            out = self.process.stdout.readline().strip()
            assert out == line
        else:
            if assert_timeout:
                assert True
            else:
                assert False, "No text received."

    def assert_ok(self, command: str) -> None:
        """Verify that the client outputs 'OK' after sending a command."""
        assert self.send(command) == "OK"

    def assert_error(self, command: str, error: str) -> None:
        """Verify that the client outputs an error message."""
        assert self.send(command) == f"ERROR: {error}"

    def send_read_until(self, command, expected, timeout_ms=2000):
        """
        Send command and read stdout until `expected` is seen.

        Returns all lines read (including the matching line).

        Raises TimeoutError if the line is not received before the timeout.
        """
        self._send(command)

        poll_obj = select.poll()
        poll_obj.register(self.process.stdout, select.POLLIN)

        deadline = time.monotonic() + timeout_ms / 1000
        lines = []

        while True:
            remaining = max(0, int((deadline - time.monotonic()) * 1000))

            if remaining == 0:
                assert False, f"Timed out waiting for {expected!r}. Received: {lines!r}"

            if not poll_obj.poll(remaining):
                assert False, f"Timed out waiting for {expected!r}. Received: {lines!r}"

            data = self.process.stdout.read()
            if not data:  # EOF
                raise EOFError(f"Process exited before {expected!r}. Received: {lines!r}")

            raw_lines = [l.strip() for l in data.split("\n") if l]
            lines.extend(raw_lines)

            if expected in lines:
                return lines

    def restart(self):
        self._run()

    def flush_manager(self):
        self.manager.c.core.flush()


@pytest.fixture
def test_client(wmanager, request):
    script = getattr(request, "param", None)

    if script is None:
        raise ValueError("The test_client fixture must be parameterised.")

    with ClientHandler(script, wmanager) as client:
        yield client
