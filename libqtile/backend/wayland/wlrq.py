# Copyright (c) 2021 Matt Colligan
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

import functools
import operator
import typing

import cairocffi
from wlroots.wlr_types import Texture
from wlroots.wlr_types.keyboard import KeyboardModifier

from libqtile.log_utils import logger


class WlrQError(Exception):
    pass


ModMasks = {
    "shift": KeyboardModifier.SHIFT,
    "lock": KeyboardModifier.CAPS,
    "control": KeyboardModifier.CTRL,
    "mod1": KeyboardModifier.ALT,
    "mod2": KeyboardModifier.MOD2,
    "mod3": KeyboardModifier.MOD3,
    "mod4": KeyboardModifier.LOGO,
    "mod5": KeyboardModifier.MOD5,
}

buttons = {
    1: 0x110,
    2: 0x111,
    3: 0x112,
}

buttons_inv = {v: k for k, v in buttons.items()}

# from drm_fourcc.h
DRM_FORMAT_ARGB8888 = 875713089


def translate_masks(modifiers: typing.List[str]) -> int:
    """
    Translate a modifier mask specified as a list of strings into an or-ed
    bit representation.
    """
    masks = []
    for i in modifiers:
        try:
            masks.append(ModMasks[i])
        except KeyError as e:
            raise WlrQError("Unknown modifier: %s" % i) from e
    if masks:
        return functools.reduce(operator.or_, masks)
    else:
        return 0


class Painter:
    def __init__(self, core):
        self.core = core

    def paint(self, screen, image_path, mode=None):
        try:
            with open(image_path, 'rb') as f:
                image, _ = cairocffi.pixbuf.decode_to_image_surface(f.read())
        except IOError as e:
            logger.error('Wallpaper: %s' % e)
            return

        surface = cairocffi.ImageSurface(
            cairocffi.FORMAT_ARGB32, screen.width, screen.height
        )
        with cairocffi.Context(surface) as context:
            context.translate(screen.x, screen.y)
            if mode == 'fill':
                context.rectangle(0, 0, screen.width, screen.height)
                context.clip()
                image_w = image.get_width()
                image_h = image.get_height()
                width_ratio = screen.width / image_w
                if width_ratio * image_h >= screen.height:
                    context.scale(width_ratio)
                else:
                    height_ratio = screen.height / image_h
                    context.translate(
                        - (image_w * height_ratio - screen.width) // 2, 0
                    )
                    context.scale(height_ratio)
            elif mode == 'stretch':
                context.scale(
                    sx=screen.width / image.get_width(),
                    sy=screen.height / image.get_height(),
                )
            context.set_source_surface(image)
            context.paint()

            stride = surface.format_stride_for_width(cairocffi.FORMAT_ARGB32, screen.width)
            surface.flush()
            texture = Texture.from_pixels(
                self.core.renderer,
                DRM_FORMAT_ARGB8888,
                stride,
                screen.width,
                screen.height,
                cairocffi.cairo.cairo_image_surface_get_data(surface._pointer)
            )
            # TODO: how to map screens to outputs?
            self.core.outputs[0].wallpaper = texture
