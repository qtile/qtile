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
import textwrap

import pytest

import libqtile.config
import libqtile.widget.bluetooth
from libqtile.bar import Bar
from libqtile.config import Screen
from test.helpers import Retry


@Retry(ignore_exceptions=(AssertionError,))
def clipboard_cleared(widget):
    assert widget.info()["text"] == ""


@pytest.fixture
def clipboard_manager(request, minimal_conf_noscreen, manager_nospawn):
    widget = libqtile.widget.Clipboard(**getattr(request, "param", dict()))
    config = minimal_conf_noscreen
    config.screens = [Screen(top=Bar([widget], 10))]
    manager_nospawn.start(config)

    if manager_nospawn.backend.name != "x11":
        pytest.skip("Test only available on X11.")

    yield manager_nospawn


def test_clipboard_display(clipboard_manager):
    widget = clipboard_manager.c.widget["clipboard"]
    assert widget.info()["text"] == ""

    fake_hook = textwrap.dedent(
        """
        from libqtile import hook

        sel = {"owner": 12345, "selection": "Test Clipboard"}

        hook.fire("selection_change", "CLIPBOARD", sel)
        hook.fire("selection_notify", "CLIPBOARD", sel)
    """
    )

    clipboard_manager.c.eval(fake_hook)

    # Default setting is to limit display to 10 chars
    assert widget.info()["text"] == "Test Clipb..."


@pytest.mark.parametrize(
    "clipboard_manager", [{"max_width": None, "blacklist": []}], indirect=True
)
def test_clipboard_display_full_text(clipboard_manager):
    widget = clipboard_manager.c.widget["clipboard"]
    assert widget.info()["text"] == ""

    fake_hook = textwrap.dedent(
        """
        from libqtile import hook

        sel = {"owner": 12345, "selection": "Test Clipboard"}

        hook.fire("selection_change", "CLIPBOARD", sel)
        hook.fire("selection_notify", "CLIPBOARD", sel)
    """
    )

    clipboard_manager.c.eval(fake_hook)

    # Widget should now show full text
    assert widget.info()["text"] == "Test Clipboard"


@pytest.mark.parametrize("clipboard_manager", [{"blacklist": ["TestWindow"]}], indirect=True)
def test_clipboard_blacklist(clipboard_manager):
    """Test widget hides selection from blacklisted windows."""
    widget = clipboard_manager.c.widget["clipboard"]
    assert widget.info()["text"] == ""

    clipboard_manager.test_window("Blacklisted Window")
    windows = clipboard_manager.c.windows()
    window_id = [w for w in windows if w["name"] == "Blacklisted Window"][0]["id"]

    fake_hook = textwrap.dedent(
        f"""
        from libqtile import hook

        sel = {{"owner": {window_id}, "selection": "Test Clipboard"}}

        hook.fire("selection_change", "CLIPBOARD", sel)
        hook.fire("selection_notify", "CLIPBOARD", sel)
    """
    )

    clipboard_manager.c.eval(fake_hook)

    # Widget should now show full text
    assert widget.info()["text"] == "***********"


def test_clipboard_ignore_different_selection(clipboard_manager):
    widget = clipboard_manager.c.widget["clipboard"]
    assert widget.info()["text"] == ""

    fake_hook = textwrap.dedent(
        """
        from libqtile import hook

        sel = {"owner": 12345, "selection": "Test Clipboard"}

        hook.fire("selection_change", "PRIMARY", sel)
        hook.fire("selection_notify", "PRIMARY", sel)
    """
    )

    clipboard_manager.c.eval(fake_hook)

    assert widget.info()["text"] == ""


@pytest.mark.parametrize("clipboard_manager", [{"timeout": 0.5}], indirect=True)
def test_clipboard_display_clear(clipboard_manager):
    widget = clipboard_manager.c.widget["clipboard"]
    assert widget.info()["text"] == ""

    fake_hook = textwrap.dedent(
        """
        from libqtile import hook

        sel = {"owner": 12345, "selection": "Test Clipboard"}

        hook.fire("selection_change", "CLIPBOARD", sel)
        hook.fire("selection_notify", "CLIPBOARD", sel)
    """
    )

    clipboard_manager.c.eval(fake_hook)

    # Default setting is to limit display to 10 chars
    assert widget.info()["text"] == "Test Clipb..."

    # Check cleared after timeout
    clipboard_cleared(widget)


def test_clipboard_display_multiple_changes(clipboard_manager):
    """Just need this test to cover last lines in hook_change."""
    widget = clipboard_manager.c.widget["clipboard"]
    assert widget.info()["text"] == ""

    fake_hook = textwrap.dedent(
        """
        from libqtile import hook

        sel = {"owner": 12345, "selection": "Test Clipboard"}
        sel_b = {"owner": 12345, "selection": "Second Selection"}

        hook.fire("selection_change", "CLIPBOARD", sel)
        hook.fire("selection_change", "CLIPBOARD", sel_b)
    """
    )

    clipboard_manager.c.eval(fake_hook)

    # Default setting is to limit display to 10 chars
    assert widget.info()["text"] == "Second Sel..."
