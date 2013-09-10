"""
Class defining a object like 'bar', but a floating and size adapting bar.
Used to make kind of popup window (see the clock widget)

"""


import drawer
import hook
import configurable
import window
import libqtile.widget

class Obj:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

STRETCH = Obj("STRETCH")
CALCULATED = Obj("CALCULATED")
STATIC = Obj("STATIC")


class NotifyWindow(configurable.Configurable):
    defaults = [
        ("background", "#000000", "Background colour."),
        ("opacity",  1, "Bar window opacity.")
    ]
    

    def __init__(self, src_widget, widgets, size=None, **config):
        """
        @widgets: a list of widget objects
        @size: a tuple of width and height of the window
        @src_widget: the widget that call for the creation of this window
        """

        self.size = size
        self.qtile, self.screen = None, None
        self.src_widget = src_widget

        configurable.Configurable.__init__(self, **config)
        self.add_defaults(NotifyWindow.defaults)

        self.widgets = widgets
        self.saved_focus = None


    def _configure(self, qtile, screen):
        # no STRETCH widget are allowed
        if len(filter(lambda w: w.width_type == STRETCH, self.widgets)) > 0:
            raise confreader.ConfigError("No STRETCH widget allowed!")

        self.qtile = qtile
        self.screen = screen
        
        # initial width is set to the screen size
        # if width is adapted to the content then this attribute 
        # is set to True
        self.size_adapted = False

        # create an initial 'large' window that will not be shown
        self.window = window.Internal.create(
                        self.qtile,
                        self.x, self.y, self.width, self.height,
                        self.opacity
                     )

        for i in self.widgets:
            i._configure(qtile, self)
            
        # recompute the width of the window according to the content
        self.compute_size()
        self.size_adapted = True

        self.window.kill()
        # now, the real window
        self.window = window.Internal.create(
                        self.qtile,
                        self.x, self.y, self.width, self.height,
                        self.opacity
                     )

        for i in self.widgets:
            i._configure(qtile, self)

        self.drawer = drawer.Drawer(
                            self.qtile,
                            self.window.window.wid,
                            self.width,
                            self.height
                      )
        self.drawer.clear(self.background)

        self.window.handle_Expose = self.handle_Expose
        self.window.handle_EnterNotify = self.handle_EnterWindow
        self.window.handle_ButtonPress = self.handle_ButtonPress
        self.window.handle_ButtonRelease = self.handle_ButtonRelease
        self.window.handle_MotionNotify = self.handle_PointerMotion

        qtile.windowMap[self.window.window.wid] = self.window
        self.window.unhide()

        # FIXME: These should be targeted better.
        hook.subscribe.setgroup(self.draw)
        hook.subscribe.changegroup(self.draw)

        
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


    def _resize(self, width, widgets):
        offset = 0
        for i in widgets:
            i.offset = offset
            offset += i.width

    def handle_Expose(self, e):
        self.draw()

    def get_widget_in_position(self, e):
        for i in self.widgets:
            if e.event_x < i.offset + i.width:
                return i

    def handle_PointerMotion(self, e):
        pass

    def handle_EnterWindow(self, e):
        pass
             
    def handle_LeaveWindow(self, e):
        pass

    def handle_ButtonPress(self, e):
        pass

    def handle_ButtonRelease(self, e):
        pass


    def widget_grab_keyboard(self, widget):
        pass

    def widget_ungrab_keyboard(self):
        pass


    def draw(self):
        self._resize(self.width, self.widgets)
        for i in self.widgets:
            i.draw()
        if self.widgets:
            end = i.offset + i.width
            if end < self.width:
                self.drawer.draw(end, self.width - end)


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
            return self.size[0]
        elif self.size:
            return min(self.size[0], self.screen.width)
        else:
            return self.screen.width


    @property
    def height(self):
        if self.size_adapted:
            return self.size[1]
        elif self.size:
            return min(self.size[1], self.screen.height)
        else:
            return self.screen.dheight


    def geometry(self):
        return self.x, self.y, self.width, self.height

    def _items(self, name):
        if name == "screen":
            return True, None

    def _select(self, name, sel):
        if name == "screen":
            return self.screen

    def info(self):
        return dict(
            x = self.x,
            y = self.y,
            width = self.width,
            height = self.height,
            widget = self.src.widget,
            widgets = [i.info() for i in self.widgets],
        )

    def cmd_info(self):
        """
            Info for this object.
        """
        return self.info()
