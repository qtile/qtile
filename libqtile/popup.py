# Copyright (c) 2020-21, Matt Colligan. All rights reserved.
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

from typing import TYPE_CHECKING

from libqtile import configurable, pangocffi

if TYPE_CHECKING:
    from typing import Any

    from cairocffi import ImageSurface

    from libqtile.backend.base import Drawer
    from libqtile.core.manager import Qtile
    from libqtile.utils import ColorType


class Popup(configurable.Configurable):
    """
    This class can be used to create popup windows that display images and/or text.
    """

    defaults = [
        ("opacity", 1.0, "Opacity of notifications."),
        ("foreground", "#ffffff", "Colour of text."),
        ("background", "#111111", "Background colour."),
        ("border", "#111111", "Border colour."),
        ("border_width", 0, "Line width of drawn borders."),
        ("font", "sans", "Font used in notifications."),
        ("font_size", 14, "Size of font."),
        ("fontshadow", None, "Colour for text shadows, or None for no shadows."),
        ("horizontal_padding", 0, "Padding at sides of text."),
        ("vertical_padding", 0, "Padding at top and bottom of text."),
        ("text_alignment", "left", "Text alignment: left, center or right."),
        ("wrap", True, "Whether to wrap text."),
    ]

    def __init__(
        self,
        qtile: Qtile,
        x: int = 50,
        y: int = 50,
        width: int = 256,
        height: int = 64,
        **config,
    ):
        configurable.Configurable.__init__(self, **config)
        self.add_defaults(Popup.defaults)
        self.qtile = qtile

        self.win: Any = qtile.core.create_internal(
            x, y, width, height
        )  # TODO: better annotate Internal
        self.win.opacity = self.opacity
        self.win.process_button_click = self.process_button_click
        self.win.process_window_expose = self.draw

        self.drawer: Drawer = self.win.create_drawer(width, height)
        self.clear()
        self.layout = self.drawer.textlayout(
            text="",
            colour=self.foreground,
            font_family=self.font,
            font_size=self.font_size,
            font_shadow=self.fontshadow,
            wrap=self.wrap,
            markup=True,
        )
        self.layout.layout.set_alignment(pangocffi.ALIGNMENTS[self.text_alignment])

        if self.border_width and self.border:
            self.win.paint_borders(self.border, self.border_width)

        self.x = self.win.x
        self.y = self.win.y

    def process_button_click(self, x, y, button) -> None:
        if button == 1:
            self.hide()

    @property
    def width(self) -> int:
        return self.win.width

    @width.setter
    def width(self, value: int) -> None:
        self.win.width = value
        self.drawer.width = value

    @property
    def height(self) -> int:
        return self.win.height

    @height.setter
    def height(self, value: int) -> None:
        self.win.height = value
        self.drawer.height = value

    @property
    def text(self) -> str:
        return self.layout.text

    @text.setter
    def text(self, value: str) -> None:
        self.layout.text = value

    @property
    def foreground(self) -> ColorType:
        return self._foreground

    @foreground.setter
    def foreground(self, value: ColorType) -> None:
        self._foreground = value
        if hasattr(self, "layout"):
            self.layout.colour = value

    def set_border(self, color: ColorType) -> None:
        self.win.paint_borders(color, self.border_width)

    def clear(self) -> None:
        self.drawer.clear(self.background)

    def draw_text(self, x: int | None = None, y: int | None = None) -> None:
        self.layout.draw(
            x or self.horizontal_padding,
            y or self.vertical_padding,
        )

    def draw(self) -> None:
        self.drawer.draw()

    def place(self) -> None:
        self.win.place(
            self.x, self.y, self.width, self.height, self.border_width, self.border, above=True
        )

    def unhide(self) -> None:
        self.win.unhide()

    def draw_image(self, image: ImageSurface, x: int, y: int) -> None:
        """
        Paint an image onto the window at point x, y. The image should be a surface e.g.
        loaded from libqtile.images.Img.from_path.
        """
        self.drawer.ctx.set_source_surface(image, x, y)
        self.drawer.ctx.paint()

    def hide(self) -> None:
        self.win.hide()

    def kill(self) -> None:
        self.win.kill()
        self.layout.finalize()
        self.drawer.finalize()
