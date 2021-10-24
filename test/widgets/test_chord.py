from libqtile import hook
from libqtile.widget import Chord, base

RED = "#FF0000"
BLUE = "#00FF00"

textbox = base._TextBox("")
BASE_BACKGROUND = textbox.background
BASE_FOREGROUND = textbox.foreground


def test_chord_widget(fake_bar):
    chord = Chord(chords_colors={"testcolor": (RED, BLUE)})
    chord.bar = fake_bar
    chord._setup_hooks()
    assert chord.text == ""
    hook.fire("enter_chord", "test")
    assert chord.text == "test"
    assert chord.background == BASE_BACKGROUND
    assert chord.foreground == BASE_FOREGROUND
    hook.fire("enter_chord", True)
    assert chord.text == ""
    hook.fire("leave_chord")
    assert chord.text == ""
    hook.fire("enter_chord", "testcolor")
    assert chord.background == RED
    assert chord.foreground == BLUE
