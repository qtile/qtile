from __future__ import annotations

from unittest.mock import MagicMock, patch


def test_add_window_inhibitor_unknown_type_logs_variable_value():
    """logger.error must interpolate the inhibitor_type variable, not print it literally.

    The bug was a missing f-prefix: logger.error("... {inhibitor_type}.")
    which prints the literal string instead of the variable value.
    """
    from libqtile.backend.base.idle_inhibit import IdleInhibitorManager

    core = MagicMock()
    manager = IdleInhibitorManager(core)
    window = MagicMock()

    with patch("libqtile.backend.base.idle_inhibit.logger") as mock_logger:
        manager.add_window_inhibitor(window, "bogus_type_xyz")
        mock_logger.error.assert_called_once()
        logged_msg = mock_logger.error.call_args[0][0]
        assert "bogus_type_xyz" in logged_msg, (
            f"logger.error message should contain the actual type name, got: {logged_msg!r}"
        )
        assert "{inhibitor_type}" not in logged_msg, (
            "logger.error is printing the literal placeholder instead of the variable value"
        )
