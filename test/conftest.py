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

import pytest

from libqtile.backend import base
from test.backend.wayland.conftest import WaylandBackend, wayland_environment
from test.backend.x11.conftest import XBackend, x11_environment
from test.helpers import BareConfig, TestManager


def pytest_addoption(parser):
    parser.addoption(
        "--debuglog", action="store_true", default=False, help="enable debug output"
    )
    parser.addoption(
        "--backend",
        action="append",
        default=[],
        help="Specify a backend to test. Can be passed more than once.",
    )


def pytest_generate_tests(metafunc):
    if "backend" in metafunc.fixturenames:
        backends = metafunc.config.getoption("backend") or ["x11"]
        metafunc.parametrize("backend_name", backends)


@pytest.fixture(scope="session", params=[1])
def outputs(request):
    return request.param


dualmonitor = pytest.mark.parametrize("outputs", [2], indirect=True)
multimonitor = pytest.mark.parametrize("outputs", [1, 2], indirect=True)


@pytest.fixture(scope="session")
def xephyr(request, outputs):  # noqa: F841
    kwargs = getattr(request, "param", {})

    with x11_environment(outputs, **kwargs) as x:
        yield x


@pytest.fixture(scope="session")
def wayland_session(outputs):  # noqa: F841
    with wayland_environment(outputs) as w:
        yield w


@pytest.fixture(scope="function")
def backend(request, backend_name, xephyr, wayland_session):
    if backend_name == "x11":
        b = XBackend({"DISPLAY": xephyr.display}, args=[xephyr.display])
    elif backend_name == "wayland":
        b = WaylandBackend(wayland_session)

    yield b


@pytest.fixture(scope="function")
def manager_nospawn(request, backend):
    with TestManager(backend, request.config.getoption("--debuglog")) as manager:
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
