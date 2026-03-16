import sys

import pytest

try:
    from libqtile.backend.macos.core import Core

    has_macos = sys.platform == "darwin"
except ImportError:
    has_macos = False

from test.helpers import Backend, BareConfig, TestManager


class MacOSBackend(Backend):
    name = "macos"

    def __init__(self, env=None, args=()):
        super().__init__(env or {}, args)
        self.core = Core

    def create(self):
        return self.core(*self.args)

    def configure(self, manager):
        pass

    def fake_click(self, x, y):
        """Click at the specified coordinates"""

    def get_all_windows(self):
        """Get a list of all windows in ascending order of Z position"""
        return list(self.manager.c.core.windows.keys())

    def test_window(self, name):
        from pathlib import Path

        path = Path(__file__).parent.parent.parent / "scripts" / "macos_window"
        return self.manager._spawn_window(str(path), name)


@pytest.fixture(scope="function")
def mmanager(request):
    """
    This replicates the `manager` fixture except that the macOS backend is hard-coded.
    """
    if not has_macos:
        pytest.skip("macOS backend not available")

    config = getattr(request, "param", BareConfig)
    backend = MacOSBackend()

    with TestManager(backend, request.config.getoption("--debuglog")) as manager:
        manager.start(config)
        yield manager
