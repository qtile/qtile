import pytest

import libqtile.bar
import libqtile.config
from libqtile import widget


def get_cursor_markup(cursor_type, selected_char):
    """Get the supposedly generated markup for the different cursors."""

    if cursor_type == "line":
        return f'<u><span foreground="#ff0000">{selected_char}</span></u>'
    if cursor_type == "block":
        return f'<span background="#ff0000" foreground="#00000000">{selected_char}</span>'
    if cursor_type == "bar":
        return f'<span foreground="#ff0000">▏</span>{selected_char}'
    if cursor_type == "none":
        return f'<span foreground="#ff0000">{selected_char}</span>'
    return None


def test_prompt_focus(manager_nospawn, minimal_conf_noscreen):
    """Test if focusing the prompt works properly."""

    prompt_widget = widget.Prompt()

    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(
        top=libqtile.bar.Bar([prompt_widget], 10))]

    manager_nospawn.start(config)
    pwidget = manager_nospawn.c.widget["prompt"]

    # Test if the unfocused default state is reasonable.
    unfocus_info = pwidget.info()
    assert unfocus_info["text"] == ""
    assert unfocus_info["width"] == 0
    assert unfocus_info["active"] == False

    # Start the input to the widget.
    pwidget.eval('self.start_input("test", lambda _: True)')

    # Test if the widget is visible and active.
    focus_info = pwidget.info()
    assert focus_info["width"] != 0
    assert focus_info["active"] == True


@pytest.mark.parametrize("cursor_type", ["line", "block", "bar", "none"])
def test_prompt_input(manager_nospawn, minimal_conf_noscreen, cursor_type):
    """Test if input is working correctly."""

    prompt_widget = widget.Prompt(
        cursor_color="#ff0000",
        cursor_type=cursor_type,
        cursorblink=False
    )

    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(
        top=libqtile.bar.Bar([prompt_widget], 10))]

    manager_nospawn.start(config)
    pwidget = manager_nospawn.c.widget["prompt"]

    # Start the input to the widget and add some text.
    pwidget.eval('self.start_input("test", lambda _: True)')
    pwidget.fake_keypress("a")
    pwidget.fake_keypress("b")
    pwidget.fake_keypress("c")

    input_info = pwidget.info()
    assert input_info["text"] == f'test: abc{get_cursor_markup(cursor_type, " ")}'

    # Move the cursor and add a new character.
    pwidget.fake_keypress("Left")
    pwidget.fake_keypress("Left")
    pwidget.fake_keypress("x")

    move_info = pwidget.info()
    assert move_info["text"] == f'test: ax{get_cursor_markup(cursor_type, "b")}c'


@pytest.mark.parametrize("cursor_type", ["line", "block", "bar", "none"])
def test_prompt_text_escape(manager_nospawn, minimal_conf_noscreen, cursor_type):
    """Test if special charters are escaped properly."""

    prompt_widget = widget.Prompt(
        cursor_color="#ff0000",
        cursor_type=cursor_type,
        cursorblink=False
    )

    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(
        top=libqtile.bar.Bar([prompt_widget], 10))]

    manager_nospawn.start(config)
    pwidget = manager_nospawn.c.widget["prompt"]

    # Start the input to the widget, input some text, and move the cursor.
    pwidget.eval('self.start_input("test", lambda _: True)')
    pwidget.fake_keypress("a")
    pwidget.fake_keypress("b")
    pwidget.fake_keypress("c")
    pwidget.fake_keypress("Left")
    pwidget.fake_keypress("Left")

    # Add a "<" character. This should become "&lt;" in the sanitised output.
    pwidget.fake_keypress("less")

    special_info = pwidget.info()
    assert special_info["text"] == f'test: a&lt;{get_cursor_markup(cursor_type, "b")}c'

    # Move the cursor on top of the special character.
    pwidget.fake_keypress("Left")

    special_move_info = pwidget.info()
    assert special_move_info["text"] == f'test: a{get_cursor_markup(cursor_type, "&lt;")}bc'
