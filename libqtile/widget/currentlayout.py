# -*- coding: utf-8 -*-
# Copyright (c) 2011 Florian Mounier
# Copyright (c) 2011 Kenji_Takahashi
# Copyright (c) 2012 roger
# Copyright (c) 2012, 2014 Tycho Andersen
# Copyright (c) 2012 Maximilian Köhl
# Copyright (c) 2013 Craig Barnes
# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 Adi Sieker
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

from . import base
from .. import bar, hook
from ..log_utils import logger
import types
import os
import cairocffi
from ..layout.base import Layout
from .. import layout as layout_module


def default_icon_path():
    # default icons are in libqtile/resources/layout-icons
    root = os.sep.join(os.path.abspath(__file__).split(os.sep)[:-2])
    return os.path.join(root, 'resources', 'layout-icons')


class CurrentLayout(base._TextBox):
    """
    Display the name of the current layout of the current group of the screen,
    the bar containing the widget, is on.
    """
    orientations = base.ORIENTATION_HORIZONTAL

    def __init__(self, width=bar.CALCULATED, **config):
        base._TextBox.__init__(self, "", width, **config)

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        self.text = self.bar.screen.group.layouts[0].name
        self.setup_hooks()

    def setup_hooks(self):
        def hook_response(layout, group):
            if group.screen is not None and group.screen == self.bar.screen:
                self.text = layout.name
                self.bar.draw()
        hook.subscribe.layout_change(hook_response)

    def button_press(self, x, y, button):
        if button == 1:
            self.qtile.cmd_next_layout()
        elif button == 2:
            self.qtile.cmd_prev_layout()


class CurrentLayoutIcon(base._TextBox):
    """
    Display the icon representing the current layout of the
    current group of the screen, the bar containing the widget, is on.
    """
    orientations = base.ORIENTATION_HORIZONTAL

    defaults = [
        ('scale', 1, 'Scale factor, defaults to 1'),
        ('theme_path', default_icon_path(), 'Path to layout icons')
    ]

    def __init__(self, **config):
        base._TextBox.__init__(self, "", **config)
        self.add_defaults(CurrentLayoutIcon.defaults)
        self.scale = 1.0 / self.scale

        self.length_type = bar.STATIC
        self.length = 0

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        self.text = self.bar.screen.group.layouts[0].name
        self.icons_loaded = False
        self.surfaces = {}
        self.setup_images()
        self.setup_hooks()

    def setup_hooks(self):
        """
        Listens for layout change and performs a redraw when it occurs.
        """
        def hook_response(layout, group):
            if group.screen is not None and group.screen == self.bar.screen:
                self.current_layout = layout.name
                self.bar.draw()
        hook.subscribe.layout_change(hook_response)

    def button_press(self, x, y, button):
        if button == 1:
            self.qtile.cmd_next_layout()
        elif button == 2:
            self.qtile.cmd_prev_layout()

    def draw(self):
        if self.icons_loaded:
            try:
                surface = self.surfaces[self.current_layout]
            except KeyError:
                logger.error('No icon for layout {}'.format(
                    self.current_layout
                ))
            else:
                self.drawer.clear(self.background or self.bar.background)
                self.drawer.ctx.set_source(surface)
                self.drawer.ctx.paint()
                self.drawer.draw(offsetx=self.offset, width=self.length)
        else:
            # Fallback to text
            self.text = self.current_layout[0].upper()
            base._TextBox.draw(self)

    def _get_layout_names(self):
        """
        Returns the list of lowercased strings for each available layout name.
        """
        return [
            layout_class_name.lower()
            for layout_class, layout_class_name
            in map(lambda x: (getattr(layout_module, x), x), dir(layout_module))
            if isinstance(layout_class, (type, types.ClassType)) and issubclass(layout_class, Layout)
        ]

    def setup_images(self):
        """
        Loads layout icons.
        """
        for key in self._get_layout_names():
            path = os.path.join(self.theme_path, 'layout-{}.png'.format(key))
            try:
                img = cairocffi.ImageSurface.create_from_png(path)
            except (cairocffi.Error, IOError) as e:
                self.icons_loaded = False
                logger.exception(
                    'Failed to load icon for layout "{}", '
                    'error was: {}'.format(key, e.message)
                )
                return

            input_width = img.get_width()
            input_height = img.get_height()

            sp = float(input_height) / (self.bar.height - 1)

            width = float(input_width) / sp
            if width > self.length:
                self.length = int(width) + self.actual_padding * 2

            imgpat = cairocffi.SurfacePattern(img)

            scaler = cairocffi.Matrix()

            scaler.scale(sp, sp)
            scaler.scale(self.scale, self.scale)
            factor = (1 - 1 / self.scale) / 2
            scaler.translate(-width * factor, -width * factor)
            scaler.translate(self.actual_padding * -1, 0)
            imgpat.set_matrix(scaler)

            imgpat.set_filter(cairocffi.FILTER_BEST)
            self.surfaces[key] = imgpat

        self.icons_loaded = True
