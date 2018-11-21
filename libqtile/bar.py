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
from __future__ import division

from . import command
from . import confreader
from . import drawer
from . import configurable
from . import window


class Gap(command.CommandObject):
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
        # If both horizontal and vertical gaps are present, screen corners are
        # given to the horizontal ones
        if screen.top is self:
            self.x = screen.x
            self.y = screen.y
            self.length = screen.width
            self.width = self.length
            self.height = self.size
            self.horizontal = True
        elif screen.bottom is self:
            self.x = screen.x
            self.y = screen.dy + screen.dheight
            self.length = screen.width
            self.width = self.length
            self.height = self.size
            self.horizontal = True
        elif screen.left is self:
            self.x = screen.x
            self.y = screen.dy
            self.length = screen.dheight
            self.width = self.size
            self.height = self.length
            self.horizontal = False
        else:  # right
            self.x = screen.dx + screen.dwidth
            self.y = screen.dy
            self.length = screen.dheight
            self.width = self.size
            self.height = self.length
            self.horizontal = False

    def draw(self):
        pass

    def finalize(self):
        pass

    def geometry(self):
        return (self.x, self.y, self.width, self.height)

    def _items(self, name):
        if name == "screen":
            return (True, None)

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


class Obj(object):
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
    ]

    def __init__(self, widgets, size, **config):
        Gap.__init__(self, size)
        configurable.Configurable.__init__(self, **config)
        self.add_defaults(Bar.defaults)
        self.widgets = widgets
        self.saved_focus = None

        self.queued_draws = 0

    def _configure(self, qtile, screen):
        Gap._configure(self, qtile, screen)

        stretches = 0
        for w in self.widgets:
            # Executing _test_orientation_compatibility later, for example in
            # the _configure() method of each widget, would still pass
            # test/test_bar.py but a segfault would be raised when nosetests is
            # about to exit
            w._test_orientation_compatibility(self.horizontal)
            if w.length_type == STRETCH:
                stretches += 1
        if stretches > 1:
            raise confreader.ConfigError("Only one STRETCH widget allowed!")

        self.window = window.Internal.create(
            self.qtile,
            self.x, self.y, self.width, self.height,
            self.opacity
        )

        self.drawer = drawer.Drawer(
            self.qtile,
            self.window.window.wid,
            self.width,
            self.height
        )
        self.drawer.clear(self.background)

        self.window.handle_Expose = self.handle_Expose
        self.window.handle_ButtonPress = self.handle_ButtonPress
        self.window.handle_ButtonRelease = self.handle_ButtonRelease
        qtile.windowMap[self.window.window.wid] = self.window
        self.window.unhide()

        for i in self.widgets:
            qtile.register_widget(i)
            i._configure(qtile, self)
        self._resize(self.length, self.widgets)

    def finalize(self):
        self.drawer.finalize()

    def _resize(self, length, widgets):
        stretches = [i for i in widgets if i.length_type == STRETCH]
        if stretches:
            stretchspace = length - sum(
                [i.length for i in widgets if i.length_type != STRETCH]
            )
            stretchspace = max(stretchspace, 0)
            astretch = stretchspace // len(stretches)
            for i in stretches:
                i.length = astretch
            if astretch:
                i.length += stretchspace % astretch

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

    def handle_Expose(self, e):
        self.draw()

    def get_widget_in_position(self, e):
        if self.horizontal:
            for i in self.widgets:
                if e.event_x < i.offsetx + i.length:
                    return i
        else:
            for i in self.widgets:
                if e.event_y < i.offsety + i.length:
                    return i

    def handle_ButtonPress(self, e):
        widget = self.get_widget_in_position(e)
        if widget:
            widget.button_press(
                e.event_x - widget.offsetx,
                e.event_y - widget.offsety,
                e.detail
            )

    def handle_ButtonRelease(self, e):
        widget = self.get_widget_in_position(e)
        if widget:
            widget.button_release(
                e.event_x - widget.offsetx,
                e.event_y - widget.offsety,
                e.detail
            )

    def widget_grab_keyboard(self, widget):
        """
            A widget can call this method to grab the keyboard focus
            and receive keyboard messages. When done,
            widget_ungrab_keyboard() must be called.
        """
        self.window.handle_KeyPress = widget.handle_KeyPress
        self.saved_focus = self.qtile.current_window
        self.window.window.set_input_focus()

    def widget_ungrab_keyboard(self):
        """
            Removes the widget's keyboard handler.
        """
        del self.window.handle_KeyPress
        if self.saved_focus is not None:
            self.saved_focus.window.set_input_focus()

    def draw(self):
        if self.queued_draws == 0:
            self.qtile.call_soon(self._actual_draw)
        self.queued_draws += 1

    def _actual_draw(self):
        self.queued_draws = 0
        self._resize(self.length, self.widgets)
        for i in self.widgets:
            i.draw()
        if self.widgets:
            end = i.offset + i.length
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
            window=self.window.window.wid
        )

    def is_show(self):
        return self.size != 0

    def show(self, is_show=True):
        if is_show != self.is_show():
            if is_show:
                self.size = self.initial_size
                self.window.unhide()
            else:
                self.size = 0
                self.window.hide()

    def cmd_fake_button_press(self, screen, position, x, y, button=1):
        """
            Fake a mouse-button-press on the bar. Co-ordinates are relative
            to the top-left corner of the bar.

            :screen The integer screen offset
            :position One of "top", "bottom", "left", or "right"
        """
        class _Fake(object):
            pass
        fake = _Fake()
        fake.event_x = x
        fake.event_y = y
        fake.detail = button
        self.handle_ButtonPress(fake)
