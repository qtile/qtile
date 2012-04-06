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

import manager, window, confreader, command, hook, drawer


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
        self.qtile, self.screen = None, None

    def _configure(self, qtile, screen):
        self.qtile, self.screen = qtile, screen

    @property
    def x(self):
        s = self.screen
        if s.right is self:
            return s.dx + s.dwidth
        else:
            return s.x

    @property
    def y(self):
        s = self.screen
        if s.top is self:
            return s.y
        elif s.bottom is self:
            return s.dy + s.dheight
        elif s.left is self:
            return s.dy
        elif s.right is self:
            return s.y + s.dy

    @property
    def width(self):
        s = self.screen
        if self in [s.top, s.bottom]:
            return s.width
        else:
            return self.size

    @property
    def height(self):
        s = self.screen
        if self in [s.top, s.bottom]:
            return self.size
        else:
            return s.dheight

    def geometry(self):
        return self.x, self.y, self.width, self.height

    def _items(self, name):
        if name == "screen":
            return True, None

    def _select(self, name, sel):
        if name == "screen":
            return self.screen

    @property
    def position(self):
        for i in ["top", "bottom", "left", "right"]:
            if getattr(self.screen, i) is self:
                return i

    def info(self):
        return dict(
            position=self.position
        )

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

class Bar(Gap):
    """
        A bar, which can contain widgets. Note that bars can only be placed at
        the top or bottom of the screen.
    """
    defaults = manager.Defaults(
        ("background", "#000000", "Background colour."),
        ("opacity",  1, "Bar window opacity.")
    )
    def __init__(self, widgets, size, **config):
        """
            - widgets: A list of widget objects.
            - size: The height of the bar.
        """
        Gap.__init__(self, size)
        self.widgets = widgets
        self.defaults.load(self, config)
        self.saved_focus = None

    def _configure(self, qtile, screen):
        if not self in [screen.top, screen.bottom]:
            raise confreader.ConfigError(
                    "Bars must be at the top or the bottom of the screen."
                  )
        if len(filter(lambda w: w.width_type == STRETCH, self.widgets)) > 1:
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
        qtile.windowMap[self.window.window.wid] = self.window
        self.window.unhide()

        for i in self.widgets:
            qtile.registerWidget(i)
            i._configure(qtile, self)

        # FIXME: These should be targeted better.
        hook.subscribe.setgroup(self.draw)
        hook.subscribe.delgroup(self.draw)
        hook.subscribe.addgroup(self.draw)

    def _resize(self, width, widgets):
        stretches = [i for i in widgets if i.width_type == STRETCH]
        if stretches:
            stretchspace = width - sum([i.width for i in widgets if i.width_type != STRETCH])
            stretchspace = max(stretchspace, 0)
            astretch = stretchspace/len(stretches)
            for i in stretches:
                i.width = astretch
            if astretch:
                i.width += stretchspace%astretch

        offset = 0
        for i in widgets:
            i.offset = offset
            offset += i.width

    def handle_Expose(self, e):
        self.draw()

    def handle_ButtonPress(self, e):
        for i in self.widgets:
            if e.event_x < i.offset + i.width:
                i.click(e.event_x - i.offset, e.event_y, e.detail)
                break

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
        if not self.saved_focus == None:
            self.saved_focus.window.set_input_focus()

    def draw(self):
        self._resize(self.width, self.widgets)
        for i in self.widgets:
            i.draw()
        if self.widgets:
            end = i.offset + i.width
            if end < self.width:
                self.drawer.draw(end, self.width-end)

    def info(self):
        return dict(
            width = self.width,
            position = self.position,
            widgets = [i.info() for i in self.widgets],
            window = self.window.window.wid
        )

    def cmd_fake_click(self, screen, position, x, y, button=1):
        """
            Fake a mouse-click on the bar. Co-ordinates are relative 
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
