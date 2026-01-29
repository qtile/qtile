# Copyright (c) 2024 Qtile
#
# Licensed under the MIT License.
# See the LICENSE file in the root of this repository for details.

from unittest.mock import Mock

import pytest

try:
    from libqtile.backend.wayland.keyboard_shortcuts_inhibit import KeyboardShortcutsInhibitorManager
    has_wayland = True
except ImportError:
    has_wayland = False


@pytest.mark.skipif(not has_wayland, reason="Wayland backend not available")
class TestKeyboardShortcutsInhibitorManager:
    @pytest.fixture
    def manager(self):
        core = Mock()
        return KeyboardShortcutsInhibitorManager(core)

    @pytest.fixture
    def mock_inhibitor_handle(self):
        return Mock()

    @pytest.fixture
    def mock_surface(self):
        return Mock()

    def test_add_inhibitor(self, manager, mock_inhibitor_handle, mock_surface):
        assert not manager.has_active_inhibitors

        # Add first inhibitor
        assert manager.add_inhibitor(mock_inhibitor_handle, mock_surface) is True
        assert manager.has_active_inhibitors
        assert len(manager.inhibitors) == 1
        assert manager.inhibitors[0].handle == mock_inhibitor_handle
        assert manager.inhibitors[0].surface == mock_surface

        # Add duplicate inhibitor (should return False)
        assert manager.add_inhibitor(mock_inhibitor_handle, mock_surface) is False
        assert len(manager.inhibitors) == 1

        # Add second, distinct inhibitor
        second_handle = Mock()
        second_surface = Mock()
        assert manager.add_inhibitor(second_handle, second_surface) is True
        assert len(manager.inhibitors) == 2

    def test_remove_inhibitor(self, manager, mock_inhibitor_handle, mock_surface):
        # Setup
        manager.add_inhibitor(mock_inhibitor_handle, mock_surface)
        assert manager.has_active_inhibitors

        # Remove existing inhibitor
        assert manager.remove_inhibitor(mock_inhibitor_handle) is True
        assert not manager.has_active_inhibitors
        assert len(manager.inhibitors) == 0

        # Remove non-existent inhibitor
        assert manager.remove_inhibitor(mock_inhibitor_handle) is False

    def test_inhibitor_equality(self, manager, mock_inhibitor_handle, mock_surface):
        # We need to test the equality on the Inhibitor object itself implicitly via add_inhibitor
        # logic, but let's test the wrapper class directly too
        from libqtile.backend.wayland.keyboard_shortcuts_inhibit import KeyboardShortcutsInhibitor

        i1 = KeyboardShortcutsInhibitor(mock_inhibitor_handle, mock_surface)
        i2 = KeyboardShortcutsInhibitor(mock_inhibitor_handle, mock_surface)
        i3 = KeyboardShortcutsInhibitor(Mock(), mock_surface)

        assert i1 == i2
        assert i1 != i3
        assert i1 != "not an inhibitor"
