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

import pytest

from libqtile.widget import cmus

# Sample output from `cmus-remote -C status`
PLAYING = """status playing
file /playing/file/rickroll.mp3
duration 222
position 14
tag artist Rick Astley
tag album Whenever You Need Somebody
tag title Never Gonna Give You Up
"""

PAUSED = """status paused
file /playing/file/rickroll.mp3
duration 222
position 14
tag artist Rick Astley
tag album Whenever You Need Somebody
tag title Never Gonna Give You Up
"""

STOPPED = "status stopped"

STREAMING = """status playing
file http://playing/file/sweetcaroline.mp3
duration -1
position -9
tag artist Neil Diamond
tag album Greatest Hits
tag title Sweet Caroline
"""

STREAM_TITLE_ONLY = """status stopped
file http://streaming.source/tomjones.m3u
duration -1
position -9
tag title It's Not Unusual
stream tomjones
"""

NEEDS_ESCAPING = """status playing
file /playing/file/always.mp3
duration 222
position 14
tag artist Above & Beyond
tag album Anjunabeats 14
tag title Always - Tinlicker Extended Mix
"""

MISSING_TAGS = """status playing
file /playing/file/always.mp3
duration 222
position 14
"""

ERROR = "cmus-remote: cmus is not running"


def test_cmus_parsing():
    widget = cmus.Cmus()
    widget.layout = MagicMock()

    # Test playing status and format
    text = widget.parse(PLAYING)
    assert text == "♫ Rick Astley - Never Gonna Give You Up"
    assert widget.layout.colour == widget.playing_color

    # Test paused status and format
    text = widget.parse(PAUSED)
    assert text == "♫ Rick Astley - Never Gonna Give You Up"
    assert widget.layout.colour == widget.paused_color

    # Test stopped status and format
    text = widget.parse(STOPPED)
    assert text == ""
    assert widget.layout.colour == widget.stopped_color

    # Test streaming format
    widget.status = "stopped"  # Reset status
    text = widget.parse(STREAMING)
    assert text == "♫ Neil Diamond - Sweet Caroline"
    assert widget.layout.colour == widget.playing_color

    # Test stream with title only
    widget.status = "playing"
    text = widget.parse(STREAM_TITLE_ONLY)
    assert text == "♫ tomjones"
    assert widget.layout.colour == widget.stopped_color

    # Test escaping of text
    widget.status = "stopped"
    text = widget.parse(NEEDS_ESCAPING)
    assert text == "♫ Above &amp; Beyond - Always - Tinlicker Extended Mix"
    assert widget.layout.colour == widget.playing_color

    # Test missing tags
    widget.status = "stopped"
    text = widget.parse(MISSING_TAGS)
    assert text == "♫ always.mp3"
    assert widget.layout.colour == widget.playing_color

    # Test error
    widget.status = "playing"
    text = widget.parse(ERROR)
    assert text == ""
    # Status should not change on error
    assert widget.layout.colour == widget.playing_color


def test_cmus_time_format():
    widget = cmus.Cmus(
        format="{position} {duration} {position_percent} {remaining} {remaining_percent}"
    )
    widget.layout = MagicMock()

    text = widget.parse(PLAYING)
    assert text == "00:14 03:42 6% 03:28 94%"

    # Times should be empty for streams
    text = widget.parse(STREAMING)
    assert text.strip() == ""


def test_cmus_no_artist_format():
    widget = cmus.Cmus(no_artist_format="{status_text}{title} by {artist}")
    widget.layout = MagicMock()
    text = widget.parse(MISSING_TAGS)
    assert text == "♫ always.mp3 by "


@pytest.mark.parametrize(
    "status,text",
    [
        ("playing", "PLAY "),
        ("paused", "PAUSE "),
        ("stopped", "STOP "),
    ],
)
def test_cmus_status_text(status, text):
    widget = cmus.Cmus(
        playing_text="PLAY ",
        paused_text="PAUSE ",
        stopped_text="STOP ",
        format="{status_text}{artist} - {title}",
    )
    widget.layout = MagicMock()
    output = PLAYING.replace("status playing", f"status {status}")
    parsed = widget.parse(output)
    assert parsed.startswith(text)
