"""
This module define a widget that displays icons to launch softwares or commands
when clicked -- a launchbar.
Only png icon files are displayed, not xpm because cairo doesn't support
loading of xpm file.

To execute a software:
 - ('thunderbird', 'thunderbird -safe-mode', 'launch thunderbird in safe mode')
To execute a python command in qtile, begin with by 'qsh:'
 - ('logout', 'qsh:self.qtile.cmd_shutdown()', 'logout from qtile')


"""

from libqtile import bar
from libqtile.widget import base
import os.path
import cairo
import gobject
from xdg.IconTheme import getIconPath


class LaunchBar(base._Widget):
    """
    A widget that display icons to launch the associated command
    """

    defaults = [
        ('padding', 2, 'Padding between icons'),
        ('default_icon', '/usr/share/icons/oxygen/256x256/mimetypes/\
        application-x-executable.png', 'Default icon not found'),
    ]

    def __init__(self, progs=None, width=bar.CALCULATED, **config):
        """
        @progs: a list of tuple (software_name, command_to_execute, comment)
        for example:
        ('thunderbird', 'thunderbird -safe-mode', 'launch thunderbird in safe\
        mode')
        ('logout', 'qsh:self.qtile.cmd_shutdown()', 'logout from qtile')
        """
        base._Widget.__init__(self, width, *config)
        if progs is None:
            progs = []
        self.add_defaults(LaunchBar.defaults)
        self.surfaces = {}
        self.icons_files = {}
        self.icons_widths = {}
        self.icons_offsets = {}
        # For now, ignore the comments but may be one day it will be useful
        self.commands = {prg[0]: prg[1] for prg in progs}

    def _configure(self, qtile, pbar):
        base._Widget._configure(self, qtile, pbar)
        self.lookup_icons()
        self.setup_images()
        self.width = self.calculate_width()

    def setup_images(self):
        """ Create image structures for each icon files. """
        for img_name, iconfile in self.icons_files.iteritems():
            try:
                img = cairo.ImageSurface.create_from_png(iconfile)
            except cairo.Error:
                self.qtile.log.exception('No icon found for application ' +
                                         img_name + '(' + iconfile + ')')
                return

            input_width = img.get_width()
            input_height = img.get_height()

            sp = input_height / float(self.bar.height - 4)

            width = input_width / sp
            if width > self.width:
                self.width = int(width) + self.padding * 2

            imgpat = cairo.SurfacePattern(img)

            scaler = cairo.Matrix()

            scaler.scale(sp, sp)
            scaler.translate(self.padding * -1, -2)
            imgpat.set_matrix(scaler)

            imgpat.set_filter(cairo.FILTER_BEST)
            self.surfaces[img_name] = imgpat
            self.icons_widths[img_name] = width

    def _lookup_icon(self, name):
        """ Search for the icon corresponding to one command. """

        # if the software_name is directly an abslolute path icon file
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

        if self.icons_files[name] is None:
            self.icons_files[name] = self.default_icon

    def lookup_icons(self):
        """ Search for the icons corresponding to the commands to execute. """
        if not os.path.isfile(self.default_icon):
            self.default_icon = None
        for name in self.commands:
            self._lookup_icon(name)

    def get_icon_in_position(self, x, y):
        """ Retreive the wich icon is clicked according to its position. """
        for i in self.commands:
            if x < self.icons_offsets[i] + self.icons_widths[i] + self.padding\
               / 2:
                return i

    def button_press(self, x, y, button):
        """ Launch the associated command to the clicked icon. """
        if button == 1:
            icon = self.get_icon_in_position(x, y)
            if icon:
                cmd = self.commands[icon]
                if cmd.startswith('qsh:'):
                    eval(cmd[4:])
                else:
                    gobject.spawn_async([os.environ['SHELL'], '-c', cmd])
            self.draw()

    def draw(self):
        """ Draw the icons in the widget. """
        width = self.calculate_width()
        self.width = width
        self.drawer.clear(self.background or self.bar.background)
        xoffset = 0
        for i in self.commands:
            self.icons_offsets[i] = xoffset+self.padding
            self.drawer.ctx.move_to(self.offset + xoffset,
                                    self.icons_widths[i])
            self.drawer.clear(self.background or self.bar.background)
            self.drawer.ctx.set_source(self.surfaces[i])
            self.drawer.ctx.paint()
            self.drawer.draw(self.offset + xoffset,
                             self.icons_widths[i] + self.padding)
            xoffset += self.icons_widths[i] + self.padding

    def calculate_width(self):
        """ Compute the width of the widget according to each icon width. """
        return sum(self.icons_widths.values()) + self.padding * (
            len(self.icons_files.values()) + 1)
