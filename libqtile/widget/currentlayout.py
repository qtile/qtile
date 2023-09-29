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
import itertools
import os

from libqtile import bar, hook
from libqtile.images import Img
from libqtile.log_utils import logger
from libqtile.widget import base


class CurrentLayout(base._TextBox):
    """
    Display the name of the current layout of the current group of the screen,
    the bar containing the widget, is on.
    """

    def __init__(self, width=bar.CALCULATED, **config):
        base._TextBox.__init__(self, "", width, **config)

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        layout_id = self.bar.screen.group.current_layout
        self.text = self.bar.screen.group.layouts[layout_id].name
        self.setup_hooks()

        self.add_callbacks(
            {
                "Button1": qtile.next_layout,
                "Button2": qtile.prev_layout,
            }
        )

    def hook_response(self, layout, group):
        if group.screen is not None and group.screen == self.bar.screen:
            self.text = layout.name
            self.bar.draw()

    def setup_hooks(self):
        hook.subscribe.layout_change(self.hook_response)

    def remove_hooks(self):
        hook.unsubscribe.layout_change(self.hook_response)

    def finalize(self):
        self.remove_hooks()
        base._TextBox.finalize(self)


class CurrentLayoutIcon(base._TextBox):
    """
    Display the icon representing the current layout of the
    current group of the screen on which the bar containing the widget is.

    If you are using custom layouts, a default icon with question mark
    will be displayed for them. If you want to use custom icon for your own
    layout, for example, `FooGrid`, then create a file named
    "layout-foogrid.png" and place it in `~/.icons` directory. You can as well
    use other directories, but then you need to specify those directories
    in `custom_icon_paths` argument for this plugin.

    The widget will look for icons with a `png` or `svg` extension.

    The order of icon search is:

    - dirs in `custom_icon_paths` config argument
    - `~/.icons`
    - built-in qtile icons
    """

    orientations = base.ORIENTATION_HORIZONTAL

    defaults = [
        ("scale", 1, "Scale factor relative to the bar height. Defaults to 1"),
        (
            "custom_icon_paths",
            [],
            "List of folders where to search icons before"
            "using built-in icons or icons in ~/.icons dir.  "
            "This can also be used to provide"
            "missing icons for custom layouts.  "
            "Defaults to empty list.",
        ),
    ]

    def __init__(self, **config):
        base._TextBox.__init__(self, "", **config)
        self.add_defaults(CurrentLayoutIcon.defaults)

        self.length_type = bar.STATIC
        self.length = 0

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        layout_id = self.bar.screen.group.current_layout
        self.text = self.bar.screen.group.layouts[layout_id].name
        self.current_layout = self.text
        self.icons_loaded = False
        self.icon_paths = []
        self.surfaces = {}
        self._update_icon_paths()
        self._setup_images()
        self._setup_hooks()

        self.add_callbacks(
            {
                "Button1": qtile.next_layout,
                "Button2": qtile.prev_layout,
            }
        )

    def hook_response(self, layout, group):
        if group.screen is not None and group.screen == self.bar.screen:
            self.current_layout = layout.name
            self.bar.draw()

    def _setup_hooks(self):
        """
        Listens for layout change and performs a redraw when it occurs.
        """
        hook.subscribe.layout_change(self.hook_response)

    def _remove_hooks(self):
        """
        Listens for layout change and performs a redraw when it occurs.
        """
        hook.unsubscribe.layout_change(self.hook_response)

    def draw(self):
        if self.icons_loaded:
            try:
                surface = self.surfaces[self.current_layout]
            except KeyError:
                logger.error("No icon for layout %s", self.current_layout)
            else:
                self.drawer.clear(self.background or self.bar.background)
                self.drawer.ctx.save()
                self.drawer.ctx.translate(
                    (self.width - surface.width) / 2,
                    (self.bar.height - surface.height) / 2,
                )
                self.drawer.ctx.set_source(surface.pattern)
                self.drawer.ctx.paint()
                self.drawer.ctx.restore()
                self.drawer.draw(offsetx=self.offset, offsety=self.offsety, width=self.length)
        else:
            # Fallback to text
            self.text = self.current_layout[0].upper()
            base._TextBox.draw(self)

    def _get_layout_names(self):
        """
        Returns a sequence of tuples of layout name and lowercased class name
        strings for each available layout.
        """

        layouts = itertools.chain(
            self.qtile.config.layouts,
            (layout for group in self.qtile.config.groups for layout in group.layouts),
        )

        return set((layout.name, layout.__class__.__name__.lower()) for layout in layouts)

    def _update_icon_paths(self):
        self.icon_paths = []

        # We allow user to override icon search path
        self.icon_paths.extend(os.path.expanduser(path) for path in self.custom_icon_paths)

        # We also look in ~/.icons/ and ~/.local/share/icons
        self.icon_paths.append(os.path.expanduser("~/.icons"))
        self.icon_paths.append(os.path.expanduser("~/.local/share/icons"))

        # Default icons are in libqtile/resources/layout-icons.
        # If using default config without any custom icons,
        # this path will be used.
        root = os.sep.join(os.path.abspath(__file__).split(os.sep)[:-2])
        self.icon_paths.append(os.path.join(root, "resources", "layout-icons"))

    def find_icon_file_path(self, layout_name):
        for icon_path in self.icon_paths:
            for extension in ["png", "svg"]:
                icon_filename = "layout-{}.{}".format(layout_name, extension)
                icon_file_path = os.path.join(icon_path, icon_filename)
                if os.path.isfile(icon_file_path):
                    return icon_file_path

    def _setup_images(self):
        """
        Loads layout icons.
        """
        for names in self._get_layout_names():
            layout_name = names[0]
            # Python doesn't have an ordered set but we can use a dictionary instead
            # First key is the layout's name (which may have been set by the user),
            # the second is the class name. If these are the same (i.e. the user hasn't
            # set a name) then there is only one key in the dictionary.
            layouts = dict.fromkeys(names)
            for layout in layouts.keys():
                icon_file_path = self.find_icon_file_path(layout)
                if icon_file_path:
                    break
            else:
                logger.warning('No icon found for layout "%s"', layout_name)
                icon_file_path = self.find_icon_file_path("unknown")

            img = Img.from_path(icon_file_path)

            new_height = (self.bar.height - 2) * self.scale
            img.resize(height=new_height)
            if img.width > self.length:
                self.length = img.width + self.actual_padding * 2

            self.surfaces[layout_name] = img

        self.icons_loaded = True

    def finalize(self):
        self._remove_hooks()
        base._TextBox.finalize(self)
