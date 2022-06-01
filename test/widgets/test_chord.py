from libqtile import hook
from libqtile.widget import Chord, base
from test.widgets.conftest import FakeBar

RED = "#FF0000"
BLUE = "#00FF00"

textbox = base._TextBox("")
BASE_BACKGROUND = textbox.background
BASE_FOREGROUND = textbox.foreground


def test_chord_widget(fake_window, fake_qtile):
    chord = Chord(chords_colors={"testcolor": (RED, BLUE)})
    fakebar = FakeBar([chord], window=fake_window)
    chord._configure(fake_qtile, fakebar)

    # Text is blank at start
    assert chord.text == ""

    # Fire hook for testcolor chord
    hook.fire("enter_chord", "testcolor")

    # Chord is in chords_colors so check colours
    assert chord.background == RED
    assert chord.foreground == BLUE
    assert chord.text == "testcolor"

    # New chord, not in dictionary so should be default colours
    hook.fire("enter_chord", "test")
    assert chord.text == "test"
    assert chord.background == BASE_BACKGROUND
    assert chord.foreground == BASE_FOREGROUND

    # Unnamed chord so no text
    hook.fire("enter_chord", True)
    assert chord.text == ""
    assert chord.background == BASE_BACKGROUND
    assert chord.foreground == BASE_FOREGROUND

    # Back into testcolor and custom colours
    hook.fire("enter_chord", "testcolor")
    assert chord.background == RED
    assert chord.foreground == BLUE
    assert chord.text == "testcolor"

    # Colours shoud reset when leaving chord
    hook.fire("leave_chord")
    assert chord.text == ""
    assert chord.background == BASE_BACKGROUND
    assert chord.foreground == BASE_FOREGROUND

    # Finalize the widget to prevent segfault
    chord.finalize()
