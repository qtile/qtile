# Copyright (c) 2014 Tycho Andersen
# Copyright (c) 2014 dequis
# Copyright (c) 2014-2015 Joseph Razik
# Copyright (c) 2014 Sean Vig
# Copyright (c) 2015 reus
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

import os.path

import cairocffi

try:
    from xdg.IconTheme import getIconPath

    has_xdg = True
except ImportError:
    has_xdg = False

from libqtile import bar
from libqtile.backend.base.drawer import TextLayout
from libqtile.images import Img
from libqtile.log_utils import logger
from libqtile.widget import base


class LaunchBar(base._Widget):
    """
    This module defines a widget that displays icons to launch softwares or commands
    when clicked -- a launchbar.
    Only png icon files are displayed, not xpm because cairo doesn't support
    loading of xpm file.
    The order of displaying (from left to right) is in the order of the list.

    If no icon was found for the name provided and if default_icon is set to None
    then the name is printed instead. If default_icon is defined then this icon is
    displayed instead.

    To execute a software:
     - ('thunderbird', 'thunderbird -safe-mode', 'launch thunderbird in safe mode')
    To execute a python command in qtile, begin with by 'qshell:'
     - ('/path/to/icon.png', 'qshell:self.qtile.shutdown()', 'logout from qtile')


    Optional requirements: `pyxdg <https://pypi.org/project/pyxdg/>`__ for finding the icon path if it is not provided in the ``progs`` tuple.
    """

    orientations = base.ORIENTATION_BOTH
    defaults = [
        ("padding", 2, "Padding between icons"),
        (
            "default_icon",
            "/usr/share/icons/oxygen/256x256/mimetypes/application-x-executable.png",
            "Default icon not found",
        ),
        ("font", "sans", "Text font"),
        ("fontsize", None, "Font pixel size. Calculated if None."),
        ("fontshadow", None, "Font shadow color, default is None (no shadow)"),
        ("foreground", "#ffffff", "Text colour."),
        (
            "progs",
            [],
            "A list of tuples (software_name or icon_path, command_to_execute, comment), for example:"
            " [('thunderbird', 'thunderbird -safe-mode', 'launch thunderbird in safe mode'), "
            " ('/path/to/icon.png', 'qshell:self.qtile.shutdown()', 'logout from qtile')]",
        ),
        ("text_only", False, "Don't use any icons."),
        ("icon_size", None, "Size of icons. ``None`` to fit to bar."),
        (
            "theme_path",
            None,
            "Path to icon theme to be used by pyxdg for icons. ``None`` will use default icon theme.",
        ),
        ("markup", False, "Whether to allow markup in text label."),
    ]

    def __init__(self, _progs: list[tuple[str, str, str]] | None = None, width=0, **config):
        base._Widget.__init__(self, width, **config)
        self.add_defaults(LaunchBar.defaults)
        self.surfaces: dict[str, Img | TextLayout] = {}
        self.icons_files: dict[str, str | None] = {}
        self.icons_widths: dict[str, int] = {}
        self.icons_offsets: dict[str, int] = {}

        if _progs:
            logger.warning(
                "The use of a positional argument in LaunchBar is deprecated. "
                "Please update your config to use progs=[...]."
            )
            config["progs"] = _progs

        # For now, ignore the comments but may be one day it will be useful
        self.progs = dict(
            enumerate(
                [
                    {
                        "name": prog[0],
                        "cmd": prog[1],
                        "comment": prog[2] if len(prog) > 2 else None,
                    }
                    for prog in config.get("progs", list())
                ]
            )
        )
        self.progs_name = set([prog["name"] for prog in self.progs.values()])
        self.length_type = bar.STATIC
        self.length = 0

    def _configure(self, qtile, pbar):
        base._Widget._configure(self, qtile, pbar)
        if self.fontsize is None:
            self.fontsize = self.bar.size - self.bar.size / 5
        self.lookup_icons()
        self.setup_images()
        self.length = self.calculate_length()

    def setup_images(self):
        """Create image structures for each icon files."""
        if self.icon_size is None:
            self._icon_size = self.bar.size - 4
        self._icon_padding = (self.bar.size - self._icon_size) // 2

        for img_name, iconfile in self.icons_files.items():
            if iconfile is None or self.text_only:
                # Only warn the user that there's no icon if they haven't set text only mode
                if not self.text_only:
                    logger.warning(
                        'No icon found for application "%s" (%s) switch to text mode',
                        img_name,
                        iconfile,
                    )
                # if no icon is found and no default icon was set, we just
                # print the name, based on a textbox.
                textbox = self.drawer.textlayout(
                    img_name,
                    self.foreground,
                    self.font,
                    self.fontsize,
                    self.fontshadow,
                    markup=self.markup,
                )
                self.icons_widths[img_name] = textbox.width + 2 * self.padding
                self.surfaces[img_name] = textbox
                continue
            else:
                try:
                    img = Img.from_path(iconfile)
                except cairocffi.Error:
                    logger.exception(
                        'Error loading icon for application "%s" (%s)', img_name, iconfile
                    )
                    return

            input_width = img.width
            input_height = img.height

            sp = input_height / (self._icon_size)
            width = int(input_width / sp)

            imgpat = cairocffi.SurfacePattern(img.surface)
            scaler = cairocffi.Matrix()
            scaler.scale(sp, sp)
            scaler.translate(self.padding * -1, -2)
            imgpat.set_matrix(scaler)

            imgpat.set_filter(cairocffi.FILTER_BEST)
            self.surfaces[img_name] = imgpat
            self.icons_widths[img_name] = width

    def _lookup_icon(self, name):
        """Search for the icon corresponding to one command."""
        self.icons_files[name] = None

        # expands ~ if name is a path and does nothing if not
        ipath = os.path.expanduser(name)

        # if the software_name is directly an absolute path icon file
        if os.path.isabs(ipath):
            # name start with '/' thus it's an absolute path
            root, ext = os.path.splitext(ipath)
            img_extensions = [".tif", ".tiff", ".bmp", ".jpg", ".jpeg", ".gif", ".png", ".svg"]
            if ext in img_extensions:
                self.icons_files[name] = ipath if os.path.isfile(ipath) else None
            else:
                # try to add the extension
                for extension in img_extensions:
                    if os.path.isfile(ipath + extension):
                        self.icons_files[name] = ipath + extension
                        break
        elif has_xdg:
            self.icons_files[name] = getIconPath(name, theme=self.theme_path)
        # no search method found an icon, so default icon
        if self.icons_files[name] is None:
            self.icons_files[name] = self.default_icon

    def lookup_icons(self):
        """Search for the icons corresponding to the commands to execute."""
        if self.default_icon is not None:
            if not os.path.isfile(self.default_icon):
                # if the default icon provided is not found, switch to
                # text mode
                self.default_icon = None
        for name in self.progs_name:
            self._lookup_icon(name)

    def get_icon_in_position(self, x, y):
        """Determine which icon is clicked according to its position."""
        if self.bar.horizontal:
            pos = x
        elif self.bar.screen.left is self.bar:
            pos = self.length - y
        else:
            pos = y
        for i in self.progs:
            if pos < (
                self.icons_offsets[i]
                + self.icons_widths[self.progs[i]["name"]]
                + self.padding / 2
            ):
                return i

    def button_press(self, x, y, button):
        """Launch the associated command to the clicked icon."""
        base._Widget.button_press(self, x, y, button)
        if button == 1:
            icon = self.get_icon_in_position(x, y)
            if icon is not None:
                cmd = self.progs[icon]["cmd"]
                if cmd.startswith("qshell:"):
                    exec(cmd[7:].lstrip())
                else:
                    self.qtile.spawn(cmd)
            self.draw()

    def draw(self):
        """Draw the icons in the widget."""
        self.drawer.clear(self.background or self.bar.background)

        offset = 0
        self.drawer.ctx.save()
        self.rotate_drawer()

        for i in sorted(self.progs.keys()):
            self.drawer.ctx.save()
            self.drawer.ctx.translate(offset, 0)
            self.icons_offsets[i] = offset + self.padding
            name = self.progs[i]["name"]
            icon_width = self.icons_widths[name]
            if isinstance(self.surfaces[name], TextLayout):
                # display the name if no icon was found and no default icon
                textbox = self.surfaces[name]
                textbox.draw(self.padding, int((self.bar.size - textbox.height) / 2) + 1)
            else:
                # display an icon
                # Translate to vertically centre the icon
                self.drawer.ctx.translate(0, self._icon_padding)
                self.drawer.ctx.set_source(self.surfaces[name])
                self.drawer.ctx.paint()

            self.drawer.ctx.restore()

            offset += icon_width + self.padding

        self.drawer.ctx.restore()
        self.draw_at_default_position()

    def calculate_length(self):
        """Compute the width of the widget according to each icon width."""
        return sum(
            self.icons_widths[prg["name"]] for prg in self.progs.values()
        ) + self.padding * (len(self.progs) + 1)
