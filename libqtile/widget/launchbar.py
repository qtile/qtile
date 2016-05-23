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

"""
This module define a widget that displays icons to launch softwares or commands
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
 - ('logout', 'qshell:self.qtile.cmd_shutdown()', 'logout from qtile')


"""

from __future__ import division

from libqtile import bar
from libqtile.log_utils import logger
from libqtile.widget import base

import os.path
import cairocffi
from xdg.IconTheme import getIconPath


class LaunchBar(base._Widget):
    """A widget that display icons to launch the associated command

    Parameters
    ==========
    progs :
        a list of tuples ``(software_name, command_to_execute, comment)``, for
        example::

            ('thunderbird', 'thunderbird -safe-mode', 'launch thunderbird in safe mode')
            ('logout', 'qshell:self.qtile.cmd_shutdown()', 'logout from qtile')
    """
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ('padding', 2, 'Padding between icons'),
        ('default_icon', '/usr/share/icons/oxygen/256x256/mimetypes/'
         'application-x-executable.png', 'Default icon not found'),
    ]

    def __init__(self, progs=None, width=bar.CALCULATED, **config):
        base._Widget.__init__(self, width, **config)
        if progs is None:
            progs = []
        self.add_defaults(LaunchBar.defaults)
        self.surfaces = {}
        self.icons_files = {}
        self.icons_widths = {}
        self.icons_offsets = {}
        # For now, ignore the comments but may be one day it will be useful
        self.progs = dict(enumerate([{'name': prog[0], 'cmd': prog[1],
                                      'comment': prog[2] if len(prog) > 2 else
                                      None} for prog in progs]))
        self.progs_name = set([prog['name'] for prog in self.progs.values()])
        self.length_type = bar.STATIC
        self.length = 0

    def _configure(self, qtile, pbar):
        base._Widget._configure(self, qtile, pbar)
        self.lookup_icons()
        self.setup_images()
        self.length = self.calculate_length()

    def setup_images(self):
        """ Create image structures for each icon files. """
        for img_name, iconfile in self.icons_files.items():
            if iconfile is None:
                logger.warning(
                    'No icon found for application "%s" (%s) switch to text mode',
                    img_name, iconfile)
                # if no icon is found and no default icon was set, we just
                # print the name, based on a textbox.
                textbox = base._TextBox()
                textbox._configure(self.qtile, self.bar)
                textbox.layout = self.drawer.textlayout(
                    textbox.text,
                    textbox.foreground,
                    textbox.font,
                    textbox.fontsize,
                    textbox.fontshadow,
                    markup=textbox.markup,
                )
                # the name will be displayed
                textbox.text = img_name
                textbox.calculate_length()
                self.icons_widths[img_name] = textbox.width
                self.surfaces[img_name] = textbox
                continue
            else:
                try:
                    img = cairocffi.ImageSurface.create_from_png(iconfile)
                except cairocffi.Error:
                    logger.exception('Error loading icon for application "%s" (%s)',
                        img_name, iconfile)
                    return

            input_width = img.get_width()
            input_height = img.get_height()

            sp = input_height / (self.bar.height - 4)
            width = int(input_width / sp)

            imgpat = cairocffi.SurfacePattern(img)
            scaler = cairocffi.Matrix()
            scaler.scale(sp, sp)
            scaler.translate(self.padding * -1, -2)
            imgpat.set_matrix(scaler)

            imgpat.set_filter(cairocffi.FILTER_BEST)
            self.surfaces[img_name] = imgpat
            self.icons_widths[img_name] = width

    def _lookup_icon(self, name):
        """ Search for the icon corresponding to one command. """
        self.icons_files[name] = None
        # if the software_name is directly an absolute path icon file
        if os.path.isabs(name):
            # name start with '/' thus it's an absolute path
            root, ext = os.path.splitext(name)
            if ext == '.png':
                self.icons_files[name] = name if os.path.isfile(name) else None
            else:
                # try to add the extension
                self.icons_files[name] = name + '.png' if os.path.isfile(name +
                                                '.png') else None
        else:
            self.icons_files[name] = getIconPath(name)
        # no search method found an icon, so default icon
        if self.icons_files[name] is None:
            self.icons_files[name] = self.default_icon

    def lookup_icons(self):
        """ Search for the icons corresponding to the commands to execute. """
        if self.default_icon is not None:
            if not os.path.isfile(self.default_icon):
                # if the default icon provided is not found, switch to
                # text mode
                self.default_icon = None
        for name in self.progs_name:
            self._lookup_icon(name)

    def get_icon_in_position(self, x, y):
        """ Determine which icon is clicked according to its position. """
        for i in self.progs:
            if x < (self.icons_offsets[i] +
                    self.icons_widths[self.progs[i]['name']] +
                    self.padding / 2):
                return i

    def button_press(self, x, y, button):
        """ Launch the associated command to the clicked icon. """
        if button == 1:
            icon = self.get_icon_in_position(x, y)
            if icon is not None:
                cmd = self.progs[icon]['cmd']
                if cmd.startswith('qshell:'):
                    exec(cmd[4:].lstrip())
                else:
                    self.qtile.cmd_spawn(cmd)
            self.draw()

    def draw(self):
        """ Draw the icons in the widget. """
        self.drawer.clear(self.background or self.bar.background)
        xoffset = 0
        for i in sorted(self.progs.keys()):
            self.icons_offsets[i] = xoffset + self.padding
            name = self.progs[i]['name']
            icon_width = self.icons_widths[name]
            self.drawer.ctx.move_to(self.offset + xoffset, icon_width)
            self.drawer.clear(self.background or self.bar.background)
            if isinstance(self.surfaces[name], base._TextBox):
                # display the name if no icon was found and no default icon
                textbox = self.surfaces[name]
                textbox.layout.draw(
                    self.padding + textbox.actual_padding,
                    int((self.bar.height - textbox.layout.height) / 2.0) + 1
                )
            else:
                # display an icon
                self.drawer.ctx.set_source(self.surfaces[name])
                self.drawer.ctx.paint()
            self.drawer.draw(offsetx=self.offset + xoffset,
                             width=icon_width + self.padding)
            xoffset += icon_width + self.padding

    def calculate_length(self):
        """ Compute the width of the widget according to each icon width. """
        return sum(self.icons_widths[prg['name']] for prg in self.progs.values()) \
            + self.padding * (len(self.progs) + 1)
