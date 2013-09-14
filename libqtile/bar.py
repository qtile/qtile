import configurable
from libqtile import pane
from xcb.xproto import EventMask
import confreader
import obj

class Bar(pane.Pane, configurable.Configurable):
    """
        A bar, which can contain widgets. Note that bars can only be placed at
        the top or bottom of the screen.
    """


    def __init__(self, widgets, size, **config):
        """
        - widgets: A list of widget objects.
        - size: The height of the bar.
        """
        pane.Pane.__init__(self, widgets, None, None)
        self.size = size
        self.popup_window = dict() 

    def _configure(self, qtile, screen):
        if not self in [screen.top, screen.bottom]:
            raise confreader.ConfigError(
                "Bars must be at the top or the bottom of the screen."
            )
        if len(filter(lambda w: w.width_type == obj.STRETCH, self.widgets)) > 1:
            raise confreader.ConfigError("Only one STRETCH widget allowed!")

        pane.Pane._configure(self, qtile, screen)
        
        for i in self.widgets:
            qtile.registerWidget(i)

    def _configure_window_handle(self):
        self.window.handle_Expose = self.handle_Expose
        self.window.handle_ButtonPress = self.handle_ButtonPress
        self.window.handle_ButtonRelease = self.handle_ButtonRelease
        self.window.handle_MotionNotify = self.handle_PointerMotion
        self.window.handle_LeaveNotify = self.handle_LeaveWindow
        # add a PointerMotion event handler to get position inside the bar and allow
        # "over" widget action 
        self.window._windowMask = self.window._windowMask | EventMask.PointerMotion
        self.window.window.set_attribute(eventmask=self.window._windowMask)


    def _resize(self, width, widgets):
        stretches = [i for i in widgets if i.width_type == obj.STRETCH]
        if stretches:
            stretchspace = width - sum(
                [i.width for i in widgets if i.width_type != obj.STRETCH]
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


    def handle_PointerMotion(self, e):
        widget = self.get_widget_in_position(e)
        if widget:
            widget.pointer_over(e.event_x - widget.offset,
                                e.event_y, e.detail)



    def handle_EnterWindow(self, e):
        widget = self.get_widget_in_position(e)
        if widget:
            widget.enter_window(e.event_x - widget.offset,
                                e.event_y, e.detail)
             
    def handle_LeaveWindow(self, e):
        widget = self.get_widget_in_position(e)
        if widget:
            widget.leave_window(e.event_x - widget.offset,
                                e.event_y, e.detail)

    def handle_ButtonPress(self, e):
        widget = self.get_widget_in_position(e)
        if widget:
            widget.button_press(
                e.event_x - widget.offset,
                e.event_y,
                e.detail
            )

    def handle_ButtonRelease(self, e):
        widget = self.get_widget_in_position(e)
        if widget:
            widget.button_release(
                e.event_x - widget.offset,
                e.event_y,
                e.detail
            )

    def widget_grab_keyboard(self, widget):
        """
            A widget can call this method to grab the keyboard focus
            and receive keyboard messages. When done,
            widget_ungrab_keyboard() must be called.
        """
        self.window.handle_KeyPress = widget.handle_KeyPress
        self.saved_focus = self.qtile.currentWindow
        self.window.window.set_input_focus()

    def widget_ungrab_keyboard(self):
        """
            Removes the widget's keyboard handler.
        """
        del self.window.handle_KeyPress
        if not self.saved_focus is None:
            self.saved_focus.window.set_input_focus()

    def info(self):
        return dict(
            width=self.width,
            position=self.position,
            widgets=[i.info() for i in self.widgets],
            window=self.window.window.wid
        )

    def cmd_fake_button_press(self, screen, position, x, y, button=1):
        """
            Fake a mouse-button-press on the bar. Co-ordinates are relative
            to the top-left corner of the bar.

            :screen The integer screen offset
            :position One of "top", "bottom", "left", or "right"
        """
        class _fake:
            pass
        fake = _fake()
        fake.event_x = x
        fake.event_y = y
        fake.detail = button
        self.handle_ButtonPress(fake)

    @property
    def x(self):
        screen = self.screen
        if screen.right is self:
            return screen.dx + screen.dwidth
        else:
            return screen.x

    @property
    def y(self):
        screen = self.screen
        if screen.top is self:
            return screen.y
        elif screen.bottom is self:
            return screen.dy + screen.dheight
        elif screen.left is self:
            return screen.dy
        elif screen.right is self:
            return screen.y + screen.dy

    @property
    def width(self):
        screen = self.screen
        if self in [screen.top, screen.bottom]:
            return screen.width
        else:
            return self.size

    @property
    def height(self):
        screen = self.screen
        if self in [screen.top, screen.bottom]:
            return self.size
        else:
            return screen.dheight
        
    @property
    def position(self):
        for i in ["top", "bottom", "left", "right"]:
            if getattr(self.screen, i) is self:
                return i
