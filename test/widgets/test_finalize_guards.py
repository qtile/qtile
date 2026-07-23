"""
Regression tests for https://github.com/qtile/qtile/issues/5960

During reload_config/restart, Qtile._finalize_configurables() finalizes all
widgets before the bars. Bar draws that were queued on the event loop before
finalization then run against dead widgets (drawer.ctx and layout are None)
and spam the log with "error when calculating widget ... length" and
"Widget failed to draw" tracebacks.
"""

from libqtile.bar import Bar
from libqtile.widget import TextBox
from test.widgets.conftest import FakeBar


class UnguardedTextBox(TextBox):
    """Mimics widgets such as GroupBox that use self.layout in draw() without
    a can_draw() check."""

    def draw(self):
        self.layout.text = self.text
        self.drawer.draw(offsetx=self.offsetx, width=self.width)


class DrawingFakeBar(FakeBar):
    """FakeBar but with the real Bar.draw so the queueing logic is tested."""

    draw = Bar.draw


class FakeHandle:
    def cancel(self):
        pass


class FakeEventLoopQtile:
    """Runs coroutines passed to call_soon (as the fake_qtile fixture does),
    returns a cancellable handle (so widget/bar finalize() works) and records
    the queued callbacks so tests can inspect them."""

    def __init__(self):
        self.queued = []
        self.register_widget = lambda *args: None

    def call_soon(self, func, *args):
        import asyncio

        coroutines = [arg for arg in args if asyncio.iscoroutine(arg)]
        if coroutines:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            for coro in coroutines:
                loop.run_until_complete(coro)
            loop.close()
        else:
            self.queued.append((func, args))
        return FakeHandle()


def configure_widget(widget, fake_window, bar_class=FakeBar):
    fakebar = bar_class([widget], window=fake_window)
    fakebar.length = 100
    fakebar.qtile = FakeEventLoopQtile()
    widget._configure(fakebar.qtile, fakebar)
    widget.configured = True
    return fakebar


def test_finalized_widget_length_is_zero(fake_window, caplog):
    """A finalized widget reports zero length instead of logging an error."""
    tbox = TextBox("test")
    configure_widget(tbox, fake_window)

    assert tbox.length > 0

    tbox.finalize()

    assert tbox.length == 0
    assert "error when calculating widget" not in caplog.text


def test_reconfigured_widget_length_is_restored(fake_window):
    """Re-configuring a finalized widget (e.g. screen re-added) restores its length."""
    tbox = TextBox("test")
    fakebar = configure_widget(tbox, fake_window)

    tbox.finalize()
    assert tbox.length == 0

    tbox._configure(fakebar.qtile, fakebar)
    assert tbox.length > 0


def test_bar_actual_draw_skips_finalized_widgets(fake_window, caplog):
    """Bar._actual_draw() during the widgets-finalized-before-bar window.

    Qtile._finalize_configurables() finalizes widgets before bars, so a
    queued _actual_draw can run while the bar is alive but its widgets are
    dead. It must not touch them.
    """
    tbox = UnguardedTextBox("test")
    fakebar = configure_widget(tbox, fake_window)
    fakebar.drawer = fake_window.create_drawer(fakebar.width, fakebar.height)

    # Sanity check: drawing works while the widget is alive
    fakebar._actual_draw()
    assert "Widget failed to draw" not in caplog.text

    tbox.finalize()

    fakebar._actual_draw()
    assert "Widget failed to draw" not in caplog.text
    assert "error when calculating widget" not in caplog.text


def test_bar_draw_after_finalize_is_noop(fake_window):
    """Bar.draw() must not queue a draw once the bar is finalized."""
    tbox = TextBox("test")
    fakebar = configure_widget(tbox, fake_window, bar_class=DrawingFakeBar)
    fakebar.drawer = fake_window.create_drawer(fakebar.width, fakebar.height)
    # _configure queued the widget's timer_setup; not relevant here
    fakebar.qtile.queued.clear()

    # Sanity check: draw() queues _actual_draw while the bar is alive
    fakebar.draw()
    assert len(fakebar.qtile.queued) == 1
    fakebar._draw_queued = False
    fakebar.qtile.queued.clear()

    # FakeWindow has no kill() and the bar never created a real window
    fakebar.window = None
    fakebar.finalize()

    fakebar.draw()
    assert fakebar.qtile.queued == []


def test_bar_actual_draw_after_finalize_is_noop(fake_window):
    """A queued Bar._actual_draw() must be a no-op after the bar is finalized."""
    tbox = TextBox("test")
    fakebar = configure_widget(tbox, fake_window)
    fakebar.drawer = fake_window.create_drawer(fakebar.width, fakebar.height)

    fakebar.window = None
    fakebar.finalize()

    # Must not raise even though finalize() deleted the bar's drawer
    fakebar._actual_draw()
