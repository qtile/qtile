import pytest

from libqtile.widget import Chord


@pytest.fixture
def widget():
    yield Chord


@pytest.mark.parametrize(
    "screenshot_manager",
    [{}, {"chords_colors": {"vim mode": ("2980b9", "ffffff")}}],
    indirect=True,
)
def ss_chord(screenshot_manager):
    screenshot_manager.c.eval("hook.fire('enter_chord', 'vim mode')")
    screenshot_manager.take_screenshot()
