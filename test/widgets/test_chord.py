from libqtile import hook
from libqtile.widget import Chord


def test_chord_widget(fake_bar):
    chord = Chord()
    chord.bar = fake_bar
    chord._setup_hooks()
    assert chord.text == ""
    hook.fire("enter_chord", "test")
    assert chord.text == "test"
    hook.fire("enter_chord", True)
    assert chord.text == ""
    hook.fire("leave_chord")
    assert chord.text == ""
