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

import math
import os

import cairocffi

from libqtile import configurable, pangocffi
from libqtile.images import Img
from libqtile.log_utils import logger
from libqtile.popup import Popup


class _PopupLayout(configurable.Configurable):
    """
    This is the base class for a 2D popup layout that displays additional
    information/controls for widgets on the user's bar.

    As a bare minimum, the tooltip requires width and height and a list of
    "controls" that should be displayed within the tooltip.

    Note: It is currently envisaged that Popups will have a fixed size unlike
    widgets which are able to have variable sizes.
    """

    defaults = [
        ("width", 200, "Width of tooltip"),
        ("height", 200, "Height of tooltip"),
        ("controls", [], "Controls to display"),
        ("margin", 5, "Margin around edge of tooltip"),
        ("background", "000000", "Popup background colour"),
        ("opacity", 1, "Popup window opacity. 'None' inherits bar opacity"),
        ("close_on_click", True, "Hide the popup when control is clicked")
    ]

    def __init__(self, qtile, **config):
        configurable.Configurable.__init__(self, **config)
        self.add_defaults(_PopupLayout.defaults)

        self.qtile = qtile

        # Define drawable area
        self._width = self.width - 2 * self.margin
        self._height = self.height - 2 * self.margin

        # Keep track of which control the mouse is over
        self.cursor_in = None

        self.configured = False

    def _configure(self):
        """
        This method creates an instances of a Popup window which serves as the
        base for the tooltip.

        We also attach handlers for mouse events so that these can be passed to
        the relevant controls.
        """
        self.popup = Popup(self.qtile,
                           width=self.width,
                           height=self.height,
                           background=self.background,
                           opacity=self.opacity)

        self.popup.win.info = self.info

        self.popup.win.process_button_click = self.process_button_click
        self.popup.win.process_button_release = self.process_button_release
        self.popup.win.process_pointer_enter = self.process_pointer_enter
        self.popup.win.process_pointer_leave = self.process_pointer_leave
        self.popup.win.process_pointer_motion = self.process_pointer_motion

        for c in self.controls:
            self._place_control(c)
            c._configure(self.qtile, self)

        self.configured = True

    def _place_control(self, control):
        """
        This method should define the offsets and positions for the control.

        Layous therefore need to override this method with the specific rules
        for that layout.
        """
        pass

    def draw(self):
        """
        Assuming popup is a fixed size, we can just draw widgets without
        re-positioning them.
        """
        self.popup.clear()
        for c in self.controls:
            c.drawer.ctx.save()
            c.drawer.ctx.translate(c.offsetx, c.offsety)
            c.paint()
            c.drawer.ctx.restore()
        self.popup.draw()

    def show(self, x=0, y=0, centered=False, warp_pointer=False):
        """Display the popup. Can be centered on screen."""
        if not self.configured:
            self._configure()
        if centered:
            x = int((self.qtile.current_screen.width - self.popup.width) / 2)
            y = int((self.qtile.current_screen.height - self.popup.height) / 2)
        self.popup.x = x
        self.popup.y = y
        self.popup.place()
        self.popup.unhide()
        self.draw()

        if warp_pointer:
            self.qtile.core.warp_pointer(
                self.popup.x + self.popup.width // 2,
                self.popup.y + self.popup.height // 2
            )

    def hide(self):
        """Hide the popup."""
        self.popup.hide()

    def kill(self):
        self.popup.kill()

    # The below methods are lifted from `bar`
    def get_control_in_position(self, x, y):
        for c in self.controls:
            if c.mouse_in_control(x, y):
                return c
        return None

    def process_button_click(self, x, y, button):  # noqa: N802
        control = self.get_control_in_position(x, y)
        if control:
            control.button_press(
                x - control.offsetx,
                y - control.offsety,
                button
            )
        if self.close_on_click:
            self.kill()

    def process_button_release(self, x, y, button):  # noqa: N802
        control = self.get_control_in_position(x, y)
        if control:
            control.button_release(
                x - control.offsetx,
                y - control.offsety,
                button
            )

    def process_pointer_enter(self, x, y):  # noqa: N802
        control = self.get_control_in_position(x, y)
        if control:
            control.mouse_enter(
                x - control.offsetx,
                y - control.offsety,
            )
        self.cursor_in = control

    def process_pointer_leave(self, x, y):  # noqa: N802
        if self.cursor_in:
            self.cursor_in.mouse_leave(
                x - self.cursor_in.offsetx,
                y - self.cursor_in.offsety,
            )
            self.cursor_in = None

    def process_pointer_motion(self, x, y):  # noqa: N802
        control = self.get_control_in_position(x, y)
        if self.cursor_in and control is not self.cursor_in:
            self.cursor_in.mouse_leave(
                x - self.cursor_in.offsetx,
                y - self.cursor_in.offsety,
            )
        if control:
            control.mouse_enter(
                x - control.offsetx,
                y - control.offsety,
            )

        self.cursor_in = control

    def info(self):
        return {
            "name": self.__class__.__name__.lower(),
            "x": self.popup.x,
            "y": self.popup.y,
            "width": self.popup.width,
            "height": self.popup.height,
            "controls": [
                control.info() for control in self.controls
            ]
        }


class PopupGridLayout(_PopupLayout):
    """
    The grid layout should be familiar to users who have used Tkinter.

    In addition to the `width` and `height` attributes, the grid layout also
    requires `rows` and `cols` to define the grid. Grid cells are evenly sized.a

    Controls can then be placed in the grid via the `row`, `col`, `row_span` and
    `col_span` parameters.

    For example:

    ::

        PopupGridLayout(rows=6, cols=6, controls=[
            PopupImage(filename="A",row=0, col=2, row_span=2, col_span=2),
            PopupImage(filename="B",row=2, col=2, row_span=2, col_span=2),
            PopupImage(filename="C",row=3, col=1),
            PopupImage(filename="D",row=3, col=4),
            PopupText(row=4,col_span=6),
        ])

    would result in a tooltip looking like:

    ::

        -------------------------
        |   |   |       |   |   |
        ---------   A   ---------
        |   |   |       |   |   |
        -------------------------
        |   |   |       |   |   |
        ---------   B   ---------
        |   | C |       | D |   |
        -------------------------
        |         TEXT          |
        -------------------------
        |   |   |   |   |   |   |
        -------------------------

    row and col are both zero-indexed.
    """
    defaults = [
        ("rows", 2, "Number of rows in grid"),
        ("cols", 2, "Number of columns in grid")
    ]

    def __init__(self, qtile, **config):
        _PopupLayout.__init__(self, qtile, **config)
        self.add_defaults(PopupGridLayout.defaults)
        self._width = self.rows * round((self.width - 2 * self.margin) / self.rows)
        self._height = self.cols * round((self.height - 2 * self.margin) / self.cols)
        self.width = self._width + 2 * self.margin
        self.height = self._height + 2 * self.margin
        self.col_width = self._width / self.cols
        self.row_height = self._height / self.rows

    def _place_control(self, control):
        if not control.placed:
            control.offsetx = int(control.col * self.col_width) + self.margin
            control.offsety = int(control.row * self.row_height) + self.margin
            control.width = int(control.col_span * self.col_width)
            control.height = int(control.row_span * self.row_height)
            control.placed = True


class PopupRelativeLayout(_PopupLayout):
    """
    The relative layout positions controls based on a percentage of the parent
    tooltip's dimensions.

    The positions are defined with the following parameters:

    ::

        `pos_x`, `pos_y`: top left corner
        `width`, `height`: size of control

    All four of these parameters should be a value between 0 and 1. Values
    outside of this range will generate a warning in the log but will not raise
    an exception.

    For example:

    ::

       PopupRelativeLayout(rows=6, cols=6, controls=[
           PopupImage(filename="A",pos_x=0.1, pos_y=0.2, width=0.5, height=0.5)
       ])

    Would result in a tooltip with dimensions of 200x200 (the default), with an
    image placed at (20, 40) with dimensions of (100, 100).

    Note: images are not stretched but are, instead, centered within the rect.
    """

    def _place_control(self, control):

        def is_relative(val):
            """
            Relative layout positions controls based on percentage of
            parent's size so check value is in range.
            """
            return 0 <= val <= 1

        if not control.placed:
            if not all([is_relative(x) for x in [control.pos_x,
                                                 control.pos_y,
                                                 control.width,
                                                 control.height]
                        ]):
                logger.warning("Control {} using non relative dimensions "
                               "in Relative layout".format(control))

            control.offsetx = int(self._width * control.pos_x) + self.margin
            control.offsety = int(self._height * control.pos_y) + self.margin
            control.width = int(self._width * control.width)
            control.height = int(self._height * control.height)
            control.placed = True


class PopupAbsoluteLayout(_PopupLayout):
    """
    The absolute layout is the simplest layout of all. Controls are placed based
    on the following parameters:

    ::

        `pos_x`, `pos_y`: top left corner
        `width`, `height`: size of control

    No further adjustments are made to the controls.

    Note: the layout currently ignores the `margin` attribute i.e. a control
    placed at (0,0) will display there even if a margin is defined.
    """
    def _place_control(self, control):
        if not control.placed:
            control.offsetx = control.pos_x
            control.offsety = control.pos_y
            control.placed = True


class _PopupWidget(configurable.Configurable):
    """
    Base class for controls to be included in tooltip windows.

    This draws heavily on the `base._Widget` class but includes additional
    defaults to allow for positioning within a 2D space.
    """

    defaults = [
        ("width", 50, "width of control"),
        ("height", 50, "height of control"),
        ("pos_x", 0, "x position of control"),
        ("pos_y", 0, "y position of control"),
        ("row", 0, "Row position (for grid layout)"),
        ("col", 0, "Column position (for grid layout)"),
        ("row_span", 1, "Number of rows covered by control"),
        ("col_span", 1, "Number of columns covered by control"),
        ("background", None, "Background colour for control"),
        ("highlight", "#006666", "Highlight colour"),
        ("hover", False, "Highlight if mouse over control"),
        ("mouse_callbacks", {}, "Dict of mouse button press callback functions.")
    ]

    offsetx = None
    offsety = None

    def __init__(self, **config):
        configurable.Configurable.__init__(self, **config)
        self.add_defaults(_PopupWidget.defaults)
        self._highlight = False
        self.placed = False

    def _configure(self, qtile, container):
        self.qtile = qtile
        self.container = container
        self.drawer = container.popup.drawer

    def add_callbacks(self, defaults):
        """
        Add default callbacks with a lower priority than user-specified
        callbacks.
        """
        defaults.update(self.mouse_callbacks)
        self.mouse_callbacks = defaults

    def paint(self):
        raise NotImplementedError

    def clear(self, colour):
        if not colour:
            return
        self.drawer.set_source_rgb(colour)
        self.drawer.ctx.save()
        # TODO: OPERATOR_SOURCE replaces background with the new drawing
        # Consider whether OVERLAY is more appropriate (particularly with
        # transparency)
        self.drawer.ctx.set_operator(cairocffi.OPERATOR_SOURCE)
        self.drawer.ctx.rectangle(0, 0, self.width, self.height)
        self.drawer.ctx.fill()
        self.drawer.ctx.restore()

    @property
    def win(self):
        return self.container.popup.win

    @property
    def _background(self):
        """
        This property changes based on whether the `_highlight` variable has been
        set.
        """
        if self._highlight and self.highlight:
            return self.highlight
        else:
            return self.background

    def mouse_in_control(self, x, y):
        """Checks whether the point (x, y) is inside the control."""
        return all([
            x >= self.offsetx,
            x < self.width + self.offsetx,
            y >= self.offsety,
            y < self.height + self.offsety
        ])

    def button_press(self, x, y, button):
        name = 'Button{0}'.format(button)
        if name in self.mouse_callbacks:
            self.mouse_callbacks[name]()

    def button_release(self, x, y, button):
        pass

    def mouse_enter(self, x, y):
        if self.hover and self.highlight and not self._highlight:
            self._highlight = True
            self.container.draw()

    def mouse_leave(self, x, y):
        if self._highlight:
            self._highlight = False
            self.container.draw()

    def info(self):
        return {
            "name": self.__class__.__name__.lower(),
            "x": self.offsetx,
            "y": self.offsety,
            "width": self.width,
            "height": self.height,
        }


class PopupText(_PopupWidget):
    """Simple control to display text."""

    defaults = [
        ("font", "sans", "Font name"),
        ("fontsize", 12, "Font size"),
        ("foreground", "#ffffff", "Font colour"),
        ('text_alignment', 'left', 'Text alignment: left, center or right.'),
        ("wrap", False, "Wrap text in layout")
    ]

    def __init__(self, text="", **config):
        _PopupWidget.__init__(self, **config)
        self.add_defaults(PopupText.defaults)
        self._text = text

    def _configure(self, qtile, container):
        _PopupWidget._configure(self, qtile, container)
        self.layout = self.drawer.textlayout(
            self._text,
            self.foreground,
            self.font,
            self.fontsize,
            None,
            markup=False,
            wrap=self.wrap
        )
        self.layout.layout.set_alignment(pangocffi.ALIGNMENTS[self.text_alignment])
        self.layout.width = self.width

    def paint(self):
        # TODO: Vertical offset
        self.clear(self._background)
        self.layout.draw(0, 0)

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, val):
        self._text = val
        self.layout.text = self._text
        self.draw()

    def info(self):
        info = _PopupWidget.info(self)
        info["text"] = self.text
        return info


class PopupSlider(_PopupWidget):
    """
    Control to display slider/progress bar.

    Bar can be displayed horizontally (draws left-to-right) or vertically
    (bottom-to-top).
    """

    defaults = [
        ("min_value", 0, "Minimum value"),
        ("max_value", 1.0, "Maximum value"),
        ("horizontal", True, "Orientation. False = vertical"),
        ("colour_below", "#ffffff", "Colour for bar below value"),
        ("colour_above", "#888888", "Colour for bar above value"),
        ("bar_size", 2, "Thickness of bar"),
        ("marker_size", 10, "Size of marker"),
        ("marker_colour", "#bbbbbb", "Colour of marker"),
        ("end_margin", 5, "Gap between edge of control and ends of bar")
    ]

    def __init__(self, value=None, **config):
        _PopupWidget.__init__(self, **config)
        self.add_defaults(PopupSlider.defaults)
        self._value = self._check_value(value)

    def _check_value(self, val):
        if val is None or type(val) not in (int, float):
            return self.min_value
        return min(max(val, self.min_value), self.max_value)

    def _configure(self, qtile, container):
        _PopupWidget._configure(self, qtile, container)
        self.bar_length = self.length - 2 * self.end_margin

    def paint(self):
        self.clear(self._background)

        offset = int((self.depth - self.bar_size) / 2)

        ctx = self.drawer.ctx
        ctx.save()
        ctx.set_line_width(self.bar_size)

        if not self.horizontal:
            ctx.rotate(-90 * math.pi / 180.0)
            ctx.translate(- self.length, 0)

        ctx.translate(self.end_margin, offset)

        if self.percentage > 0:
            ctx.new_sub_path()
            self.drawer.set_source_rgb(self.colour_below)
            ctx.move_to(0, 0)
            ctx.line_to(self.bar_length * self.percentage, 0)
            ctx.stroke()

        if self.percentage < 1:
            ctx.new_sub_path()
            self.drawer.set_source_rgb(self.colour_above)
            ctx.move_to(self.bar_length * self.percentage, 0)
            ctx.line_to(self.bar_length, 0)
            ctx.stroke()

        if self.marker_size:
            self.drawer.set_source_rgb(self.marker_colour)
            ctx.arc(self.bar_length * self.percentage,
                    0,
                    self.marker_size / 2,
                    0,
                    math.pi * 2)
            ctx.fill()

        ctx.restore()

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, val):
        self._value = self._check_value(val)
        self.draw()

    @property
    def percentage(self):
        return (self.value - self.min_value) / (self.max_value - self.min_value)

    @property
    def length(self):
        if self.horizontal:
            return self.width
        else:
            return self.height

    @property
    def depth(self):
        if self.horizontal:
            return self.height
        else:
            return self.width

    def info(self):
        info = _PopupWidget.info(self)
        info["value"] = self.value
        return info


class PopupImage(_PopupWidget):
    """
    Control to display an image.

    Image will be scaled (locked aspect ratio) to fit within the control rect.
    The image will also be centered vertically and horizontally.
    """

    defaults = [
        ("filename", None, "path to image file.")
    ]

    def __init__(self, **config):
        _PopupWidget.__init__(self, **config)
        self.add_defaults(PopupImage.defaults)

    def _configure(self, qtile, container):
        _PopupWidget._configure(self, qtile, container)
        self.img = None
        self.load_image()

    def load_image(self):
        self.filename = os.path.expanduser(self.filename)

        if not os.path.exists(self.filename):
            logger.warning("Image does not exist: {}".format(self.filename))
            return

        img = Img.from_path(self.filename)
        self.img = img

        if (img.width / img.height) >= (self.width / self.height):
            self.img.scale(width_factor=(self.width / img.width), lock_aspect_ratio=True)
        else:
            self.img.scale(height_factor=(self.height / img.height), lock_aspect_ratio=True)

    def paint(self):
        self.drawer.clear(self._background or self.container.background)
        self.drawer.ctx.save()
        self.drawer.ctx.translate(int((self.width-self.img.width) / 2),
                                  int((self.height - self.img.height) / 2))
        self.drawer.ctx.set_source(self.img.pattern)
        self.drawer.ctx.paint()
        self.drawer.ctx.restore()

    def info(self):
        info = _PopupWidget.info(self)
        info["image"] = self.filename
        return info
