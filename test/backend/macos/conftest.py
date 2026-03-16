from __future__ import annotations

import os
import sys

import pytest

from test.helpers import Backend, TestManager

if sys.platform != "darwin" and not any(arg.startswith("test_unit_") for arg in sys.argv):
    pytest.skip("macOS tests (only unit tests run on Linux)", allow_module_level=True)


class MacosBackend(Backend):
    def __init__(self, env, args=()):
        super().__init__(env, args)
        if "DISPLAY" in self.env:
            del self.env["DISPLAY"]

    @property
    def core(self):
        from libqtile.backend.macos.core import Core

        return Core

    def get_all_windows(self):
        # Requires Accessibility permissions (AX trust) — returns empty list without them.
        from libqtile.backend.macos.core import Core

        c = Core()
        return [w.wid for w in c.list_windows()]

    def fake_click(self, x, y):
        from libqtile.backend.macos.core import Core

        c = Core()
        c.warp_pointer(x, y)
        # Full implementation requires `CGEventCreateMouseEvent` + `CGEventPost` which needs
        # macOS. Pointer warp only for now.


@pytest.fixture(scope="function")
def manager(backend, request):
    with TestManager(
        backend, request.node.get_closest_marker("debug_log") is not None
    ) as manager:
        yield manager


@pytest.fixture(scope="session")
def backend(request):
    return MacosBackend(os.environ.copy())


@pytest.fixture
def fake_window(manager):
    from libqtile.backend.macos.window import Window

    class FakeWindow(Window):
        def __init__(self, qtile, win_struct_ptr):
            super().__init__(qtile, win_struct_ptr)

    return FakeWindow
