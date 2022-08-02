# Copyright (c) 2021-22 elParaguayo
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
import pytest

import libqtile.bar
import libqtile.config
from libqtile.widget import TextBox
from libqtile.widget.base import ThreadPoolText, _Widget
from test.helpers import BareConfig, Retry


class TimerWidget(_Widget):
    def cmd_set_timer1(self):
        self.timer1 = self.timeout_add(10, self.cmd_set_timer1)

    def cmd_cancel_timer1(self):
        self.timer1.cancel()

    def cmd_set_timer2(self):
        self.timer2 = self.timeout_add(10, self.cmd_set_timer2)

    def cmd_cancel_timer2(self):
        self.timer2.cancel()

    def cmd_get_active_timers(self):
        active = [x for x in self._futures if x._scheduled]
        return len(active)


class PollingWidget(ThreadPoolText):
    poll_count = 0

    def poll(self):
        self.poll_count += 1
        return f"Poll count: {self.poll_count}"


def test_multiple_timers(minimal_conf_noscreen, manager_nospawn):
    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(top=libqtile.bar.Bar([TimerWidget(10)], 10))]

    # Start manager and check no active timers
    manager_nospawn.start(config)
    assert manager_nospawn.c.widget["timerwidget"].get_active_timers() == 0

    # Start both timers and confirm both are active
    manager_nospawn.c.widget["timerwidget"].set_timer1()
    manager_nospawn.c.widget["timerwidget"].set_timer2()
    assert manager_nospawn.c.widget["timerwidget"].get_active_timers() == 2

    # Cancel timer1
    manager_nospawn.c.widget["timerwidget"].cancel_timer1()
    assert manager_nospawn.c.widget["timerwidget"].get_active_timers() == 1

    # Cancel timer2
    manager_nospawn.c.widget["timerwidget"].cancel_timer2()
    assert manager_nospawn.c.widget["timerwidget"].get_active_timers() == 0

    # Restart both timers
    manager_nospawn.c.widget["timerwidget"].set_timer1()
    manager_nospawn.c.widget["timerwidget"].set_timer2()
    assert manager_nospawn.c.widget["timerwidget"].get_active_timers() == 2

    # Verify that `finalize()` cancels all timers.
    manager_nospawn.c.widget["timerwidget"].eval("self.finalize()")
    assert manager_nospawn.c.widget["timerwidget"].get_active_timers() == 0


def test_mirrors_same_bar(minimal_conf_noscreen, manager_nospawn):
    """Verify that mirror created when widget reused in same bar."""
    config = minimal_conf_noscreen
    tbox = TextBox("Testing Mirrors")
    config.screens = [libqtile.config.Screen(top=libqtile.bar.Bar([tbox, tbox], 10))]

    manager_nospawn.start(config)
    info = manager_nospawn.c.bar["top"].info()["widgets"]

    # First instance is retained, second is replaced by mirror
    assert len(info) == 2
    assert [w["name"] for w in info] == ["textbox", "mirror"]


def test_mirrors_different_bar(minimal_conf_noscreen, manager_nospawn):
    """Verify that mirror created when widget reused in different bar."""
    config = minimal_conf_noscreen
    tbox = TextBox("Testing Mirrors")
    config.fake_screens = [
        libqtile.config.Screen(top=libqtile.bar.Bar([tbox], 10), x=0, y=0, width=400, height=600),
        libqtile.config.Screen(
            top=libqtile.bar.Bar([tbox], 10), x=400, y=0, width=400, height=600
        ),
    ]

    manager_nospawn.start(config)
    screen0 = manager_nospawn.c.screen[0].bar["top"].info()["widgets"]
    screen1 = manager_nospawn.c.screen[1].bar["top"].info()["widgets"]

    # Original widget should be in the first screen
    assert len(screen0) == 1
    assert [w["name"] for w in screen0] == ["textbox"]

    # Widget is replaced with a mirror on the second screen
    assert len(screen1) == 1
    assert [w["name"] for w in screen1] == ["mirror"]


def test_threadpolltext_force_update(minimal_conf_noscreen, manager_nospawn):
    """Check that widget can be polled instantly via command interface."""
    config = minimal_conf_noscreen
    tpoll = PollingWidget("Not polled")
    config.screens = [libqtile.config.Screen(top=libqtile.bar.Bar([tpoll], 10))]

    manager_nospawn.start(config)
    widget = manager_nospawn.c.widget["pollingwidget"]

    # Widget is polled immediately when configured
    assert widget.info()["text"] == "Poll count: 1"

    # Default update_imterval is 600 seconds so the widget won't poll during test unless forced
    widget.force_update()
    assert widget.info()["text"] == "Poll count: 2"


class ScrollingTextConfig(BareConfig):
    screens = [
        libqtile.config.Screen(
            top=libqtile.bar.Bar(
                [
                    TextBox("NoWidth", name="no_width", scroll=True),
                    TextBox("ShortText", name="short_text", width=100, scroll=True),
                    TextBox("Longer text " * 5, name="longer_text", width=100, scroll=True),
                ],
                32,
            )
        )
    ]


scrolling_text_config = pytest.mark.parametrize("manager", [ScrollingTextConfig], indirect=True)


@scrolling_text_config
def test_text_scroll_no_width(logger, manager):
    """
    Scrolling text needs a fixed width. If this is not set a warning is provided and
    scrolling is disabled.
    """
    records = [r for r in logger.get_records("setup") if r.msg.startswith("no_width")]
    assert records
    assert records[0].levelname == "WARNING"
    assert records[0].msg == "no_width: You must specify a width when enabling scrolling."
    _, output = manager.c.widget["no_width"].eval("self.scroll")
    assert output == "False"


@scrolling_text_config
def test_text_scroll_short_text(manager):
    """
    When scrolling is enabled, width is a "max_width" setting.
    Shorter text will reslult in widget shrinking.
    """
    widget = manager.c.widget["short_text"]

    # Width is shorter than max width
    assert widget.info()["width"] < 100

    # Scrolling is still enabled (but won't do anything)
    _, output = widget.eval("self.scroll")
    assert output == "True"

    _, output = widget.eval("self._should_scroll")
    assert output == "False"


@scrolling_text_config
def test_text_scroll_long_text(manager):
    """
    Longer text scrolls by incrementing an offset counter.
    """

    @Retry(ignore_exceptions=(AssertionError,))
    def wait_for_scroll(widget):
        _, scroll_count = widget.eval("self._scroll_offset")
        assert int(scroll_count) > 5

    widget = manager.c.widget["longer_text"]

    # Width is fixed at set width
    assert widget.info()["width"] == 100

    # Scrolling is still enabled
    _, output = widget.eval("self.scroll")
    assert output == "True"

    _, output = widget.eval("self._should_scroll")
    assert output == "True"

    # Check actually scrolling
    wait_for_scroll(widget)
