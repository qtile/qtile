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

import subprocess
import threading
import warnings
from typing import Any, List, Tuple  # noqa: F401

from libqtile.log_utils import logger
from libqtile.command_object import CommandObject, CommandError
from .. import bar, configurable, drawer, confreader


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


ORIENTATION_NONE = _Orientations(0, 'none')
ORIENTATION_HORIZONTAL = _Orientations(1, 'horizontal only')
ORIENTATION_VERTICAL = _Orientations(2, 'vertical only')
ORIENTATION_BOTH = _Orientations(3, 'horizontal and vertical')


class _Widget(CommandObject, configurable.Configurable):
    """Base Widget class

    If length is set to the special value `bar.STRETCH`, the bar itself will
    set the length to the maximum remaining space, after all other widgets have
    been configured. Only ONE widget per bar can have the `bar.STRETCH` length
    set.

    In horizontal bars, 'length' corresponds to the width of the widget; in
    vertical bars, it corresponds to the widget's height.

    The offsetx and offsety attributes are set by the Bar after all widgets
    have been configured.
    """
    orientations = ORIENTATION_BOTH
    offsetx = None
    offsety = None
    defaults = [("background", None, "Widget background color")]  # type: List[Tuple[str, Any, str]]

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
        else:
            assert isinstance(length, int)
            self.length_type = bar.STATIC
            self.length = length
        self.configured = False

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
        return self.bar.size

    @property
    def height(self):
        if self.bar.horizontal:
            return self.bar.size
        return self.length

    @property
    def offset(self):
        if self.bar.horizontal:
            return self.offsetx
        return self.offsety

    @property
    def win(self):
        return self.bar.window.window

    # Do not start the name with "test", or nosetests will try to test it
    # directly (prepend an underscore instead)
    def _test_orientation_compatibility(self, horizontal):
        if horizontal:
            if not self.orientations & ORIENTATION_HORIZONTAL:
                raise confreader.ConfigError(
                    self.__class__.__name__ +
                    " is not compatible with the orientation of the bar."
                )
        elif not self.orientations & ORIENTATION_VERTICAL:
            raise confreader.ConfigError(
                self.__class__.__name__ +
                " is not compatible with the orientation of the bar."
            )

    def timer_setup(self):
        """ This is called exactly once, after the widget has been configured
        and timers are available to be set up. """
        pass

    def _configure(self, qtile, bar):
        self.qtile = qtile
        self.bar = bar
        self.drawer = drawer.Drawer(
            qtile,
            self.win.wid,
            self.bar.width,
            self.bar.height
        )
        if not self.configured:
            self.configured = True
            self.qtile.call_soon(self.timer_setup)

    def finalize(self):
        if hasattr(self, 'layout') and self.layout:
            self.layout.finalize()
        self.drawer.finalize()

    def clear(self):
        self.drawer.set_source_rgb(self.bar.background)
        self.drawer.fillrect(self.offsetx, self.offsety, self.width,
                             self.height)

    def info(self):
        return dict(
            name=self.name,
            offset=self.offset,
            length=self.length,
            width=self.width,
            height=self.height,
        )

    def button_press(self, x, y, button):
        pass

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

    def _items(self, name):
        if name == "bar":
            return (True, None)

    def _select(self, name, sel):
        if name == "bar":
            return self.bar

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
            This method calls either ``.call_later`` with given arguments.
        """
        return self.qtile.call_later(seconds, self._wrapper, method,
                                     *method_args)

    def call_process(self, command, **kwargs):
        """
            This method uses `subprocess.check_output` to run the given command
            and return the string from stdout, which is decoded when using
            Python 3.
        """
        output = subprocess.check_output(command, **kwargs)
        output = output.decode()
        return output

    def _wrapper(self, method, *method_args):
        try:
            method(*method_args)
        except:  # noqa: E722
            logger.exception('got exception from widget timer')


UNSPECIFIED = bar.Obj("UNSPECIFIED")


class _TextBox(_Widget):
    """
        Base class for widgets that are just boxes containing text.
    """
    orientations = ORIENTATION_HORIZONTAL
    defaults = [
        ("font", "sans", "Default font"),
        ("fontsize", None, "Font size. Calculated if None."),
        ("padding", None, "Padding. Calculated if None."),
        ("foreground", "ffffff", "Foreground colour"),
        (
            "fontshadow",
            None,
            "font shadow color, default is None(no shadow)"
        ),
        ("markup", True, "Whether or not to use pango markup"),
        ("fmt", "{}", "How to format the text")
    ]  # type: List[Tuple[str, Any, str]]

    def __init__(self, text=" ", width=bar.CALCULATED, **config):
        self.layout = None
        _Widget.__init__(self, width, **config)
        self._text = text
        self.add_defaults(_TextBox.defaults)

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, value):
        self._text = value
        if self.layout:
            self.layout.text = self.formatted_text

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

    def calculate_length(self):
        if self.text:
            return min(
                self.layout.width,
                self.bar.width
            ) + self.actual_padding * 2
        else:
            return 0

    def draw(self):
        # if the bar hasn't placed us yet
        if self.offsetx is None:
            return
        self.drawer.clear(self.background or self.bar.background)
        self.layout.draw(
            self.actual_padding or 0,
            int(self.bar.height / 2.0 - self.layout.height / 2.0) + 1
        )
        self.drawer.draw(offsetx=self.offsetx, width=self.width)

    def cmd_set_font(self, font=UNSPECIFIED, fontsize=UNSPECIFIED,
                     fontshadow=UNSPECIFIED):
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
        d['foreground'] = self.foreground
        d['text'] = self.formatted_text
        return d


class InLoopPollText(_TextBox):
    """ A common interface for polling some 'fast' information, munging it, and
    rendering the result in a text box. You probably want to use
    ThreadedPollText instead.

    ('fast' here means that this runs /in/ the event loop, so don't block! If
    you want to run something nontrivial, use ThreadedPollWidget.) """

    defaults = [
        ("update_interval", 600, "Update interval in seconds, if none, the "
            "widget updates whenever the event loop is idle."),
    ]  # type: List[Tuple[str, Any, str]]

    def __init__(self, default_text="N/A", width=bar.CALCULATED, **config):
        _TextBox.__init__(self, default_text, width, **config)
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

    def poll(self):
        return 'N/A'

    def tick(self):
        text = self.poll()
        self.update(text)

    def update(self, text):
        old_width = self.layout.width
        if self.text != text:
            self.text = text
            # If our width hasn't changed, we just draw ourselves. Otherwise,
            # we draw the whole bar.
            if self.layout.width == old_width:
                self.draw()
            else:
                self.bar.draw()


class ThreadedPollText(InLoopPollText):
    """ A common interface for polling some REST URL, munging the data, and
    rendering the result in a text box. """
    def tick(self):
        def worker():
            try:
                text = self.poll()
                if self.qtile is not None:
                    self.qtile.call_soon_threadsafe(self.update, text)
            except:  # noqa: E722
                logger.exception("problem polling to update widget %s", self.name)
        # TODO: There are nice asyncio constructs for this sort of thing, I
        # think...
        threading.Thread(target=worker).start()


class ThreadPoolText(_TextBox):
    """ A common interface for wrapping blocking events which when triggered
    will update a textbox.  This is an alternative to the ThreadedPollText
    class which differs by being push based rather than pull.

    The poll method is intended to wrap a blocking function which may take
    quite a while to return anything.  It will be executed as a future and
    should return updated text when completed.  It may also return None to
    disable any further updates.

    param: text - Initial text to display.
    """
    defaults = [
        ("update_interval", None, "Update interval in seconds, if none, the "
            "widget updates whenever it's done'."),
    ]  # type: List[Tuple[str, Any, str]]

    def __init__(self, text, **config):
        super().__init__(text, width=bar.CALCULATED, **config)
        self.add_defaults(ThreadPoolText.defaults)

    def timer_setup(self):
        def on_done(future):
            try:
                result = future.result()
            except Exception:
                result = None
                logger.exception('poll() raised exceptions, not rescheduling')

            if result is not None:
                try:
                    self.update(result)

                    if self.update_interval is not None:
                        self.timeout_add(self.update_interval, self.timer_setup)
                    else:
                        self.timer_setup()

                except Exception:
                    logger.exception('Failed to reschedule.')
            else:
                logger.warning('poll() returned None, not rescheduling')

        future = self.qtile.run_in_executor(self.poll)
        future.add_done_callback(on_done)

    def update(self, text):
        old_width = self.layout.width
        if self.text == text:
            return

        self.text = text

        if self.layout.width == old_width:
            self.draw()
        else:
            self.bar.draw()

    def poll(self):
        pass

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
    ]  # type: List[Tuple[str, Any, str]]

    padding_x = configurable.ExtraFallback('padding_x', 'padding')
    padding_y = configurable.ExtraFallback('padding_y', 'padding')


class MarginMixin(configurable.Configurable):
    """Mixin that provides margin(_x|_y|)

    To use it, subclass and add this to __init__:

        self.add_defaults(base.MarginMixin.defaults)
    """

    defaults = [
        ("margin", 3, "Margin inside the box"),
        ("margin_x", None, "X Margin. Overrides 'margin' if set"),
        ("margin_y", None, "Y Margin. Overrides 'margin' if set"),
    ]  # type: List[Tuple[str, Any, str]]

    margin_x = configurable.ExtraFallback('margin_x', 'margin')
    margin_y = configurable.ExtraFallback('margin_y', 'margin')


def deprecated(msg):
    warnings.warn(msg, DeprecationWarning)
