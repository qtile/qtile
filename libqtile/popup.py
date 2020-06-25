# Copyright (c) 2020, Matt Colligan. All rights reserved.
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


from xcffib.xproto import StackMode

from libqtile import configurable, drawer, pangocffi, window


class Popup(configurable.Configurable):
    """
    This class can be used to create popup windows that display images and/or text.
    """
    defaults = [
        ('opacity', 1.0, 'Opacity of notifications.'),
        ('foreground', '#ffffff', 'Colour of text.'),
        ('background', '#111111', 'Background colour.'),
        ('border', '#111111', 'Border colour.'),
        ('border_width', 0, 'Line width of drawn borders.'),
        ('corner_radius', None, 'Corner radius for round corners, or None.'),
        ('font', 'sans', 'Font used in notifications.'),
        ('font_size', 14, 'Size of font.'),
        ('fontshadow', None, 'Colour for text shadows, or None for no shadows.'),
        ('horizontal_padding', 0, 'Padding at sides of text.'),
        ('vertical_padding', 0, 'Padding at top and bottom of text.'),
        ('text_alignment', 'left', 'Text alignment: left, center or right.'),
        ('wrap', True, 'Whether to wrap text.'),
    ]

    def __init__(self, qtile, x=50, y=50, width=256, height=64, **config):
        configurable.Configurable.__init__(self, **config)
        self.add_defaults(Popup.defaults)
        self.qtile = qtile

        win = qtile.conn.create_window(x, y, width, height)
        win.set_property("QTILE_INTERNAL", 1)
        self.win = window.Internal(win, qtile)
        self.win.opacity = self.opacity
        self.drawer = drawer.Drawer(
            self.qtile, self.win.window.wid, width, height,
        )
        self.layout = self.drawer.textlayout(
            text='',
            colour=self.foreground,
            font_family=self.font,
            font_size=self.font_size,
            font_shadow=self.fontshadow,
            wrap=self.wrap,
            markup=True,
        )
        self.layout.layout.set_alignment(pangocffi.ALIGNMENTS[self.text_alignment])

        if self.border_width:
            self.win.window.configure(borderwidth=self.border_width)
        if self.corner_radius:
            self.win.window.round_corners(width, height, self.corner_radius, self.border_width)

        self.win.handle_Expose = self._handle_Expose
        self.win.handle_KeyPress = self._handle_KeyPress
        self.win.handle_ButtonPress = self._handle_ButtonPress

        self.x = self.win.x
        self.y = self.win.y
        if not self.border_width:
            self.border = None

    def _handle_Expose(self, e):  # noqa: N802
        pass

    def _handle_KeyPress(self, event):  # noqa: N802
        pass

    def _handle_ButtonPress(self, event):  # noqa: N802
        if event.detail == 1:
            self.hide()

    @property
    def width(self):
        return self.win.width

    @width.setter
    def width(self, value):
        self.win.width = value
        self.drawer.width = value

    @property
    def height(self):
        return self.win.height

    @height.setter
    def height(self, value):
        self.win.height = value
        self.drawer.height = value

    @property
    def text(self):
        return self.layout.text

    @text.setter
    def text(self, value):
        self.layout.text = value

    @property
    def foreground(self):
        return self._foreground

    @foreground.setter
    def foreground(self, value):
        self._foreground = value
        if hasattr(self, 'layout'):
            self.layout.colour = value

    def set_border(self, color):
        self.win.window.set_attribute(borderpixel=color)

    def clear(self):
        self.drawer.clear(self.background)

    def draw_text(self, x=None, y=None):
        self.layout.draw(
            x or self.horizontal_padding,
            y or self.vertical_padding,
        )

    def draw(self):
        self.drawer.draw()

    def place(self):
        self.win.place(
            self.x, self.y, self.width, self.height,
            self.border_width, self.border, above=True
        )

    def unhide(self):
        self.win.unhide()
        self.win.window.configure(stackmode=StackMode.Above)

    def draw_image(self, image, x, y):
        """
        Paint an image onto the window at point x, y. The image should be a surface e.g.
        loaded from libqtile.images.Img.load_path.
        """
        self.drawer.ctx.set_source_surface(image, x, y)
        self.drawer.ctx.paint()

    def hide(self):
        self.win.hide()

    def kill(self):
        self.win.kill()
