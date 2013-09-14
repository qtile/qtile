"""
Class defining a object like 'bar', but a floating and size adapting bar.
Used to make kind of popup window (see the clock widget)

"""


import drawer
import configurable
import libqtile.widget

from libqtile import pane
from pane import Obj

STRETCH = pane.STRETCH
CALCULATED = pane.CALCULATED
STATIC = pane.STATIC

class Obj:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

STRETCH = Obj("STRETCH")


class NotifyWindow(pane.Pane, configurable.Configurable):

    def __init__(self, src_widget, widgets, size=None, **config):
        """
        @widgets: a list of widget objects
        @size: a tuple of width and height of the window
        @src_widget: the widget that call for the creation of this window
        """

        pane.Pane.__init__(self, widgets, (0,0), size, hidden=True,  **config)
        self.src_widget = src_widget


    def _configure(self, qtile, screen):
        # no STRETCH widget are allowed
        if any([w.width_type == STRETCH for w in self.widgets]):
            raise confreader.ConfigError("No STRETCH widget allowed!")

        # initial width is set to the screen size
        # if width is adapted to the content then this attribute 
        # is set to True
        self.size_adapted = False
        
        # the initial window is just used to compute content width
        # and height, no need to render or draw.
        # So, first save the drawer and handle methods
        drawer_backup = pane.Pane._configure_drawer
        window_handle_backup = pane.Pane._configure_window_handle

        pane.Pane._configure_drawer =  self._configure_no_drawer
        pane.Pane._configure_window_handle = self._configure_no_window_handle
        pane.Pane._configure(self, qtile, screen)

        # recompute the width of the window according to the content
        self.compute_size()
        self.size_adapted = True

        self.window.kill()
        # now, the real window

        # restore the initial drawer and handle methods
        pane.Pane._configure_drawer =  drawer_backup
        pane.Pane._configure_window_handle = window_handle_backup
        self.hidden = False
        pane.Pane._configure(self, qtile, screen)


    def _configure_no_drawer(self):
        pass

    def _configure_no_window_handle(self):
        pass

    def compute_size(self):
        # it is supposed that for now all widget are aline like in 'bar'
        width = 0
        for w in self.widgets:
            width += w.width

        height = self.src_widget.bar.height
        # calculate the height according to number of lines in text widgets
        nb_lines = [w.text.count('\n') for w in self.widgets if isinstance(w, libqtile.widget.textbox.TextBox)]
        nb_lines = 1 if len(nb_lines) == 0 else max(nb_lines) 
        height *= nb_lines + 1

        if self.size :
            width = min(width, size[0])
            height = min(height, size[1])
        self.size = (min(width, self.screen.width), min(height, self.screen.height))
        self._width = self.size[0]
        self._height = self.size[1]

    @property
    def x(self):
        s = self.screen
        if self.size_adapted:
            if s.right is self.src_widget.bar:
                return s.dwidth - (self.width + max(s.dx / 5, s.dy / 5))
            elif s.left is self.src_widget.bar:
                return s.x + max(s.dx / 5, s.dy / 5)
            else:
                # top or bottom bar : try to be the closest to the widget
                offset = self.src_widget.offset
                x = offset
                if (offset + self.width > s.width) and \
                   (offset + self.src_widget.width - self.width > 0):
                    x = offset + self.src_widget.width - self.width
                return x
        else:
            return 0


    @property
    def y(self):
        s = self.screen
        if self.size_adapted:
            if s.top is self.src_widget.bar:
                return s.y + s.top.height + max(s.dy / 5, s.dx / 5)
            elif s.bottom is self.src_widget.bar:
                return s.dheight - (self.height + max(s.dy / 5, s.dx / 5))
            else:
                # right or left bar : try to be the closest to the widget
                offset = self.src_widget.offset
                y = offset
                if (offset + self.height > s.height) and \
                   (offset + self.src_widget.height - self.height > 0):
                    y = offset + self.src_widget.height - self.height
                return y
        else:
            return 0


    @property
    def width(self):
        if self.size_adapted:
            return self._width
        elif self.size:
            return min(self._width, self.screen.width)
        else:
            return self.screen.width


    @property
    def height(self):
        if self.size_adapted:
            return self._height
        elif self.size:
            return min(self._height, self.screen.height)
        else:
            return self.screen.dheight


    def info(self):
        return dict(
            x = self.x,
            y = self.y,
            width = self.width,
            height = self.height,
            widget = self.src.widget,
            widgets = [i.info() for i in self.widgets],
            window = self.window.window.wid,
        )

