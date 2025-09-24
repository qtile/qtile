from unittest.mock import MagicMock, patch

from libqtile.widget.tuned_manager import TunedManager


def test_find_mode():
    # Mocking subprocess.run to return a specific output
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = "Current active profile: balanced-battery\n"

        widget = TunedManager()
        mode = widget.find_mode()

        assert mode == "balanced-battery"
        assert mock_run.call_count == 2  # Called during init and explicitly


def test_update_bar():
    with (
        patch("subprocess.run") as mock_run,
        patch.object(TunedManager, "bar", create=True) as mock_bar,
    ):
        mock_run.return_value.stdout = "Current active profile: powersave\n"
        mock_bar.draw = MagicMock()

        widget = TunedManager()
        widget.update_bar()

        assert widget.current_mode == "powersave"
        assert widget.text == "powersave"
        mock_bar.draw.assert_called_once()


def test_next_mode():
    with patch.object(TunedManager, "execute_command") as mock_execute_command:
        widget = TunedManager()
        widget.modes = ["powersave", "balanced-battery", "throughput-performance"]
        widget.current_mode = "powersave"

        widget.next_mode()

        mock_execute_command.assert_called_once_with(1)


def test_previous_mode():
    with patch.object(TunedManager, "execute_command") as mock_execute_command:
        widget = TunedManager()
        widget.modes = ["powersave", "balanced-battery", "throughput-performance"]
        widget.current_mode = "balanced-battery"

        widget.previous_mode()

        mock_execute_command.assert_called_once_with(0)
