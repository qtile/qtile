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
