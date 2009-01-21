from base import Layout, SubLayout, Rect
from .. import command, utils
from .. theme import Theme

class ClientStack(Layout):
    name="tile"
    ADD_TO_TOP, ADD_TO_BOTTOM, ADD_TO_NEXT, ADD_TO_PREVIOUS = \
        (1, 2, 3, 4)
    FOCUS_TO_TOP, FOCUS_TO_BOTTOM, \
    FOCUS_TO_NEXT, FOCUS_TO_PREVIOUS, \
    FOCUS_TO_LAST_FOCUSED = \
        (1, 2, 3, 4, 5)
    def __init__(self, SubLayouts, theme=Theme({}), add_mode=ADD_TO_TOP,
                 focus_mode=FOCUS_TO_TOP,
                 focus_history_length=10, mouse_warp = False):
        Layout.__init__(self)
        # store constructor values #
        self.theme = theme
        self.add_mode = add_mode
        self.focus_mode = focus_mode
        self.focus_history_length = focus_history_length
        self.mouse_warp = mouse_warp
        # initialise other values #
        self.clients = []
        self.focus_history = []
        self.normal_border, self.active_border, self.focused_border = \
            None, None, None
        self.sublayouts = []
        self.current_sublayout = -1
        self.SubLayouts = SubLayouts

    def layout(self, windows):
        sl = self.sublayouts[self.current_sublayout]
        rect = Rect(self.group.screen.dx,
                    self.group.screen.dy,
                    self.group.screen.dwidth,
                    self.group.screen.dheight,
                    )
        sl.layout(rect, [c for c in windows if c in sl.clients])
                
    def clone(self, group):
        print "CLONING, group is" , group
        print "SCREEN IS", group.screen
        if not self.active_border:
            def color(color):
                colormap = group.qtile.display.screen().default_colormap
                return colormap.alloc_named_color(color).pixel
            self.active_border = color(self.theme["clientstack_border_active"])
            self.focused_border = color(self.theme["clientstack_border_focus"])
            self.normal_border = color(self.theme["clientstack_border_normal"])
        c = Layout.clone(self, group)
        c.clients = []
        c.focus_history = []
        c.sublayouts = []
        for SL, kwargs in self.SubLayouts:
            print "creating sublayouts id is", id(c)
            c.sublayouts.append(SL(c, #pass the new clientstack!!!!!
                                   self.theme,
                                   **kwargs
                                   ))
        c.current_sublayout = 0
        return c

    def focus(self, c):
        self.focus_history.insert(0, c)
        self.focus_history = self.focus_history[:self.focus_history_length]
        for sl in self.sublayouts:
            sl.focus(c)

    def add(self, c):
        if self.add_mode == ClientStack.ADD_TO_TOP:
            self.clients.insert(0, c)
        elif self.add_mode == ClientStack.ADD_TO_BOTTOM:
            self.clients.append(c)
        elif self.add_mode in (ClientStack.ADD_TO_NEXT, 
                               ClientStack.ADD_TO_PREVIOUS):
            if self.focus['current'] in self.clients:
                pos = self.clients.index(self.focus['current'])
                offset = (1 if self.add_mode == ClientStack.ADD_TO_NEXT \
                              else 0)
                self.clients.insert(pos+offset, c)
            else:
                #bleh, just add it to the top???
                #TODO: define better behaviour
                self.clients.insert(0, c)
        else:
            raise NotImplementedError, "This mode is not catered for"
        print "done adding, self.clients is", self.clients
        print "id is in addclientstack", id(self)
        for sl in self.sublayouts:
            print "attempting to add it to the sublayout %s" % sl.__class__.__name__
            sl.add(c)

    def remove(self, c):
        position = 0
        if c in self.clients:
            position = self.clients.index(c)
            self.clients.remove(c)
            for sl in self.sublayouts:
                sl.remove(c)
            while c in self.focus_history:
                self.focus_history.remove(c)
        if not self.clients:
            return None
        elif self.focus_mode == ClientStack.FOCUS_TO_TOP:
            return self.clients[0]
        elif self.focus_mode == ClientStack.FOCUS_TO_BOTTOM:
            return self.clients[-1]
        elif self.focus_mode == ClientStack.FOCUS_TO_NEXT:
            return self.clients[position]
        elif self.focus_mode == ClientStack.FOCUS_TO_PREVIOUS:
            return self.clients[position-1]
        elif self.focus_mode == ClientStack.FOCUS_TO_LAST_FOCUSED and self.focus_history:
            return self.focus_history[0]
        else:
            return None

    def index_of(self, client):
        print "indexing", client
        print "self.clients is ", self.clients
        return self.clients.index(client)

    def change_focus(self, offset):
        if self.focus['current'] in self.clients:
            current_focus_index = self.clients.index(self.focus['current'])
        else:
            current_focus_index = 0
        current_focus_index += offset
        self.group.focus(self.clients[current_focus_index], self.mouse_warp)

    def cmd_up(self):
        """
            Switch focus to the previous window in the stack
        """
        self.change_focus(-1)
        
    def cmd_down(self):
        """
            Switch focus to the next window in the stack
        """
        self.change_focus(1)
        
