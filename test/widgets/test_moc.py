# Copyright (c) 2021 elParaguayo
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
from unittest.mock import MagicMock

from libqtile.widget import moc

# Sample output from `mocp -i`
PLAYING = """State: PLAY
File: /playing/file/rickroll.mp3
SongTitle: Never Gonna Give You Up
Artist: Rick Astley
Album: Whenever You Need Somebody
"""

PAUSED = """State: PAUSE
File: /playing/file/rickroll.mp3
SongTitle: Never Gonna Give You Up
Artist: Rick Astley
Album: Whenever You Need Somebody
"""

STOPPED = "State: STOP"

TITLE_ONLY = """State: PLAY
File: /playing/file/sweetcaroline.mp3
SongTitle: Sweet Caroline
Artist:
Album: Greatest Hits
"""

FILENAME_ONLY = """State: PLAY
File: /playing/file/always.mp3
SongTitle:
Artist:
Album:
"""

ERROR = "Couldn't connect to moc."


def test_moc_parsing():
    widget = moc.Moc()
    widget.layout = MagicMock()

    # Test playing status and format
    text = widget.parse(PLAYING)
    assert text == "♫ Rick Astley - Never Gonna Give You Up"
    assert widget.layout.colour == widget.play_color

    # Test paused status and format
    text = widget.parse(PAUSED)
    assert text == "♫ Rick Astley - Never Gonna Give You Up"
    assert widget.layout.colour == widget.noplay_color

    # Test stopped status and format
    text = widget.parse(STOPPED)
    assert text == "♫"
    assert widget.layout.colour == widget.noplay_color

    # Test title only
    widget.status = "STOP"  # Reset status
    text = widget.parse(TITLE_ONLY)
    assert text == "♫ Sweet Caroline"
    assert widget.layout.colour == widget.play_color

    # Test filename only
    widget.status = "STOP"  # Reset status
    text = widget.parse(FILENAME_ONLY)
    assert text == "♫ always"
    assert widget.layout.colour == widget.play_color

    # Test error
    widget.status = "PLAY"
    text = widget.parse(ERROR)
    assert text == ""
    # Status should not change on error
    assert widget.layout.colour == widget.play_color
