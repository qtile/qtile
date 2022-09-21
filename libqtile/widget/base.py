# Copyright (c) 2008-2010 Aldo Cortesi
# Copyright (c) 2011 Florian Mounier
# Copyright (c) 2011 Kenji_Takahashi
# Copyright (c) 2011 Paul Colomiets
# Copyright (c) 2012 roger
# Copyright (c) 2012 Craig Barnes
# Copyright (c) 2012-2015 Tycho Andersen
# Copyright (c) 2013 dequis
# Copyright (c) 2013 David R. Andersen
# Copyright (c) 2013 Tao Sauvage
# Copyright (c) 2014-2015 Sean Vig
# Copyright (c) 2014 Justin Bronder
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

from __future__ import annotations

import asyncio
import copy
import math
import subprocess
from typing import TYPE_CHECKING

from libqtile import bar, configurable, confreader
from libqtile.command import interface
from libqtile.command.base import CommandError, CommandObject
from libqtile.lazy import LazyCall
from libqtile.log_utils import logger

if TYPE_CHECKING:
    from typing import Any

    from libqtile.command.base import ItemT

# Each widget class must define which bar orientation(s) it supports by setting
# these bits in an 'orientations' class attribute. Simply having the attribute
# inherited by superclasses is discouraged, because if a superclass that was
# only supporting one orientation, adds support for the other, its subclasses
# will have to be adapted too, in general. ORIENTATION_NONE is only added for
# completeness' sake.
# +------------------------+--------------------+--------------------+
# | Widget bits            | Horizontal bar     | Vertical bar       |
# +========================+====================+====================+
# | ORIENTATION_NONE       | ConfigError raised | ConfigError raised |
# +------------------------+--------------------+--------------------+
# | ORIENTATION_HORIZONTAL | Widget displayed   | ConfigError raised |
# |                        | horizontally       |                    |
# +------------------------+--------------------+--------------------+
# | ORIENTATION_VERTICAL   | ConfigError raised | Widget displayed   |
# |                        |                    | vertically         |
# +------------------------+--------------------+--------------------+
# | ORIENTATION_BOTH       | Widget displayed   | Widget displayed   |
# |                        | horizontally       | vertically         |
# +------------------------+--------------------+--------------------+


class _Orientations(int):
    def __new__(cls, value, doc):
        return super().__new__(cls, value)

    def __init__(self, value, doc):
        self.doc = doc

    def __str__(self):
        return self.doc

    def __repr__(self):
        return self.doc


ORIENTATION_NONE = _Orientations(0, "none")
ORIENTATION_HORIZONTAL = _Orientations(1, "horizontal only")
ORIENTATION_VERTICAL = _Orientations(2, "vertical only")
ORIENTATION_BOTH = _Orientations(3, "horizontal and vertical")


class _Widget(CommandObject, configurable.Configurable):
    """Base Widget class

    If length is set to the special value `bar.STRETCH`, the bar itself will
    set the length to the maximum remaining space, after all other widgets have
    been configured.

    In horizontal bars, 'length' corresponds to the width of the widget; in
    vertical bars, it corresponds to the widget's height.

    The offsetx and offsety attributes are set by the Bar after all widgets
    have been configured.

    Callback functions can be assigned to button presses by passing a dict to the
    'callbacks' kwarg. No arguments are passed to the function so, if
    you need access to the qtile object, it needs to be imported into your code.

    ``lazy`` functions can also be passed as callback functions and can be used in
    the same was as keybindings.

    For example:

    .. code-block:: python

        from libqtile import qtile

        def open_calendar():
            qtile.cmd_spawn('gsimplecal next_month')

        clock = widget.Clock(
            mouse_callbacks={
                'Button1': open_calendar,
                'Button3': lazy.spawn('gsimplecal prev_month')
            }
        )

    When the clock widget receives a click with button 1, the ``open_calendar`` function
    will be executed.
    """

    orientations = ORIENTATION_BOTH

    # Default (empty set) is for all backends to be supported. Widgets can override this
    # to explicitly confirm which backends are supported
    supported_backends: set[str] = set()

    offsetx: int = 0
    offsety: int = 0
    defaults = [
        ("background", None, "Widget background color"),
        (
            "mouse_callbacks",
            {},
            "Dict of mouse button press callback functions. Accepts functions and ``lazy`` calls.",
        ),
    ]  # type: list[tuple[str, Any, str]]

    def __init__(self, length, **config):
        """
        length: bar.STRETCH, bar.CALCULATED, or a specified length.
        """
        CommandObject.__init__(self)
        self.name = self.__class__.__name__.lower()
        if "name" in config:
            self.name = config["name"]

        configurable.Configurable.__init__(self, **config)
        self.add_defaults(_Widget.defaults)

        if length in (bar.CALCULATED, bar.STRETCH):
            self.length_type = length
            self.length = 0
        elif isinstance(length, int):
            self.length_type = bar.STATIC
            self.length = length
        else:
            raise confreader.ConfigError("Widget width must be an int")

        self.configured = False
        self._futures: list[asyncio.TimerHandle] = []
        self._mirrors: set[_Widget] = set()

    @property
    def length(self):
        if self.length_type == bar.CALCULATED:
            return int(self.calculate_length())
        return self._length

    @length.setter
    def length(self, value):
        self._length = value

    @property
    def width(self):
        if self.bar.horizontal:
            return self.length
        return self.bar.size - (self.bar.border_width[1] + self.bar.border_width[3])

    @property
    def height(self):
        if self.bar.horizontal:
            return self.bar.size - (self.bar.border_width[0] + self.bar.border_width[2])
        return self.length

    @property
    def offset(self):
        if self.bar.horizontal:
            return self.offsetx
        return self.offsety

    def _test_orientation_compatibility(self, horizontal):
        if horizontal:
            if not self.orientations & ORIENTATION_HORIZONTAL:
                raise confreader.ConfigError(
                    self.__class__.__name__
                    + " is not compatible with the orientation of the bar."
                )
        elif not self.orientations & ORIENTATION_VERTICAL:
            raise confreader.ConfigError(
                self.__class__.__name__ + " is not compatible with the orientation of the bar."
            )

    def timer_setup(self):
        """This is called exactly once, after the widget has been configured
        and timers are available to be set up."""
        pass

    def _configure(self, qtile, bar):
        self._test_orientation_compatibility(bar.horizontal)

        self.qtile = qtile
        self.bar = bar
        self.drawer = bar.window.create_drawer(self.bar.width, self.bar.height)
        if not self.configured:
            self.qtile.call_soon(self.timer_setup)
            self.qtile.call_soon(asyncio.create_task, self._config_async())

    async def _config_async(self):
        """
        This is called once when the main eventloop has started. this
        happens after _configure has been run.

        Widgets that need to use asyncio coroutines after this point may
        wish to initialise the relevant code (e.g. connections to dbus
        using dbus_next) here.
        """
        pass

    def finalize(self):
        for future in self._futures:
            future.cancel()
        if hasattr(self, "layout") and self.layout:
            self.layout.finalize()
        self.drawer.finalize()

    def clear(self):
        self.drawer.set_source_rgb(self.bar.background)
        self.drawer.fillrect(self.offsetx, self.offsety, self.width, self.height)

    def info(self):
        return dict(
            name=self.name,
            offset=self.offset,
            length=self.length,
            width=self.width,
            height=self.height,
        )

    def add_callbacks(self, defaults):
        """Add default callbacks with a lower priority than user-specified callbacks."""
        defaults.update(self.mouse_callbacks)
        self.mouse_callbacks = defaults

    def button_press(self, x, y, button):
        name = "Button{0}".format(button)
        if name in self.mouse_callbacks:
            cmd = self.mouse_callbacks[name]
            if isinstance(cmd, LazyCall):
                if cmd.check(self.qtile):
                    status, val = self.qtile.server.call(
                        (cmd.selectors, cmd.name, cmd.args, cmd.kwargs)
                    )
                    if status in (interface.ERROR, interface.EXCEPTION):
                        logger.error("Mouse callback command error %s: %s", cmd.name, val)
            else:
                cmd()

    def button_release(self, x, y, button):
        pass

    def get(self, q, name):
        """
        Utility function for quick retrieval of a widget by name.
        """
        w = q.widgets_map.get(name)
        if not w:
            raise CommandError("No such widget: %s" % name)
        return w

    def _items(self, name: str) -> ItemT:
        if name == "bar":
            return True, []
        elif name == "screen":
            return True, []
        return None

    def _select(self, name, sel):
        if name == "bar":
            return self.bar
        elif name == "screen":
            return self.bar.screen

    def cmd_info(self):
        """
        Info for this object.
        """
        return self.info()

    def draw(self):
        """
        Method that draws the widget. You may call this explicitly to
        redraw the widget, but only if the length of the widget hasn't
        changed. If it has, you must call bar.draw instead.
        """
        raise NotImplementedError

    def calculate_length(self):
        """
        Must be implemented if the widget can take CALCULATED for length.
        It must return the width of the widget if it's installed in a
        horizontal bar; it must return the height of the widget if it's
        installed in a vertical bar. Usually you will test the orientation
        of the bar with 'self.bar.horizontal'.
        """
        raise NotImplementedError

    def timeout_add(self, seconds, method, method_args=()):
        """
        This method calls ``.call_later`` with given arguments.
        """
        future = self.qtile.call_later(seconds, self._wrapper, method, *method_args)

        self._futures.append(future)
        return future

    def call_process(self, command, **kwargs):
        """
        This method uses `subprocess.check_output` to run the given command
        and return the string from stdout, which is decoded when using
        Python 3.
        """
        return subprocess.check_output(command, **kwargs, encoding="utf-8")

    def _remove_dead_timers(self):
        """Remove completed and cancelled timers from the list."""
        self._futures = [
            timer
            for timer in self._futures
            if not (timer.cancelled() or timer.when() < self.qtile._eventloop.time())
        ]

    def _wrapper(self, method, *method_args):
        self._remove_dead_timers()
        try:
            method(*method_args)
        except:  # noqa: E722
            logger.exception("got exception from widget timer")

    def create_mirror(self):
        return Mirror(self, background=self.background)

    def clone(self):
        return copy.copy(self)

    def mouse_enter(self, x, y):
        pass

    def mouse_leave(self, x, y):
        pass

    def _draw_with_mirrors(self) -> None:
        self._old_draw()
        for mirror in self._mirrors:
            if not mirror.configured:
                continue

            # If the widget and mirror are on the same bar then we could have an
            # infinite loop when we call bar.draw(). mirror.draw() will trigger a resize
            # if it's the wrong size.
            if mirror.length_type == bar.CALCULATED and mirror.bar is not self.bar:
                mirror.bar.draw()
            else:
                mirror.draw()

    def add_mirror(self, widget: _Widget):
        if not self._mirrors:
            self._old_draw = self.draw
            self.draw = self._draw_with_mirrors  # type: ignore

        self._mirrors.add(widget)
        if not self.drawer.has_mirrors:
            self.drawer.has_mirrors = True

    def remove_mirror(self, widget: _Widget):
        try:
            self._mirrors.remove(widget)
        except KeyError:
            pass

        if not self._mirrors:
            self.drawer.has_mirrors = False

            if hasattr(self, "_old_draw"):
                # Deletes the reference to draw and falls back to the original
                del self.draw
                del self._old_draw


UNSPECIFIED = bar.Obj("UNSPECIFIED")


class _TextBox(_Widget):
    """
    Base class for widgets that are just boxes containing text.
    """

    orientations = ORIENTATION_BOTH
    defaults = [
        ("font", "sans", "Default font"),
        ("fontsize", None, "Font size. Calculated if None."),
        ("padding", None, "Padding. Calculated if None."),
        ("foreground", "ffffff", "Foreground colour"),
        ("fontshadow", None, "font shadow color, default is None(no shadow)"),
        ("markup", True, "Whether or not to use pango markup"),
        (
            "fmt",
            "{}",
            "To format the string returned by the widget. For example, if the clock widget \
             returns '08:46' we can do fmt='time {}' do print 'time 08:46' on the widget. \
             To format the individual strings like hour and minutes use the format paramater \
             of the widget (if it has one)",
        ),
        ("max_chars", 0, "Maximum number of characters to display in widget."),
        (
            "scroll",
            False,
            "Whether text should be scrolled. When True, you must set the widget's ``width``.",
        ),
        (
            "scroll_repeat",
            True,
            "Whether text should restart scrolling once the text has ended",
        ),
        (
            "scroll_delay",
            2,
            "Number of seconds to pause before starting scrolling and restarting/clearing text at end",
        ),
        ("scroll_step", 1, "Number of pixels to scroll with each step"),
        ("scroll_interval", 0.1, "Time in seconds before next scrolling step"),
        (
            "scroll_clear",
            False,
            "Whether text should scroll completely away (True) or stop when the end of the text is shown (False)",
        ),
        ("scroll_hide", False, "Whether the widget should hide when scrolling has finished"),
    ]  # type: list[tuple[str, Any, str]]

    def __init__(self, text=" ", width=bar.CALCULATED, **config):
        self.layout = None
        _Widget.__init__(self, width, **config)
        self.add_defaults(_TextBox.defaults)
        self.text = text
        self._is_scrolling = False
        self._should_scroll = False
        self._scroll_offset = 0
        self._scroll_queued = False
        self._scroll_timer = None
        self._scroll_width = width

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, value):
        if len(value) > self.max_chars > 0:
            value = value[: self.max_chars] + "…"
        self._text = value
        if self.layout:
            self.layout.text = self.formatted_text
            if self.scroll:
                self.check_width()
                self.reset_scroll()

    @property
    def formatted_text(self):
        return self.fmt.format(self._text)

    @property
    def foreground(self):
        return self._foreground

    @foreground.setter
    def foreground(self, fg):
        self._foreground = fg
        if self.layout:
            self.layout.colour = fg

    @property
    def font(self):
        return self._font

    @font.setter
    def font(self, value):
        self._font = value
        if self.layout:
            self.layout.font = value

    @property
    def fontshadow(self):
        return self._fontshadow

    @fontshadow.setter
    def fontshadow(self, value):
        self._fontshadow = value
        if self.layout:
            self.layout.font_shadow = value

    @property
    def actual_padding(self):
        if self.padding is None:
            return self.fontsize / 2
        else:
            return self.padding

    def _configure(self, qtile, bar):
        _Widget._configure(self, qtile, bar)
        if self.fontsize is None:
            self.fontsize = self.bar.height - self.bar.height / 5
        self.layout = self.drawer.textlayout(
            self.formatted_text,
            self.foreground,
            self.font,
            self.fontsize,
            self.fontshadow,
            markup=self.markup,
        )
        if not isinstance(self._scroll_width, int) and self.scroll:
            logger.warning("%s: You must specify a width when enabling scrolling.", self.name)
            self.scroll = False

        if self.scroll:
            self.check_width()

    def check_width(self):
        """
        Check whether the widget needs to have calculated or fixed width
        and whether the text should be scrolled.
        """
        if self.layout.width > self._scroll_width:
            self.length_type = bar.STATIC
            self.length = self._scroll_width
            self._is_scrolling = True
            self._should_scroll = True
        else:
            self.length_type = bar.CALCULATED
            self._should_scroll = False

    def calculate_length(self):
        if self.text:
            if self.bar.horizontal:
                return min(self.layout.width, self.bar.width) + self.actual_padding * 2
            else:
                return min(self.layout.width, self.bar.height) + self.actual_padding * 2
        else:
            return 0

    def can_draw(self):
        can_draw = (
            self.layout is not None and not self.layout.finalized() and self.offsetx is not None
        )  # if the bar hasn't placed us yet
        return can_draw

    def draw(self):
        if not self.can_draw():
            return
        self.drawer.clear(self.background or self.bar.background)

        # size = self.bar.height if self.bar.horizontal else self.bar.width
        self.drawer.ctx.save()

        if not self.bar.horizontal:
            # Left bar reads bottom to top
            if self.bar.screen.left is self.bar:
                self.drawer.ctx.rotate(-90 * math.pi / 180.0)
                self.drawer.ctx.translate(-self.length, 0)

            # Right bar is top to bottom
            else:
                self.drawer.ctx.translate(self.bar.width, 0)
                self.drawer.ctx.rotate(90 * math.pi / 180.0)

        # If we're scrolling, we clip the context to the scroll width less the padding
        # Move the text layout position (and we only see the clipped portion)
        if self._should_scroll:
            self.drawer.ctx.rectangle(
                self.actual_padding,
                0,
                self._scroll_width - 2 * self.actual_padding,
                self.bar.size,
            )
            self.drawer.ctx.clip()

        size = self.bar.height if self.bar.horizontal else self.bar.width

        self.layout.draw(
            (self.actual_padding or 0) - self._scroll_offset,
            int(size / 2.0 - self.layout.height / 2.0) + 1,
        )
        self.drawer.ctx.restore()

        self.drawer.draw(
            offsetx=self.offsetx, offsety=self.offsety, width=self.width, height=self.height
        )

        # We only want to scroll if:
        # - User has asked us to scroll and the scroll width is smaller than the layout (should_scroll=True)
        # - We are still scrolling (is_scrolling=True)
        # - We haven't already queued the next scroll (scroll_queued=False)
        if self._should_scroll and self._is_scrolling and not self._scroll_queued:
            self._scroll_queued = True
            if self._scroll_offset == 0:
                interval = self.scroll_delay
            else:
                interval = self.scroll_interval
            self._scroll_timer = self.timeout_add(interval, self.do_scroll)

    def do_scroll(self):
        # Allow the next scroll tick to be queued
        self._scroll_queued = False

        # If we're still scrolling, adjust the next offset
        if self._is_scrolling:
            self._scroll_offset += self.scroll_step

        # Check whether we need to stop scrolling when:
        # - we've scrolled all the text off the widget (scroll_clear = True)
        # - the final pixel is visible (scroll_clear = False)
        if (self.scroll_clear and self._scroll_offset > self.layout.width) or (
            not self.scroll_clear
            and (self.layout.width - self._scroll_offset)
            < (self._scroll_width - 2 * self.actual_padding)
        ):
            self._is_scrolling = False

        # We've reached the end of the scroll so what next?
        if not self._is_scrolling:
            if self.scroll_repeat:
                # Pause and restart scrolling
                self._scroll_timer = self.timeout_add(self.scroll_delay, self.reset_scroll)
            elif self.scroll_hide:
                # Clear the text
                self._scroll_timer = self.timeout_add(self.scroll_delay, self.hide_scroll)
            # If neither of these options then the text is no longer updated.

        self.draw()

    def reset_scroll(self):
        self._scroll_offset = 0
        self._is_scrolling = True
        self._scroll_queued = False
        if self._scroll_timer:
            self._scroll_timer.cancel()
        self.draw()

    def hide_scroll(self):
        self.update("")

    def cmd_set_font(self, font=UNSPECIFIED, fontsize=UNSPECIFIED, fontshadow=UNSPECIFIED):
        """
        Change the font used by this widget. If font is None, the current
        font is used.
        """
        if font is not UNSPECIFIED:
            self.font = font
        if fontsize is not UNSPECIFIED:
            self.fontsize = fontsize
        if fontshadow is not UNSPECIFIED:
            self.fontshadow = fontshadow
        self.bar.draw()

    def info(self):
        d = _Widget.info(self)
        d["foreground"] = self.foreground
        d["text"] = self.formatted_text
        return d

    def update(self, text):
        if self.text == text:
            return
        if text is None:
            text = ""

        old_width = self.layout.width
        self.text = text

        # If our width hasn't changed, we just draw ourselves. Otherwise,
        # we draw the whole bar.
        if self.layout.width == old_width:
            self.draw()
        else:
            self.bar.draw()


class InLoopPollText(_TextBox):
    """A common interface for polling some 'fast' information, munging it, and
    rendering the result in a text box. You probably want to use
    ThreadPoolText instead.

    ('fast' here means that this runs /in/ the event loop, so don't block! If
    you want to run something nontrivial, use ThreadedPollWidget.)"""

    defaults = [
        (
            "update_interval",
            600,
            "Update interval in seconds, if none, the "
            "widget updates whenever the event loop is idle.",
        ),
    ]  # type: list[tuple[str, Any, str]]

    def __init__(self, default_text="N/A", **config):
        _TextBox.__init__(self, default_text, **config)
        self.add_defaults(InLoopPollText.defaults)

    def timer_setup(self):
        update_interval = self.tick()
        # If self.update_interval is defined and .tick() returns None, re-call
        # after self.update_interval
        if update_interval is None and self.update_interval is not None:
            self.timeout_add(self.update_interval, self.timer_setup)
        # We can change the update interval by returning something from .tick()
        elif update_interval:
            self.timeout_add(update_interval, self.timer_setup)
        # If update_interval is False, we won't re-call

    def _configure(self, qtile, bar):
        should_tick = self.configured
        _TextBox._configure(self, qtile, bar)

        # Update when we are being re-configured.
        if should_tick:
            self.tick()

    def button_press(self, x, y, button):
        self.tick()
        _TextBox.button_press(self, x, y, button)

    def poll(self):
        return "N/A"

    def tick(self):
        text = self.poll()
        self.update(text)


class ThreadPoolText(_TextBox):
    """A common interface for wrapping blocking events which when triggered
    will update a textbox.

    The poll method is intended to wrap a blocking function which may take
    quite a while to return anything.  It will be executed as a future and
    should return updated text when completed.  It may also return None to
    disable any further updates.

    param: text - Initial text to display.
    """

    defaults = [
        (
            "update_interval",
            600,
            "Update interval in seconds, if none, the " "widget updates whenever it's done.",
        ),
    ]  # type: list[tuple[str, Any, str]]

    def __init__(self, text, **config):
        super().__init__(text, **config)
        self.add_defaults(ThreadPoolText.defaults)

    def timer_setup(self):
        def on_done(future):
            try:
                result = future.result()
            except Exception:
                result = None
                logger.exception("poll() raised exceptions, not rescheduling")

            if result is not None:
                try:
                    self.update(result)

                    if self.update_interval is not None:
                        self.timeout_add(self.update_interval, self.timer_setup)
                    else:
                        self.timer_setup()

                except Exception:
                    logger.exception("Failed to reschedule.")
            else:
                logger.warning("poll() returned None, not rescheduling")

        self.future = self.qtile.run_in_executor(self.poll)
        self.future.add_done_callback(on_done)

    def poll(self):
        pass

    def cmd_force_update(self):
        """Immediately poll the widget. Existing timers are unaffected."""
        self.update(self.poll())


# these two classes below look SUSPICIOUSLY similar


class PaddingMixin(configurable.Configurable):
    """Mixin that provides padding(_x|_y|)

    To use it, subclass and add this to __init__:

        self.add_defaults(base.PaddingMixin.defaults)
    """

    defaults = [
        ("padding", 3, "Padding inside the box"),
        ("padding_x", None, "X Padding. Overrides 'padding' if set"),
        ("padding_y", None, "Y Padding. Overrides 'padding' if set"),
    ]  # type: list[tuple[str, Any, str]]

    padding_x = configurable.ExtraFallback("padding_x", "padding")
    padding_y = configurable.ExtraFallback("padding_y", "padding")


class MarginMixin(configurable.Configurable):
    """Mixin that provides margin(_x|_y|)

    To use it, subclass and add this to __init__:

        self.add_defaults(base.MarginMixin.defaults)
    """

    defaults = [
        ("margin", 3, "Margin inside the box"),
        ("margin_x", None, "X Margin. Overrides 'margin' if set"),
        ("margin_y", None, "Y Margin. Overrides 'margin' if set"),
    ]  # type: list[tuple[str, Any, str]]

    margin_x = configurable.ExtraFallback("margin_x", "margin")
    margin_y = configurable.ExtraFallback("margin_y", "margin")


class Mirror(_Widget):
    """
    A widget for showing the same widget content in more than one place, for
    instance, on bars across multiple screens.

    You don't need to use it directly; instead, just instantiate your widget
    once and hand it in to multiple bars. For instance::

        cpu = widget.CPUGraph()
        clock = widget.Clock()

        screens = [
            Screen(top=bar.Bar([widget.GroupBox(), cpu, clock])),
            Screen(top=bar.Bar([widget.GroupBox(), cpu, clock])),
        ]

    Widgets can be passed to more than one bar, so that there don't need to be
    any duplicates executing the same code all the time, and they'll always be
    visually identical.

    This works for all widgets that use `drawers` (and nothing else) to display
    their contents. Currently, this is all widgets except for `Systray`.
    """

    def __init__(self, reflection, **config):
        _Widget.__init__(self, reflection.length, **config)
        self.reflects = reflection
        self._length = 0
        if self.reflects.length_type == bar.STRETCH:
            self.length_type = bar.STRETCH

    def _configure(self, qtile, bar):
        _Widget._configure(self, qtile, bar)
        self.reflects.add_mirror(self)
        # We need to fill the background once before `draw` is called so, if
        # there's no reflection, the mirror matches its parent bar.
        self.drawer.clear(self.background or self.bar.background)

    @property
    def length(self):
        if self.length_type != bar.STRETCH:
            return self.reflects.length
        return self._length

    @length.setter
    def length(self, value):
        self._length = value

    def draw(self):
        if self.length_type != bar.STRETCH and self._length != self.reflects.length:
            self._length = self.length
            self.bar.draw()
        else:
            self.drawer.clear(self.reflects.background or self.bar.background)
            self.reflects.drawer.paint_to(self.drawer)
            self.drawer.draw(offsetx=self.offset, offsety=self.offsety, width=self.width)

    def button_press(self, x, y, button):
        self.reflects.button_press(x, y, button)

    def mouse_enter(self, x, y):
        self.reflects.mouse_enter(x, y)

    def mouse_leave(self, x, y):
        self.reflects.mouse_leave(x, y)

    def finalize(self):
        self.reflects.remove_mirror(self)
        _Widget.finalize(self)
