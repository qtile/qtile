# Copyright (c) 2025 Emma Nora Theuer
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

# Widget specific tests

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
