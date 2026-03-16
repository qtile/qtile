from __future__ import annotations

from test.helpers import BareConfig


class MacosTestConfig(BareConfig):
    pass


# def test_macos_window_mapping(manager):
#     manager.start(MacosTestConfig)
#     assert manager.c.windows() == []
#     path = manager.backend.get_all_windows()[0]
#     manager.test_window("one")
#     assert manager.c.windows()[0]["name"] == "one"
#     manager.kill_window(path)
#     assert manager.c.windows() == []
