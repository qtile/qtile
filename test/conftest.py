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
import logging
import multiprocessing

import pytest

from libqtile.backend import base
from test.helpers import BareConfig, TestManager


def pytest_addoption(parser):
    parser.addoption("--debuglog", action="store_true", default=False, help="enable debug output")
    parser.addoption(
        "--backend",
        action="append",
        choices=("x11", "wayland"),
        help="Test a specific backend. Can be passed more than once.",
    )


def pytest_cmdline_main(config):
    if not config.option.backend:
        config.option.backend = ["x11"]

    ignore = config.option.ignore or []
    if "wayland" not in config.option.backend:
        ignore.append("test/backend/wayland")
    if "x11" not in config.option.backend:
        ignore.append("test/backend/x11")
    config.option.ignore = ignore


def pytest_generate_tests(metafunc):
    if "backend" in metafunc.fixturenames:
        backends = metafunc.config.option.backend
        metafunc.parametrize("backend_name", backends)


@pytest.fixture(scope="session", params=[1])
def outputs(request):
    return request.param


dualmonitor = pytest.mark.parametrize("outputs", [2], indirect=True)
multimonitor = pytest.mark.parametrize("outputs", [1, 2], indirect=True)


@pytest.fixture(scope="session")
def xephyr(request, outputs):
    if "x11" not in request.config.option.backend:
        yield
        return

    from test.backend.x11.conftest import x11_environment

    kwargs = getattr(request, "param", {})

    with x11_environment(outputs, **kwargs) as x:
        yield x


@pytest.fixture(scope="session")
def wayland_session(request, outputs):
    if "wayland" not in request.config.option.backend:
        yield
        return

    from test.backend.wayland.conftest import wayland_environment

    with wayland_environment(outputs) as w:
        yield w


@pytest.fixture(scope="function")
def backend(request, backend_name, xephyr, wayland_session):
    if backend_name == "x11":
        from test.backend.x11.conftest import XBackend

        yield XBackend({"DISPLAY": xephyr.display}, args=[xephyr.display])
    elif backend_name == "wayland":
        from test.backend.wayland.conftest import WaylandBackend

        yield WaylandBackend(wayland_session)


@pytest.fixture(scope="function")
def log_queue():
    """Creates a new Queue for logging messages run in a backend process."""
    yield multiprocessing.Queue(-1)


@pytest.fixture(scope="function")
def logger(caplog, log_queue):
    """
    Connects logging messages in the backend to a logger in the main thread
    and returns a caplog fixture  which can access those messages.
    """
    root = logging.getLogger()
    listener = logging.handlers.QueueListener(log_queue, *root.handlers)
    listener.start()

    yield caplog

    listener.stop()


@pytest.fixture(scope="function")
def manager_nospawn(request, backend, log_queue):
    with TestManager(backend, request.config.getoption("--debuglog")) as manager:
        manager.log_queue = log_queue
        yield manager


@pytest.fixture(scope="function")
def manager(request, manager_nospawn):
    config = getattr(request, "param", BareConfig)

    manager_nospawn.start(config)
    yield manager_nospawn


@pytest.fixture(scope="function")
def fake_window():
    """
    A fake window that can provide a fake drawer to test widgets.
    """

    class FakeWindow:
        class _NestedWindow:
            wid = 10

        window = _NestedWindow()

        def create_drawer(self, width, height):
            return base.Drawer(None, self, width, height)

    return FakeWindow()
