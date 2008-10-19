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

import sys
import manager, window, confreader, command, utils
import Xlib.X

_HIGHLIGHT = "#48677E"
_FOREGROUND = "#dddddd"

class Gap(command.CommandObject):
    def __init__(self, size):
        """
            :size The width of the gap.
        """
        self.size = size
        self.qtile, self.screen = None, None

    def _configure(self, qtile, screen, event):
        self.qtile, self.screen, self.event = qtile, screen, event

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
            return []

    def _select(self, name, sel):
        if name == "screen":
            if sel is None:
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
        return self.info()

STRETCH = -1
class Bar(Gap):
    background = "black"
    widgets = None
    window = None
    def __init__(self, widgets, size):
        """
            Note that bars can only be at the top or the bottom of the screen.
            
            widgets: A list of widget objects.
            size: The width of the bar.
        """
        Gap.__init__(self, size)
        self.widgets = widgets

    def _configure(self, qtile, screen, event):
        if not self in [screen.top, screen.bottom]:
            raise confreader.ConfigError("Bars must be at the top or the bottom of the screen.")
        Gap._configure(self, qtile, screen, event)
        colormap = qtile.display.screen().default_colormap
        c = colormap.alloc_named_color(self.background).pixel
        self.window = window.Internal.create(
                        self.qtile,
                        c,
                        self.x, self.y, self.width, self.height
                     )
        self.window.handle_Expose = self.handle_Expose
        self.window.handle_ButtonPress = self.handle_ButtonPress
        qtile.internalMap[self.window.window] = self.window
        self.window.unhide()

        for i in self.widgets:
            qtile.registerWidget(i)
            i._configure(qtile, self, event)
        self.resize()

    def resize(self):
        offset = 0
        stretchWidget = None
        for i in self.widgets:
            i.offset = offset
            if i.width == STRETCH:
                stretchWidget = i
                break
            offset += i.width
        total = offset
        offset = self.width
        if stretchWidget:
            for i in reversed(self.widgets):
                if i.width == STRETCH:
                    break
                offset -= i.width
                total += i.width
                i.offset = offset
            stretchWidget.width = self.width - total

    def handle_Expose(self, e):
        self.draw()

    def handle_ButtonPress(self, e):
        for i in self.widgets:
            if e.event_x < i.offset + i.width:
                i.click(e.event_x - i.offset, e.event_y)
                break

    def draw(self):
        for i in self.widgets:
            i.draw()

    def info(self):
        return dict(
            position = self.position,
            widgets = [i.info() for i in self.widgets],
            window = self.window.window.id
        )

    def get(self, q, screen, position):
        if len(q.screens) - 1 < screen:
            raise command.CommandError("No such screen: %s"%screen)
        s = q.screens[screen]
        b = getattr(s, position)
        if not b:
            raise command.CommandError("No such bar: %s:%s"%(screen, position))
        return b

    def cmd_fake_click(self, screen, position, x, y):
        """
            Fake a mouse-click on the bar. Co-ordinates are relative 
            to the top-left corner of the bar.

            :screen The integer screen offset
            :position One of "top", "bottom", "left", or "right"
        """
        class _fake: pass
        fake = _fake()
        fake.event_x = x
        fake.event_y = y
        self.handle_ButtonPress(fake)


LEFT = object()
CENTER = object()
class _Drawer:
    """
        A helper class for drawing and text layout.
    """
    _fallbackFont = "-*-fixed-bold-r-normal-*-15-*-*-*-c-*-*-*"
    def __init__(self, qtile, window):
        self.qtile, self.window = qtile, window
        self.win = window.window
        self.gc = self.win.create_gc()
        self.colormap = qtile.display.screen().default_colormap
        self.background, self.foreground = None, None
        
    @utils.LRUCache(100)
    def color(self, color):
        return self.colormap.alloc_named_color(color).pixel

    def setFont(self, font):
        f = self.qtile.display.open_font(font)
        if not f:
            self.qtile.log.add("Could not open font %s, falling back."%font)
            f = self.qtile.display.open_font(self._fallbackFont)
        self.font = f
        self.gc.change(font=f)

    @utils.LRUCache(100)
    def text_extents(self, font, i):
        return font.query_text_extents(i)

    def textsize(self, font, *text):
        """
            Return a textheight, textwidth tuple, for a box large enough to
            enclose any of the passed strings.
        """
        textheight, textwidth = 0, 0
        for i in text:
            data = self.text_extents(font, i)
            if  data.font_ascent > textheight:
                textheight = data.font_ascent
            if data.overall_width > textwidth:
                textwidth = data.overall_width
        return textheight, textwidth

    def change(self, **kwargs):
        newargs = kwargs.copy()
        newargs.pop("background", None)
        newargs.pop("foreground", None)
        if kwargs.has_key("background") and self.background != kwargs["background"]:
            self.background = kwargs["background"]
            newargs["background"] = self.color(kwargs["background"])
        if kwargs.has_key("foreground") and self.background != kwargs["foreground"]:
            self.background = kwargs["foreground"]
            newargs["foreground"] = self.color(kwargs["foreground"])
        if newargs:
            self.gc.change(**newargs)

    def textbox(self, text, x, y, width, height, padding = 0,
                alignment=LEFT, background=None, **attrs):
        """
            Draw text in the specified box using the current font. Text is
            centered vertically, and left-aligned. 
            
            :background Fill box with the specified color first.
            :padding  Padding to the left of the text.
        """
        text = text or " "
        if background:
            self.rectangle(x, y, width, height, background)
            attrs["background"] = background
        if attrs:
            self.change(**attrs)
        textheight, textwidth = self.textsize(self.font, text)
        y = y + textheight + (height - textheight)/2
        if alignment == LEFT:
            x = x + padding
        else:
            x = x + (width - textwidth)/2
        self.win.draw_text(self.gc, x, y, text)

    def rectangle(self, x, y, width, height, fillColor=None, borderColor=None, borderWidth=1):
        if fillColor:
            self.change(foreground=fillColor)
            self.win.fill_rectangle(self.gc, x, 0, width, height)
        if borderColor:
            self.change(
                foreground=borderColor,
                line_width=borderWidth
            )
            self.win.rectangle(self.gc, x, 0, width, height)


class _Widget(command.CommandObject):
    """
        Each widget must set its own width attribute when the _configure method
        is called. If this is set to the special value STRETCH, the bar itself
        will set the width to the maximum remaining space, after all other
        widgets have been configured. Only ONE widget per bar can have the
        STRETCH width set.

        The offset attribute is set by the Bar after all widgets have been
        configured.
    """
    font = "-*-luxi mono-*-r-*-*-12-*-*-*-*-*-*-*"
    width = None
    offset = None
    name = None

    @property
    def win(self):
        return self.bar.window.window

    @property
    def colormap(self):
        return self.qtile.display.screen().default_colormap

    def _configure(self, qtile, bar, event):
        self.qtile, self.bar, self.event = qtile, bar, event
        self._drawer = _Drawer(qtile, self.bar.window)
        self._drawer.setFont(self.font)

    def clear(self):
        self._drawer.rectangle(
            self.offset, 0, self.width, self.bar.size,
            self.bar.background
        )

    def info(self):
        return dict(
            name = self.__class__.__name__,
            offset = self.offset,
            width = self.width,
        )

    def click(self, x, y):
        pass

    def get(self, q, name):
        """
            Utility function for quick retrieval of a widget by name.
        """
        w = q.widgetMap.get(name)
        if not w:
            raise command.CommandError("No such widget: %s"%name)
        return w

    def _select(self, name, sel):
        if name == "bar":
            if not sel or sel == self.bar.position:
                return self.bar

    def cmd_info(self):
        return dict(name=self.name)


class Spacer(_Widget):
    def _configure(self, qtile, bar, event):
        _Widget._configure(self, qtile, bar, event)
        self.width = STRETCH

    def draw(self):
        pass


class GroupBox(_Widget):
    BOXPADDING_SIDE = 8
    PADDING = 3
    BORDERWIDTH = 1
    def __init__(self, currentFG="white", currentBG=_HIGHLIGHT, font=None,
                 activeFG="white", inactiveFG="#666666", border="#666666"):
        self.currentFG, self.currentBG = currentFG, currentBG
        self.activeFG, self.inactiveFG = activeFG, inactiveFG
        self.border = border
        if font:
            self.font = font

    def click(self, x, y):
        groupOffset = x/self.boxwidth
        if len(self.qtile.groups) - 1 >= groupOffset:
            self.bar.screen.setGroup(self.qtile.groups[groupOffset])

    def _configure(self, qtile, bar, event):
        _Widget._configure(self, qtile, bar, event)
        self.textheight, self.textwidth = self._drawer.textsize(
                                                self._drawer.font,
                                                *[i.name for i in qtile.groups]
                                            )
        self.boxwidth = self.BOXPADDING_SIDE*2 + self.textwidth
        self.width = self.boxwidth * len(qtile.groups) + 2 * self.PADDING
        self.event.subscribe("setgroup", self.draw)
        self.event.subscribe("window_add", self.draw)

    def draw(self):
        self.clear()
        x = self.offset + self.PADDING
        for i in self.qtile.groups:
            foreground, background, border = None, None, None
            if i.screen:
                if self.bar.screen.group.name == i.name:
                    background = self.currentBG
                    foreground = self.currentFG
                else:
                    background = self.bar.background
                    foreground = self.currentFG
                    border = True
            elif i.windows:
                foreground = self.activeFG
                background = self.bar.background
            else:
                foreground = self.inactiveFG
                background = self.bar.background
            self._drawer.textbox(
                i.name,
                x, 0, self.boxwidth, self.bar.size,
                padding = self.BOXPADDING_SIDE,
                foreground = foreground,
                background = background,
                alignment = CENTER,
            )
            if border:
                self._drawer.rectangle(
                    x, 0,
                    self.boxwidth - self.BORDERWIDTH,
                    self.bar.size - self.BORDERWIDTH,
                    borderWidth = self.BORDERWIDTH,
                    borderColor = self.border
                )
            x += self.boxwidth


class _TextBox(_Widget):
    PADDING = 5
    def __init__(self, text=" ", width=STRETCH, foreground="white",
                 background=_HIGHLIGHT, font=None):
        self.width, self.foreground, self.background = width, foreground, background
        self.text = text
        if font:
            self.font = font

    def draw(self):
        self._drawer.textbox(
            self.text,
            self.offset, 0, self.width, self.bar.size,
            padding = self.PADDING,
            foreground=self.foreground,
            background=self.background,
        )


class WindowName(_TextBox):
    def _configure(self, qtile, bar, event):
        _Widget._configure(self, qtile, bar, event)
        self.event.subscribe("window_name_change", self.update)
        self.event.subscribe("focus_change", self.update)

    def update(self):
        w = self.bar.screen.group.currentWindow
        self.text = w.name if w else " "
        self.draw()


class TextBox(_TextBox):
    def __init__(self, name, text=" ", width=STRETCH,
                 foreground="white", background=_HIGHLIGHT, font=None):
        self.name = name
        _TextBox.__init__(self, text, width, foreground, background, font)

    def update(self, text):
        self.text = text
        self.draw()

    def cmd_update(self, text):
        """
            Update the text in a TextBox widget.
        """
        self.update(text)

    def cmd_get(self):
        """
            Retrieve the text in a TextBox widget.
        """
        return self.text


class MeasureBox(_Widget):
    colors = ["red", "yellow", "orange", "green"]
    def __init__(self, name, width):
        self.name, self.width = name, width
        self.percentage = 0

    def update(self, percentage):
        self.percentage = percentage
        self.draw()

    def draw(self):
        self.clear()
        step = 100/float(len(self.colors))
        idx = int(self.percentage/step)
        idx = idx - 1 if self.percentage == 100 else idx
        color = self.colors[idx]
        self._drawer.rectangle(
            self.offset,
            0,
            int(float(self.width)/100*self.percentage),
            self.bar.size,
            color
        )

    def cmd_update(self, percentage):
        """
            Update the percentage in a MeasureBox widget.
        """
        if percentage > 100 or percentage < 0:
            raise command.CommandError("Percentage out of range: %s"%percentage)
        self.update(percentage)

