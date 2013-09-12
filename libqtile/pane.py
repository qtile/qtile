import drawer
import hook
import configurable
import window
import command

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


class Pane(command.CommandObject, configurable.Configurable):
    
    defaults = [
        ("background", "#000000", "Background colour."),
        ("opacity",  1, "Pane window opacity.")
    ]

    def __init__(self, widgets, pos, size, hidden=False, **config):
        
        self.hidden = hidden
        self.widgets = widgets
        self.size = size
        if size:
            self._width, self._height = size
        self.pos = pos
        if pos:
            self._x, self._y = pos
        self.qtile = None
        self.screen = None
        self.saved_focus = None
        configurable.Configurable.__init__(self, **config)
        self.add_defaults(Pane.defaults)

    def _configure(self, qtile, screen):
        self.qtile = qtile
        self.screen = screen

        self.window = window.Internal.create(
            self.qtile,
            self.x, self.y, 
            self.width, self.height,
            self.opacity
        )

        self._configure_drawer()
        self._configure_window_handle()

        if not self.hidden:
            qtile.windowMap[self.window.window.wid] = self.window
            self.window.unhide()

        for i in self.widgets:
            i._configure(qtile,self)

        # FIXME: These should be targeted better.
        hook.subscribe.setgroup(self.draw)
        hook.subscribe.changegroup(self.draw)

    def _configure_drawer(self):
        self.drawer = drawer.Drawer(
            self.qtile,
            self.window.window.wid,
            self.width, self.height
        )
        self.drawer.clear(self.background)

    def _configure_window_handle(self):
        self.window.handle_Expose = self.handle_Expose
        self.window.handle_EnterNotify = self.handle_EnterWindow
        self.window.handle_ButtonPress = self.handle_ButtonPress
        self.window.handle_ButtonRelease = self.handle_ButtonRelease
        self.window.handle_MotionNotify = self.handle_PointerMotion
        self.window.handle_LeaveNotify = self.handle_LeaveWindow

    def _unhide(self):
        if self.window.window.wid not in qtile.windowMap: 
            qtile.windowMap[self.window.window.wid] = self.window
        self.window.unhide()


    def _resize(self, width, widgets):
        stretches = [i for i in widgets if i.width_type == STRETCH]
        if stretches:
            stretchspace = width - sum(
                [i.width for i in widgets if i.width_type != STRETCH]
            )
            stretchspace = max(stretchspace, 0)
            astretch = stretchspace / len(stretches)
            for i in stretches:
                i.width = astretch
            if astretch:
                i.width += stretchspace % astretch

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

    def widget_ungrab_keyboard(self, widget):
        pass

    def draw(self):
        stretches = [i for i in self.widgets if i.width_type == STRETCH]
        self._resize(self.width, self.widgets)
        for i in self.widgets:
            i.draw()
        if self.widgets:
            end = i.offset + i.width
            if end < self.width:
                self.drawer.draw(end, self.width - end)


    @property
    def x(self):
        return self._x if self.pos else 0

    @x.setter
    def x(self, val):
        self._x = val

    @property
    def y(self):
        return self._y if self.pos else 0
        
    @y.setter
    def y(self, val):
        self._y = val

    @property
    def width(self):
        return self._width if self.size else self.screen.width

    @width.setter
    def width(self, val):
        self._width = val

    @property
    def height(self):
        return self._height if self.size else self.screen.dheight
        
    @height.setter
    def height(self, val):
        self._height = val

    def geometry(self):
        return (self.x, self.y, self.width, self.height)

    def _items(self, name):
        if name == "screen":
            return (True, None)

    def _select(self, name, sel):
        if name == "screen":
            return self.screen

    def info(self):
        return dict(
            x = self.x,
            y = self.y,
            width = self.width,
            height = self.height,
            widgets = [i.info() for i in self.widgets],
            window = self.window.window.wid,
        )

    def cmd_info(self):
        """
            Info for this object.
        """
        return self.info()
