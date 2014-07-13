from .. import command, bar, configurable, drawer
import gobject
import logging
import threading
import exceptions
import warnings


LEFT = object()
CENTER = object()


class _Widget(command.CommandObject, configurable.Configurable):
    """
        If width is set to the special value bar.STRETCH, the bar itself
        will set the width to the maximum remaining space, after all other
        widgets have been configured. Only ONE widget per bar can have the
        bar.STRETCH width set.

        The offset attribute is set by the Bar after all widgets have been
        configured.
    """
    offset = None
    defaults = [("background", None, "Widget background color")]

    def __init__(self, width, **config):
        """
            width: bar.STRETCH, bar.CALCULATED, or a specified width.
        """
        command.CommandObject.__init__(self)
        self.name = self.__class__.__name__.lower()
        if "name" in config:
            self.name = config["name"]

        self.log = logging.getLogger('qtile')

        configurable.Configurable.__init__(self, **config)
        self.add_defaults(_Widget.defaults)

        if width in (bar.CALCULATED, bar.STRETCH):
            self.width_type = width
            self.width = 0
        else:
            self.width_type = bar.STATIC
            self.width = width
        self.configured = False

    @property
    def width(self):
        if self.width_type == bar.CALCULATED:
            return int(self.calculate_width())
        return self._width

    @width.setter
    def width(self, value):
        self._width = value

    @property
    def win(self):
        return self.bar.window.window

    def _configure(self, qtile, bar):
        self.qtile = qtile
        self.bar = bar
        self.drawer = drawer.Drawer(
            qtile,
            self.win.wid,
            self.bar.width,
            self.bar.height
        )
        self.configured = True

    def clear(self):
        self.drawer.set_source_rgb(self.bar.background)
        self.drawer.fillrect(self.offset, 0, self.width, self.bar.size)

    def info(self):
        return dict(
            name=self.__class__.__name__,
            offset=self.offset,
            width=self.width,
        )

    def button_press(self, x, y, button):
        pass

    def button_release(self, x, y, button):
        pass

    def get(self, q, name):
        """
            Utility function for quick retrieval of a widget by name.
        """
        w = q.widgetMap.get(name)
        if not w:
            raise command.CommandError("No such widget: %s" % name)
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
        return dict(name=self.name)

    def draw(self):
        """
            Method that draws the widget. You may call this explicitly to
            redraw the widget, but only if the width of the widget hasn't
            changed. If it has, you must call bar.draw instead.
        """
        raise NotImplementedError

    def calculate_width(self):
        """
            Must be implemented if the widget can take CALCULATED for width.
        """
        raise NotImplementedError

    def timeout_add(self, seconds, method, method_args=()):
        """
            This method calls either ``gobject.timeout_add`` or
            ``gobject.timeout_add_seconds`` with same arguments. Latter is
            better for battery usage, but works only with integer timeouts.
        """
        self.log.debug('Adding timer for %r in %.2fs', method, seconds)
        if int(seconds) == seconds:
            return gobject.timeout_add_seconds(
                int(seconds), method, *method_args
            )
        else:
            return gobject.timeout_add(
                int(seconds * 1000), method, *method_args
            )


UNSPECIFIED = bar.Obj("UNSPECIFIED")


class _TextBox(_Widget):
    """
        Base class for widgets that are just boxes containing text.
    """
    defaults = [
        ("font", "Arial", "Default font"),
        ("fontsize", None, "Font size. Calculated if None."),
        ("padding", None, "Padding. Calculated if None."),
        ("foreground", "ffffff", "Foreground colour"),
        (
            "fontshadow",
            None,
            "font shadow color, default is None(no shadow)"
        ),
    ]

    def __init__(self, text=" ", width=bar.CALCULATED, **config):
        self.layout = None
        _Widget.__init__(self, width, **config)
        self.text = text
        self.add_defaults(_TextBox.defaults)

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, value):
        self._text = value
        if self.layout:
            self.layout.text = value

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
            self.text,
            self.foreground,
            self.font,
            self.fontsize,
            self.fontshadow,
        )

    def calculate_width(self):
        if self.text:
            return min(
                self.layout.width,
                self.bar.width
            ) + self.actual_padding * 2
        else:
            return 0

    def draw(self):
        self.drawer.clear(self.background or self.bar.background)
        self.layout.draw(
            self.actual_padding or 0,
            int(self.bar.height / 2.0 - self.layout.height / 2.0) + 1
        )
        self.drawer.draw(self.offset, self.width)

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


class InLoopPollText(_TextBox):
    """ A common interface for polling some 'fast' information, munging it, and
    rendering the result in a text box. You probably want to use
    ThreadedPollText instead.

    ('fast' here means that this runs /in/ the event loop, so don't block! If
    you want to run something nontrivial, use ThreadedPollWidget.) """

    defaults = [
        ("update_interval", 600, "Update interval in seconds, if none, the "
            "widget updates whenever the event loop is idle."),
    ]

    def __init__(self, **config):
        _TextBox.__init__(self, 'N/A', width=bar.CALCULATED, **config)
        self.add_defaults(InLoopPollText.defaults)

    def _configure(self, qtile, bar):
        self.qtile = qtile
        if not self.configured:
            if self.update_interval is None:
                gobject.idle_add(self.tick)
            else:
                self.timeout_add(self.update_interval, self.tick)
        _TextBox._configure(self, qtile, bar)

        # Update when we are configured.
        self.tick()

    def button_press(self, x, y, button):
        self.tick()

    def poll(self):
        return 'N/A'

    def _poll(self):
        try:
            return self.poll()
        except:
            self.log.exception('got exception while polling')

    def tick(self):
        text = self._poll()
        self.update(text)
        return True

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
        return False


class ThreadedPollText(InLoopPollText):
    """ A common interface for polling some REST URL, munging the data, and
    rendering the result in a text box. """
    def __init__(self, **config):
        InLoopPollText.__init__(self, **config)

    def tick(self):
        def worker():
            text = self._poll()
            gobject.idle_add(self.update, text)
        threading.Thread(target=worker).start()
        return True

# these two classes below look SUSPICIOUSLY similar

class PaddingMixin(object):
    """
        Mixin that provides padding(_x|_y|)

        To use it, subclass and add this to __init__:

            self.add_defaults(base.PaddingMixin.defaults)
    """

    defaults = [
        ("padding", 3, "Padding inside the box"),
        ("padding_x", None, "X Padding. Overrides 'padding' if set"),
        ("padding_y", None, "Y Padding. Overrides 'padding' if set"),
    ]

    padding_x = configurable.ExtraFallback('padding_x', 'padding')
    padding_y = configurable.ExtraFallback('padding_y', 'padding')


class MarginMixin(object):
    """
        Mixin that provides margin(_x|_y|)

        To use it, subclass and add this to __init__:

            self.add_defaults(base.MarginMixin.defaults)
    """

    defaults = [
        ("margin", 3, "Margin inside the box"),
        ("margin_x", None, "X Margin. Overrides 'margin' if set"),
        ("margin_y", None, "Y Margin. Overrides 'margin' if set"),
    ]

    margin_x = configurable.ExtraFallback('margin_x', 'margin')
    margin_y = configurable.ExtraFallback('margin_y', 'margin')

def deprecated(msg):
    warnings.warn(msg, exceptions.DeprecationWarning)
