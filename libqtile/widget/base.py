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
import inspect
import math
import subprocess
from typing import TYPE_CHECKING

from libqtile import bar, configurable, confreader
from libqtile.command import interface
from libqtile.command.base import CommandError, CommandObject, expose_command
from libqtile.lazy import LazyCall
from libqtile.log_utils import logger
from libqtile.utils import ColorType, create_task

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
    the same way as keybindings.

    For example:

    .. code-block:: python

        from libqtile import qtile

        def open_calendar():
            qtile.spawn('gsimplecal next_month')

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
    defaults: list[tuple[str, Any, str]] = [
        ("background", None, "Widget background color"),
        (
            "mouse_callbacks",
            {},
            "Dict of mouse button press callback functions. Accepts functions and ``lazy`` calls.",
        ),
        ("hide_crash", False, "Don't display error in bar if widget crashes on startup."),
    ]

    def __init__(self, length, **config):
        """
        length: bar.STRETCH, bar.CALCULATED, or a specified length.
        """
        CommandObject.__init__(self)
        self.name = self.__class__.__name__.lower()
        if "name" in config:
            self.name = config["name"]

        configurable.Configurable.__init__(self, **config)

        # Add defaults for Mixins if inherited
        if isinstance(self, PaddingMixin):
            self.add_defaults(PaddingMixin.defaults)
        if isinstance(self, MarginMixin):
            self.add_defaults(MarginMixin.defaults)

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
        self._futures: list[asyncio.Handle] = []
        self._mirrors: set[_Widget] = set()
        self.finalized = False

    @property
    def length(self):
        if self.length_type == bar.CALCULATED:
            try:
                return int(self.calculate_length())
            except Exception:
                logger.exception(f"error when calculating widget {self.name} length")
                return 0
        return self._length

    @length.setter
    def length(self, value):
        self._length = value

    @property
    def width(self):
        if self.bar.horizontal:
            return self.length
        return self.bar.width

    @property
    def height(self):
        if self.bar.horizontal:
            return self.bar.height
        return self.length

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

    def _configure(self, qtile, bar):
        self._test_orientation_compatibility(bar.horizontal)

        self.qtile = qtile
        self.bar = bar
        self.drawer = bar.window.create_drawer(self.bar.width, self.bar.height)

        # Clear this flag as widget may be restarted (e.g. if screen removed and re-added)
        self.finalized = False

        # Timers are added to futures list so they can be cancelled if the `finalize` method is
        # called before the timers have fired.
        if not self.configured:
            timer = self.qtile.call_soon(self.timer_setup)
            async_timer = self.qtile.call_soon(asyncio.create_task, self._config_async())

            # Add these to our list of futures so they can be cancelled.
            self._futures.extend([timer, async_timer])

    async def _config_async(self):
        """
        This is called once when the main eventloop has started. this
        happens after _configure has been run.

        Widgets that need to use asyncio coroutines after this point may
        wish to initialise the relevant code (e.g. connections to dbus
        using dbus_fast) here.
        """

    def finalize(self):
        for future in self._futures:
            future.cancel()
        if hasattr(self, "layout") and self.layout:
            self.layout.finalize()
            self.layout = None
        self.drawer.finalize()
        self.finalized = True

        # Reset configuration status so the widget can be reconfigured
        # e.g. when screen is re-added
        self.configured = False

    def clear(self):
        self.drawer.set_source_rgb(self.bar.background)
        self.drawer.fillrect(self.offsetx, self.offsety, self.width, self.height)

    @expose_command()
    def info(self):
        """Info for this object."""
        return dict(
            name=self.name,
            offset=self.offsetx if self.bar.horizontal else self.offsety,
            length=self.length,
            width=self.width,
            height=self.height,
        )

    def add_callbacks(self, defaults):
        """Add default callbacks with a lower priority than user-specified callbacks."""
        defaults.update(self.mouse_callbacks)
        self.mouse_callbacks = defaults

    def button_press(self, x, y, button):
        name = f"Button{button}"
        if name in self.mouse_callbacks:
            cmd = self.mouse_callbacks[name]
            if isinstance(cmd, LazyCall):
                if cmd.check(self.qtile):
                    status, val = self.qtile.server.call(
                        (cmd.selectors, cmd.name, cmd.args, cmd.kwargs, False)
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
            raise CommandError(f"No such widget: {name}")
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

    def rotate_drawer_left(self):
        # Left bar reads bottom to top
        self.drawer.ctx.rotate(-90 * math.pi / 180.0)
        self.drawer.ctx.translate(-self.length, 0)

    def rotate_drawer_right(self):
        # Right bar is top to bottom
        self.drawer.ctx.translate(self.bar.width, 0)
        self.drawer.ctx.rotate(90 * math.pi / 180.0)

    def rotate_drawer(self):
        if self.bar.horizontal:
            return
        if self.bar.screen.left is self.bar:
            self.rotate_drawer_left()
        elif self.bar.screen.right is self.bar:
            self.rotate_drawer_right()

    def draw_at_default_position(self):
        """Default position to draw the widget in horizontal and vertical bars."""
        self.drawer.draw(
            offsetx=self.offsetx, offsety=self.offsety, width=self.width, height=self.height
        )

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
        # Don't add timers for finalised widgets
        if self.finalized:
            return

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

    async def acall_process(self, command, shell=False) -> str:
        """
        Like call_process, but the async version
        """
        stdin = asyncio.subprocess.DEVNULL
        stdout = asyncio.subprocess.PIPE
        stderr = asyncio.subprocess.STDOUT

        if shell:
            p = await asyncio.subprocess.create_subprocess_shell(
                command, stdin=stdin, stdout=stdout, stderr=stderr
            )
        else:
            p = await asyncio.subprocess.create_subprocess_exec(
                *command, stdin=stdin, stdout=stdout, stderr=stderr
            )

        (out, _) = await p.communicate()
        return out.decode("utf-8")

    def _remove_dead_timers(self):
        """Remove completed and cancelled timers from the list."""

        def is_ready(timer):
            return timer in self.qtile._eventloop._ready

        self._futures = [
            timer
            for timer in self._futures
            # Filter out certain handles...
            if not (
                timer.cancelled()
                # Once a scheduled timer is ready to be run its _scheduled flag is set to False
                # and it's added to the loop's `_ready` queue
                or (
                    isinstance(timer, asyncio.TimerHandle)
                    and not timer._scheduled
                    and not is_ready(timer)
                )
                # Callbacks scheduled via `call_soon` are put into the loop's `_ready` queue
                # and are removed once they've been executed
                or (isinstance(timer, asyncio.Handle) and not is_ready(timer))
            )
        ]

    def _wrapper(self, method, *method_args):
        self._remove_dead_timers()
        try:
            if inspect.iscoroutinefunction(method):
                create_task(method(*method_args))
            elif asyncio.iscoroutine(method):
                create_task(method)
            else:
                method(*method_args)
        except:  # noqa: E722
            logger.exception("got exception from widget timer")

    def create_mirror(self):
        return Mirror(self, background=self.background)

    def clone(self):
        return copy.deepcopy(self)

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
            self.draw = self._draw_with_mirrors

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
            "Format to apply to the string returned by the widget. Main purpose: applying markup. "
            "For a widget that returns ``foo``, using ``fmt='<i>{}</i>'`` would give you ``<i>foo</i>``. "
            "To control what the widget outputs in the first place, use the ``format`` paramater of the widget (if it has one).",
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
        (
            "scroll_fixed_width",
            False,
            "When ``scroll=True`` the ``width`` parameter is a maximum width and, when text is shorter than this, the widget will resize. "
            "Setting ``scroll_fixed_width=True`` will force the widget to have a fixed width, regardless of the size of the text.",
        ),
        ("rotate", True, "Rotate text in vertical bar."),
        (
            "direction",
            "default",
            "Override the text direction in vertical bar, has no effect on text in horizontal bar."
            "default: text displayed based on vertical bar position (left/right)"
            "ttb: text read from top to bottom, btt: text read from bottom to top."
            "'default', 'ttb', 'btt'",
        ),
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

    def _configure(self, qtile, bar):
        _Widget._configure(self, qtile, bar)
        if self.fontsize is None:
            self.fontsize = self.bar.size - self.bar.size / 5
        if self.padding is None:
            self.padding = self.fontsize // 2
        if self.direction not in ("default", "ttb", "btt"):
            logger.warning(
                "Invalid value set for direction: %s. Valid values are: 'default', 'ttb', 'btt'. "
                "direction has been set to 'default'",
                self.direction,
            )
            self.direction = "default"
        self.layout = self.drawer.textlayout(
            self.formatted_text,
            self.foreground,
            self.font,
            self.fontsize,
            self.fontshadow,
            markup=self.markup,
        )
        if not isinstance(self._scroll_width, int) and self.scroll:
            if not self.bar.horizontal and not self.rotate:
                self._scroll_width = self.bar.width
            else:
                logger.warning("%s: You must specify a width when enabling scrolling.", self.name)
                self.scroll = False

        # Setting the layout width will wrap text which increases layout's height,
        # we only want this when bar is vertical and rotation is disabled
        # to be able to display more of the text using multiple lines,
        # only if scrolling is enabled the layout width will be overwritten
        # because the widget's width is handle by scroll.
        if not self.bar.horizontal and not self.rotate:
            self.layout.width = self.bar.width

        if self.scroll:
            self.check_width()

    def check_width(self):
        """
        Check whether the widget needs to have calculated or fixed width
        and whether the text should be scrolled.
        """
        # Reset the layout width to let the layout calculate
        # the width based on the length of the text.
        self.layout.reset_width()
        if self.layout.width > self._scroll_width:
            if self.bar.horizontal or self.rotate:
                self.length_type = bar.STATIC
                self.length = self._scroll_width
            self._is_scrolling = True
            self._should_scroll = True
        else:
            if not self.bar.horizontal and not self.rotate:
                self.layout.width = self.bar.width
            elif self.scroll_fixed_width:
                self.length_type = bar.STATIC
                self.length = self._scroll_width
            else:
                self.length_type = bar.CALCULATED
            self._should_scroll = False

    def calculate_length(self):
        if not self.text:
            return 0
        if not self.bar.horizontal and not self.rotate:
            return self.layout.height + self.padding * 2
        else:
            return min(self.layout.width, self.bar.length) + self.padding * 2

    def can_draw(self):
        return self.layout is not None

    def rotate_drawer(self):
        if self.bar.horizontal or not self.rotate:
            return
        # Execute the base method when direction is default
        if self.direction == "default":
            _Widget.rotate_drawer(self)
        # Read bottom to top always with 'btt' direction
        elif self.direction == "btt":
            self.rotate_drawer_left()
        # Read top to bottom always with 'ttb' direction
        elif self.direction == "ttb":
            self.rotate_drawer_right()

    def draw(self):
        if not self.can_draw():
            return
        self.drawer.clear(self.background or self.bar.background)
        self.drawer.ctx.save()
        self.rotate_drawer()

        # If we're scrolling, we clip the context to the scroll width less the padding
        # Move the text layout position (and we only see the clipped portion)
        if self._should_scroll:
            height = self.bar.size if self.bar.horizontal or self.rotate else self.length
            self.drawer.ctx.rectangle(0, 0, self._scroll_width, height)
            self.drawer.ctx.clip()

        if not self.bar.horizontal and not self.rotate:
            x, y = 0, self.padding
        else:
            x = self.padding if self.length_type != bar.STATIC else 0
            y = (self.bar.size - self.layout.height) / 2 + 1

        self.layout.draw(x - self._scroll_offset, y)
        self.drawer.ctx.restore()

        self.draw_at_default_position()

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
            and (self.layout.width - self._scroll_offset) < (self._scroll_width)
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

    @expose_command()
    def set_font(
        self,
        font: str | None = None,
        fontsize: int = 0,
        fontshadow: ColorType = "",
    ):
        """
        Change the font used by this widget. If font is None, the current
        font is used.
        """
        if font is not None:
            self.font = font
        if fontsize != 0:
            self.fontsize = fontsize
        if fontshadow != "":
            self.fontshadow = fontshadow
        if self.layout:
            self.layout.font_family = self.font
            self.layout.font_size = self.fontsize
            self.layout.font_shadow = self.fontshadow
        self.bar.draw()

    @expose_command()
    def info(self):
        d = _Widget.info(self)
        d["text"] = self.formatted_text
        return d

    def update(self, text):
        """Update the widget text."""
        # Don't try to update text in dead layouts
        # This is mainly required for BackgroundPoll based widgets as the
        # polling function cannot be cancelled and so may be called after the widget
        # is finalised.
        if not self.can_draw():
            return

        if self.text == text:
            return
        if text is None:
            text = ""

        old_width = self.layout.width
        self.text = text

        # If our width hasn't changed, we just draw ourselves. Otherwise,
        # we draw the whole bar.
        if self.layout.width == old_width and (self.bar.horizontal or self.rotate):
            self.draw()
        else:
            self.bar.draw()


class InLoopPollText(_TextBox):
    """A common interface for polling some 'fast' information, munging it, and
    rendering the result in a text box. You probably want to use
    BackgroundPoll instead.

    ('fast' here means that this runs /in/ the event loop, so don't block! If
    you want to run something nontrivial, use BackgroundPoll.)"""

    defaults = [
        (
            "update_interval",
            600,
            "Update interval in seconds, if none, the widget updates only once.",
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

    def button_press(self, x, y, button):
        self.tick()
        _TextBox.button_press(self, x, y, button)

    def poll(self):
        return "N/A"

    def tick(self):
        text = self.poll()
        self.update(text)


class BackgroundPoll(_TextBox):
    """A common interface for wrapping blocking events which when triggered
    will update a textbox.

    The poll/apoll methods are intended to wrap a blocking function which may
    take quite a while to return anything. Either method should return the
    string to update the widget text to. It may also return None to disable
    any further updates.

    If an `async def apoll()` is defined, that will be used to do the polling.

    For widgets that have not been ported to asyncio and define a `def poll()`
    method, their poll method will still be run in a thread as it is today.

    param: text - Initial text to display.
    """

    defaults = [
        (
            "update_interval",
            600,
            "Update interval in seconds, if none, the widget updates only once.",
        ),
    ]  # type: list[tuple[str, Any, str]]

    def __init__(self, text="N/A", **config):
        super().__init__(text, **config)
        self.add_defaults(BackgroundPoll.defaults)

    def timer_setup(self):
        create_task(self.do_tick())

    def poll(self):
        """An optional non-async-based method for polling. Will be run as an
        async future."""

    async def apoll(self):
        """An optional async-based method for polling."""

    async def do_tick(self, requeue=True):
        if type(self).apoll != BackgroundPoll.apoll:
            result = await self.apoll()
        elif type(self).poll != BackgroundPoll.poll:
            future = self.qtile.run_in_executor(self.poll)
            result = await future
        else:
            raise Exception(f"widget {self.name} has neither apoll() nor poll() overridden?")
        if result is not None:
            try:
                self.update(result)
            except Exception:
                logger.exception("Failed to reschedule timer for %s.", self.name)
            if requeue and self.update_interval is not None:
                await asyncio.sleep(self.update_interval)
                create_task(self.do_tick())
        else:
            logger.warning("%s's poll() returned None, not rescheduling", self.name)

    @expose_command()
    def force_update(self):
        """Immediately poll the widget. Existing timers are unaffected."""
        create_task(self.do_tick(requeue=False))


class PaddingMixin(configurable.Configurable):
    """Mixin that provides padding(_x|_y|)."""

    defaults = [
        ("padding", 3, "Padding inside the box"),
        ("padding_x", None, "X Padding. Overrides 'padding' if set"),
        ("padding_y", None, "Y Padding. Overrides 'padding' if set"),
    ]  # type: list[tuple[str, Any, str]]

    padding_x = configurable.ExtraFallback("padding_x", "padding")
    padding_y = configurable.ExtraFallback("padding_y", "padding")

    @property
    def padding_side(self):
        if self.bar.horizontal:
            return self.padding_x
        return self.padding_y

    @property
    def padding_top(self):
        if self.bar.horizontal:
            return self.padding_y
        return self.padding_x


class MarginMixin(configurable.Configurable):
    """Mixin that provides margin(_x|_y|)."""

    defaults = [
        ("margin", 3, "Margin inside the box"),
        ("margin_x", None, "X Margin. Overrides 'margin' if set"),
        ("margin_y", None, "Y Margin. Overrides 'margin' if set"),
    ]  # type: list[tuple[str, Any, str]]

    margin_x = configurable.ExtraFallback("margin_x", "margin")
    margin_y = configurable.ExtraFallback("margin_y", "margin")

    @property
    def margin_side(self):
        if self.bar.horizontal:
            return self.margin_x
        return self.margin_y

    @property
    def margin_top(self):
        if self.bar.horizontal:
            return self.margin_y
        return self.margin_x


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
        self.length_type = self.reflects.length_type
        if self.length_type is bar.STATIC:
            self._length = self.reflects._length

    def _configure(self, qtile, bar):
        _Widget._configure(self, qtile, bar)
        self.reflects.add_mirror(self)
        # We need to fill the background once before `draw` is called so, if
        # there's no reflection, the mirror matches its parent bar.
        self.drawer.clear(self.background or self.bar.background)

    def calculate_length(self):
        return self.reflects.calculate_length()

    @property
    def length(self):
        if self.length_type != bar.STRETCH:
            return self.reflects.length
        return self._length

    @length.setter
    def length(self, value):
        self._length = value

    def draw(self):
        if self.length <= 0:
            return
        self.drawer.clear_rect()
        self.reflects.drawer.paint_to(self.drawer)
        self.draw_at_default_position()

    def button_press(self, x, y, button):
        self.reflects.button_press(x, y, button)

    def mouse_enter(self, x, y):
        self.reflects.mouse_enter(x, y)

    def mouse_leave(self, x, y):
        self.reflects.mouse_leave(x, y)

    def finalize(self):
        self.reflects.remove_mirror(self)
        _Widget.finalize(self)
