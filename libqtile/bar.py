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
from . import hook
from . import configurable
from . import window

from six.moves import gobject

USE_BAR_DRAW_QUEUE = True

class Gap(command.CommandObject):
    """
        A gap, placed along one of the edges of the screen. If a gap has been
        defined, Qtile will avoid covering it with windows. The most probable
        reason for configuring a gap is to make space for a third-party bar or
        other static window.
    """
    def __init__(self, size):
        """
            size: The width of the gap.
        """
        self.size = size
        self.qtile = None
        self.screen = None

    def _configure(self, qtile, screen):
        self.qtile = qtile
        self.screen = screen

    def draw(self):
        pass

    @property
    def x(self):
        screen = self.screen
        if screen.right is self:
            return screen.dx + screen.dwidth
        else:
            return screen.x

    @property
    def y(self):
        screen = self.screen
        if screen.top is self:
            return screen.y
        elif screen.bottom is self:
            return screen.dy + screen.dheight
        elif screen.left is self:
            return screen.dy
        elif screen.right is self:
            return screen.y + screen.dy

    @property
    def width(self):
        screen = self.screen
        if self in [screen.top, screen.bottom]:
            return screen.width
        else:
            return self.size

    @property
    def height(self):
        screen = self.screen
        if self in [screen.top, screen.bottom]:
            return self.size
        else:
            return screen.dheight

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
    """
        A bar, which can contain widgets. Note that bars can only be placed at
        the top or bottom of the screen.
    """
    defaults = [
        ("background", "#000000", "Background colour."),
        ("opacity", 1, "Bar window opacity."),
    ]

    def __init__(self, widgets, size, **config):
        """
            - widgets: A list of widget objects.
            - size: The height of the bar.
        """
        Gap.__init__(self, size)
        configurable.Configurable.__init__(self, **config)
        self.add_defaults(Bar.defaults)
        self.widgets = widgets
        self.saved_focus = None

        self.queued_draws = 0

    def _configure(self, qtile, screen):
        if self not in [screen.top, screen.bottom]:
            raise confreader.ConfigError(
                "Bars must be at the top or the bottom of the screen."
            )
        if len([w for w in self.widgets if w.width_type == STRETCH]) > 1:
            raise confreader.ConfigError("Only one STRETCH widget allowed!")

        Gap._configure(self, qtile, screen)
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
            qtile.registerWidget(i)
            i._configure(qtile, self)
        self._resize(self.width, self.widgets)

        # FIXME: These should be targeted better.
        hook.subscribe.setgroup(self.draw)
        hook.subscribe.changegroup(self.draw)

    def _resize(self, width, widgets):
        stretches = [i for i in widgets if i.width_type == STRETCH]
        if stretches:
            stretchspace = width - sum(
                [i.width for i in widgets if i.width_type != STRETCH]
            )
            stretchspace = max(stretchspace, 0)
            astretch = stretchspace // len(stretches)
            for i in stretches:
                i.width = astretch
            if astretch:
                i.width += stretchspace % astretch

        offset = 0
        for i in widgets:
            i.offset = offset
            offset += i.width

    def handle_Expose(self, e):
        self.draw()

    def get_widget_in_position(self, e):
        for i in self.widgets:
            if e.event_x < i.offset + i.width:
                return i

    def handle_ButtonPress(self, e):
        widget = self.get_widget_in_position(e)
        if widget:
            widget.button_press(
                e.event_x - widget.offset,
                e.event_y,
                e.detail
            )

    def handle_ButtonRelease(self, e):
        widget = self.get_widget_in_position(e)
        if widget:
            widget.button_release(
                e.event_x - widget.offset,
                e.event_y,
                e.detail
            )

    def widget_grab_keyboard(self, widget):
        """
            A widget can call this method to grab the keyboard focus
            and receive keyboard messages. When done,
            widget_ungrab_keyboard() must be called.
        """
        self.window.handle_KeyPress = widget.handle_KeyPress
        self.saved_focus = self.qtile.currentWindow
        self.window.window.set_input_focus()

    def widget_ungrab_keyboard(self):
        """
            Removes the widget's keyboard handler.
        """
        del self.window.handle_KeyPress
        if self.saved_focus is not None:
            self.saved_focus.window.set_input_focus()

    def draw(self):
        if USE_BAR_DRAW_QUEUE:
            if self.queued_draws == 0:
                gobject.idle_add(self._actual_draw)
            self.queued_draws += 1
        else:
            self._actual_draw()

    def _actual_draw(self):
        self.queued_draws = 0
        self._resize(self.width, self.widgets)
        for i in self.widgets:
            i.draw()
        if self.widgets:
            end = i.offset + i.width
            if end < self.width:
                self.drawer.draw(end, self.width - end)

        # have to return False here to avoid getting called again
        return False

    def info(self):
        return dict(
            width=self.width,
            position=self.position,
            widgets=[i.info() for i in self.widgets],
            window=self.window.window.wid
        )

    def cmd_fake_button_press(self, screen, position, x, y, button=1):
        """
            Fake a mouse-button-press on the bar. Co-ordinates are relative
            to the top-left corner of the bar.

            :screen The integer screen offset
            :position One of "top", "bottom", "left", or "right"
        """
        class _fake:
            pass
        fake = _fake()
        fake.event_x = x
        fake.event_y = y
        fake.detail = button
        self.handle_ButtonPress(fake)
