# Copyright (c) 2008, Aldo Cortesi. All rights reserved.
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

import typing

from libqtile import configurable
from libqtile.command.base import CommandObject, ItemT
from libqtile.log_utils import logger
from libqtile.utils import has_transparency

if typing.TYPE_CHECKING:
    from libqtile.widget.base import _Widget


class Gap(CommandObject):
    """A gap placed along one of the edges of the screen

    If a gap has been defined, Qtile will avoid covering it with windows. The
    most probable reason for configuring a gap is to make space for a
    third-party bar or other static window.

    Parameters
    ==========
    size :
        The "thickness" of the gap, i.e. the height of a horizontal gap, or the
        width of a vertical gap.
    """
    def __init__(self, size):
        """
        """
        # 'size' corresponds to the height of a horizontal gap, or the width
        # of a vertical gap
        self.size = size
        self.initial_size = size
        # 'length' corresponds to the width of a horizontal gap, or the height
        # of a vertical gap
        self.length = None
        self.qtile = None
        self.screen = None
        self.x = None
        self.y = None
        self.width = None
        self.height = None
        self.horizontal = None

    def _configure(self, qtile, screen):
        self.qtile = qtile
        self.screen = screen
        self.size = self.initial_size
        # If both horizontal and vertical gaps are present, screen corners are
        # given to the horizontal ones
        if screen.top is self:
            self.x = screen.x
            self.y = screen.y
            self.length = screen.width
            self.width = self.length
            self.height = self.initial_size
            self.horizontal = True
        elif screen.bottom is self:
            self.x = screen.x
            self.y = screen.dy + screen.dheight
            self.length = screen.width
            self.width = self.length
            self.height = self.initial_size
            self.horizontal = True
        elif screen.left is self:
            self.x = screen.x
            self.y = screen.dy
            self.length = screen.dheight
            self.width = self.initial_size
            self.height = self.length
            self.horizontal = False
        else:  # right
            self.x = screen.dx + screen.dwidth
            self.y = screen.dy
            self.length = screen.dheight
            self.width = self.initial_size
            self.height = self.length
            self.horizontal = False

    def draw(self):
        pass

    def finalize(self):
        pass

    def geometry(self):
        return (self.x, self.y, self.width, self.height)

    def _items(self, name: str) -> ItemT:
        if name == "screen" and self.screen is not None:
            return True, []
        return None

    def _select(self, name, sel):
        if name == "screen":
            return self.screen

    @property
    def position(self):
        for i in ["top", "bottom", "left", "right"]:
            if getattr(self.screen, i) is self:
                return i

    def info(self):
        return dict(position=self.position)

    def cmd_info(self):
        """
            Info for this object.
        """
        return self.info()


class Obj:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name


STRETCH = Obj("STRETCH")
CALCULATED = Obj("CALCULATED")
STATIC = Obj("STATIC")


class Bar(Gap, configurable.Configurable):
    """A bar, which can contain widgets

    Parameters
    ==========
    widgets :
        A list of widget objects.
    size :
        The "thickness" of the bar, i.e. the height of a horizontal bar, or the
        width of a vertical bar.
    """
    defaults = [
        ("background", "#000000", "Background colour."),
        ("opacity", 1, "Bar window opacity."),
        ("margin", 0, "Space around bar as int or list of ints [N E S W]."),
    ]

    def __init__(self, widgets, size, **config):
        Gap.__init__(self, size)
        configurable.Configurable.__init__(self, **config)
        self.add_defaults(Bar.defaults)
        self.widgets = widgets
        self.saved_focus = None
        self.cursor_in = None
        self.window = None
        self.size_calculated = 0
        self._configured = False

        self.queued_draws = 0

    def _configure(self, qtile, screen):
        Gap._configure(self, qtile, screen)

        if self.margin:
            if isinstance(self.margin, int):
                self.margin = [self.margin] * 4
            if self.horizontal:
                self.x += self.margin[3]
                self.width -= self.margin[1] + self.margin[3]
                self.length = self.width
                if self.size == self.initial_size:
                    self.size += self.margin[0] + self.margin[2]
                if self.screen.top is self:
                    self.y += self.margin[0]
                else:
                    self.y -= self.margin[2]
            else:
                self.y += self.margin[0]
                self.height -= self.margin[0] + self.margin[2]
                self.length = self.height
                self.size += self.margin[1] + self.margin[3]
                if self.screen.left is self:
                    self.x += self.margin[3]
                else:
                    self.x -= self.margin[1]

        for w in self.widgets:
            # Executing _test_orientation_compatibility later, for example in
            # the _configure() method of each widget, would still pass
            # test/test_bar.py but a segfault would be raised when nosetests is
            # about to exit
            w._test_orientation_compatibility(self.horizontal)

        if self.window:
            # We get _configure()-ed with an existing window when screens are getting
            # reconfigured but this screen is present both before and after
            self.window.place(self.x, self.y, self.width, self.height, 0, None)
        else:
            # Whereas we won't have a window if we're startup up for the first time or
            # the window has been killed by us no longer using the bar's screen

            # X11 only:
            # To preserve correct display of SysTray widget, we need a 24-bit
            # window where the user requests an opaque bar.
            if self.qtile.core.name == "x11":
                depth = 32 if has_transparency(self.background) else self.qtile.core.conn.default_screen.root_depth

                self.window = self.qtile.core.create_internal(
                    self.x, self.y, self.width, self.height, depth
                )

            else:
                self.window = self.qtile.core.create_internal(
                    self.x, self.y, self.width, self.height
                )

            self.window.opacity = self.opacity
            self.window.unhide()

            self.drawer = self.window.create_drawer(self.width, self.height)
            self.drawer.clear(self.background)

            self.window.process_window_expose = self.draw
            self.window.process_button_click = self.process_button_click
            self.window.process_button_release = self.process_button_release
            self.window.process_pointer_enter = self.process_pointer_enter
            self.window.process_pointer_leave = self.process_pointer_leave
            self.window.process_pointer_motion = self.process_pointer_motion
            self.window.process_key_press = self.process_key_press

        self.crashed_widgets = []
        if self._configured:
            for i in self.widgets:
                self._configure_widget(i)
        else:
            for idx, i in enumerate(self.widgets):
                if i.configured:
                    i = i.create_mirror()
                    self.widgets[idx] = i
                success = self._configure_widget(i)
                if success:
                    qtile.register_widget(i)

        self._remove_crashed_widgets()
        self.draw()
        self._resize(self.length, self.widgets)
        self._configured = True

    def _configure_widget(self, widget):
        configured = True
        try:
            widget._configure(self.qtile, self)
            widget.configured = True
        except Exception as e:
            logger.error(
                "{} widget crashed during _configure with "
                "error: {}".format(widget.__class__.__name__, repr(e))
            )
            self.crashed_widgets.append(widget)
            configured = False

        return configured

    def _remove_crashed_widgets(self):
        if self.crashed_widgets:
            from libqtile.widget.config_error import ConfigErrorWidget

        for i in self.crashed_widgets:
            index = self.widgets.index(i)
            crash = ConfigErrorWidget(widget=i)
            crash._configure(self.qtile, self)
            self.widgets.insert(index, crash)
            self.widgets.remove(i)

    def _items(self, name: str) -> ItemT:
        if name == "screen" and self.screen is not None:
            return True, []
        elif name == "widget" and self.widgets:
            return False, [w.name for w in self.widgets]
        return None

    def _select(self, name, sel):
        if name == "screen":
            return self.screen
        elif name == "widget":
            for widget in self.widgets:
                if widget.name == sel:
                    return widget
        return None

    def finalize(self):
        self.drawer.finalize()

    def kill_window(self):
        """Kill the window when the bar's screen is no longer being used."""
        self.drawer.finalize()
        self.window.kill()
        self.window = None

    def _resize(self, length, widgets):
        stretches = [i for i in widgets if i.length_type == STRETCH]
        if stretches:
            stretchspace = length - sum(
                [i.length for i in widgets if i.length_type != STRETCH]
            )
            stretchspace = max(stretchspace, 0)
            num_stretches = len(stretches)
            if num_stretches == 1:
                stretches[0].length = stretchspace
            else:
                block = 0
                blocks = []
                for i in widgets:
                    if i.length_type != STRETCH:
                        block += i.length
                    else:
                        blocks.append(block)
                        block = 0
                if block:
                    blocks.append(block)
                interval = length // num_stretches
                for idx, i in enumerate(stretches):
                    if idx == 0:
                        i.length = interval - blocks[0] - blocks[1] // 2
                    elif idx == num_stretches - 1:
                        i.length = interval - blocks[-1] - blocks[-2] // 2
                    else:
                        i.length = int(interval - blocks[idx] / 2 - blocks[idx + 1] / 2)
                    stretchspace -= i.length
                stretches[0].length += stretchspace // 2
                stretches[-1].length += stretchspace - stretchspace // 2

        offset = 0
        if self.horizontal:
            for i in widgets:
                i.offsetx = offset
                i.offsety = 0
                offset += i.length
        else:
            for i in widgets:
                i.offsetx = 0
                i.offsety = offset
                offset += i.length

    def get_widget_in_position(self, x: int, y: int) -> typing.Optional[_Widget]:
        if self.horizontal:
            for i in self.widgets:
                if x < i.offsetx + i.length:
                    return i
        else:
            for i in self.widgets:
                if y < i.offsety + i.length:
                    return i
        return None

    def process_button_click(self, x: int, y: int, button: int) -> None:
        widget = self.get_widget_in_position(x, y)
        if widget:
            widget.button_press(
                x - widget.offsetx,
                y - widget.offsety,
                button,
            )

    def process_button_release(self, x: int, y: int, button: int) -> None:
        widget = self.get_widget_in_position(x, y)
        if widget:
            widget.button_release(
                x - widget.offsetx,
                y - widget.offsety,
                button,
            )

    def process_pointer_enter(self, x: int, y: int) -> None:
        widget = self.get_widget_in_position(x, y)
        if widget:
            widget.mouse_enter(
                x - widget.offsetx,
                y - widget.offsety,
            )
        self.cursor_in = widget

    def process_pointer_leave(self, x: int, y: int) -> None:
        if self.cursor_in:
            self.cursor_in.mouse_leave(
                x - self.cursor_in.offsetx,
                y - self.cursor_in.offsety,
            )
            self.cursor_in = None

    def process_pointer_motion(self, x: int, y: int) -> None:
        widget = self.get_widget_in_position(x, y)
        if widget and self.cursor_in and widget is not self.cursor_in:
            self.cursor_in.mouse_leave(
                x - self.cursor_in.offsetx,
                y - self.cursor_in.offsety,
            )
            widget.mouse_enter(
                x - widget.offsetx,
                y - widget.offsety,
            )
        self.cursor_in = widget

    def process_key_press(self, keycode: int) -> None:
        if self.has_keyboard:
            self.has_keyboard.process_key_press(keycode)

    def widget_grab_keyboard(self, widget):
        """
            A widget can call this method to grab the keyboard focus
            and receive keyboard messages. When done,
            widget_ungrab_keyboard() must be called.
        """
        self.has_keyboard = widget
        self.saved_focus = self.qtile.current_window
        self.window.focus(False)

    def widget_ungrab_keyboard(self):
        """
            Removes keyboard focus from the widget.
        """
        if self.saved_focus is not None:
            self.saved_focus.focus(False)
        self.has_keyboard = None

    def draw(self):
        if not self.widgets:
            return  # calling self._actual_draw in this case would cause a NameError.
        if self.queued_draws == 0:
            self.qtile.call_soon(self._actual_draw)
        self.queued_draws += 1

    def _actual_draw(self):
        self.queued_draws = 0
        self._resize(self.length, self.widgets)
        for i in self.widgets:
            i.draw()
        end = i.offset + i.length  # pylint: disable=undefined-loop-variable
        # we verified that self.widgets is not empty in self.draw(), see above.
        if end < self.length:
            if self.horizontal:
                self.drawer.draw(offsetx=end, width=self.length - end)
            else:
                self.drawer.draw(offsety=end, height=self.length - end)

    def info(self):
        return dict(
            size=self.size,
            length=self.length,
            width=self.width,
            height=self.height,
            position=self.position,
            widgets=[i.info() for i in self.widgets],
            window=self.window.wid
        )

    def is_show(self):
        return self.size != 0

    def show(self, is_show=True):
        if is_show != self.is_show():
            if is_show:
                self.size = self.size_calculated
                self.window.unhide()
            else:
                self.size_calculated = self.size
                self.size = 0
                self.window.hide()
            self.screen.group.layout_all()

    def adjust_for_strut(self, size):
        if self.size:
            self.size = self.initial_size
        if not self.margin:
            self.margin = [0, 0, 0, 0]
        if self.screen.top is self:
            self.margin[0] += size
        elif self.screen.bottom is self:
            self.margin[2] += size
        elif self.screen.left is self:
            self.margin[3] += size
        else:  # right
            self.margin[1] += size

    def cmd_fake_button_press(self, screen, position, x, y, button=1):
        """
            Fake a mouse-button-press on the bar. Co-ordinates are relative
            to the top-left corner of the bar.

            :screen The integer screen offset
            :position One of "top", "bottom", "left", or "right"
        """
        self.process_button_click(x, y, button)


BarType = typing.Union[Bar, Gap]
