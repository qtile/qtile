# Copyright (c) 2021, elParaguayo. All rights reserved.
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
from typing import Any, List, Tuple

from libqtile.log_utils import logger
from libqtile.widget import base


class _Decoration(base.PaddingMixin):
    """
        Base decoration class. Should not be called by
        configs directly.
    """

    defaults = [
        ("padding", 0, "Default padding")
    ]  # type: List[Tuple[str, Any, str]]

    def __init__(self, **config):
        base.PaddingMixin.__init__(self, **config)
        self.add_defaults(_Decoration.defaults)

    @property
    def height(self):
        return self.parent.height

    @property
    def width(self):
        return self.parent.width

    @property
    def drawer(self):
        return self.parent.drawer

    @property
    def ctx(self):
        return self.parent.drawer.ctx

    def draw(self, parent):
        self.parent = parent


class RectDecoration(_Decoration):
    """
        Widget decoration that draws a rectangle behind the widget contents.

        Only one colour can be set but decorations can be layered to achieve
        multi-coloured effects.

        Rectangles can be drawn as just the the outline or filled. Curved corners
        can be obtained by setting the ``radius`` parameter.
    """
    defaults = [
        ("filled", False, "Whether to fill shape"),
        ("radius", 4, "Radius for corners (0 for square)"),
        ("dec_colour", "#000000", "Colour for decoration"),
        ("linewidth", 2, "Line width for decoration")
    ]  # type: List[Tuple[str, Any, str]]

    def __init__(self, **config):
        _Decoration.__init__(self, **config)
        self.add_defaults(RectDecoration.defaults)

    def draw(self, parent):
        _Decoration.draw(self, parent)

        box_height = self.height - 2 * self.padding_y
        box_width = self.width - 2 * self.padding_x

        self.drawer.set_source_rgb(self.dec_colour)

        degrees = math.pi / 180.0

        self.ctx.new_sub_path()

        delta = self.radius + self.linewidth / 2

        self.ctx.arc(
            self.padding_x + box_width - delta,
            self.padding_y + delta,
            self.radius,
            -90 * degrees,
            0 * degrees
        )

        self.ctx.arc(
            self.padding_x + box_width - delta,
            self.padding_y + box_height - delta,
            self.radius,
            0 * degrees,
            90 * degrees
        )

        self.ctx.arc(
            self.padding_x + delta,
            self.padding_y + box_height - delta,
            self.radius,
            90 * degrees,
            180 * degrees
        )
        self.ctx.arc(
            self.padding_x + delta,
            self.padding_y + delta,
            self.radius,
            180 * degrees,
            270 * degrees
        )

        self.ctx.close_path()

        if self.filled:
            self.ctx.fill()
        else:
            self.ctx.set_line_width(self.linewidth)
            self.ctx.stroke()


class BorderDecoration(_Decoration):
    """
        Widget decoration that draws a straight line on the widget border.
        Padding can be used to adjust the position of the border further.

        Only one colour can be set but decorations can be layered to achieve
        multi-coloured effects.
    """
    defaults = [
        ("colour", "#000000", "Border colour"),
        (
            "border_width",
            2,
            "Border width. Single number is all edges, or [top/bottom, left/right] or [top, bottom, left, right]"
        )
    ]  # type: List[Tuple[str, Any, str]]

    def __init__(self, **config):
        _Decoration.__init__(self, **config)
        self.add_defaults(BorderDecoration.defaults)

        if type(self.border_width) in [float, int]:
            tp = bm = lt = rt = self.border_width
        elif type(self.border_width) in [tuple, list]:
            if len(self.border_width) == 1:
                tp = bm = lt = rt = self.border_width[0]
            elif len(self.border_width) == 2:
                tp = bm = self.border_width[0]
                lt = rt = self.border_width[1]
            elif len(self.border_width) == 4:
                tp, bm, lt, rt = self.border_width
            else:
                logger.info("Border width should be a single number or a list of 1, 2 or 4 values")
                tp = bm = lt = rt = 0
        else:
            logger.info("Border width should be a single number or a list of 1, 2 or 4 values")
            tp = bm = lt = rt = 0

        self.borders = [tp, bm, lt, rt]

    def draw(self, parent):
        _Decoration.draw(self, parent)

        top, bottom, left, right = self.borders

        self.drawer.set_source_rgb(self.colour)

        if top:
            offset = top // 2
            self._draw_border(
                offset + self.padding_x,
                offset + self.padding_y,
                self.width - offset - self.padding_x,
                offset + self.padding_y,
                top
            )

        if bottom:
            offset = bottom // 2
            self._draw_border(
                offset + self.padding_x,
                self.height - offset - self.padding_y,
                self.width - offset - self.padding_y,
                self.height - offset - self.padding_y,
                bottom
            )

        if left:
            offset = left // 2
            self._draw_border(
                offset + self.padding_x,
                offset + self.padding_y,
                offset + self.padding_x,
                self.height - offset - self.padding_y,
                left
            )

        if right:
            offset = right // 2
            self._draw_border(
                self.width - offset - self.padding_x,
                offset + self.padding_y,
                self.width - offset - self.padding_x,
                self.height - offset - self.padding_y,
                right
            )

    def _draw_border(self, x1, y1, x2, y2, linewidth):
        self.ctx.move_to(x1, y1)
        self.ctx.line_to(x2, y2)
        self.ctx.set_line_width(linewidth)
        self.ctx.stroke()
