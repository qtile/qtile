# Copyright (c) 2008, Aldo Cortesi. All rights reserved.
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

import marshal, sys
import Xlib
from Xlib import X, Xatom, Xutil
import Xlib.protocol.event as event
import Xlib.error
import command, utils
import manager

class _Window(command.CommandObject):
    possible_states = ["normal", "minimised", "floating", "maximised", "fullscreen"]
    def __init__(self, window, qtile):
        self.window, self.qtile = window, qtile
        self.hidden = True
        window.change_attributes(event_mask=self._windowMask)
        self.x, self.y, self.width, self.height = None, None, None, None
        self.borderwidth = 0
        self.name = "<no name>"
        self.states = ["normal"]
        self.window_type = "normal"
        g = self.window.get_geometry()
        self.floatDimensions = {
            'x': g.x, 'y': g.y, 
            'w': g.width, 'h': g.height
            }
        self.hints = {
            'input': True,
            'state': Xutil.NormalState, #Normal state
            'icon_pixmap': None,
            'icon_window': None,
            'icon_x': 0,
            'icon_y': 0,
            'icon_mask': 0,
            'window_group': None,
            'urgent': False,
            }
        self.updateName()
        self.updateHints()
        self.updateWindowType()

    def setState(self, state, val):
        if state not in self.possible_states:
            print "No such state: %s" % state
            return
        oldstate = self.states[0]
        if val:
            if self.states[0] != state:
                self.states.insert(0, state)
        else:
            if self.states[0] == state:
                self.states = self.states[1:]
            if not self.states:
                self.states = ["normal"]
        if oldstate != self.states[0]:
            manager.Hooks.call_hook("client-state-changed", state, self)
    def getState(self, state):
        if self.states[0] == state:
            return True
        else:
            return False

    def getMinimised(self):
        return self.getState("minimised")
    def setMinimised(self, val):
        self.setState("minimised", val)
    minimised = property(getMinimised, setMinimised)

    def getFloating(self):
        return self.getState("floating")
    def setFloating(self, val):
        self.setState("floating", val)
    floating = property(getFloating, setFloating)

    def getMaximised(self):
        return self.getState("maximised")
    def setMaximised(self, val):
        self.setState("maximised", val)
    maximised = property(getMaximised, setMaximised)

    def getFullscreen(self):
        return self.getState("fullscreen")
    def setFullscreen(self, val):
        self.setState("fullscreen", val)
    fullscreen = property(getFullscreen, setFullscreen)

    def updateName(self):
        try:
            self.name = self.window.get_wm_name()
            self.qtile.event.fire("window_name_change")
        except (Xlib.error.BadWindow, Xlib.error.BadValue):
            # This usually means the window has just been deleted, and a new
            # focus will be acquired shortly. We don't raise an event for this.
            pass

    def setWindowType(self, window_type):
        try:
            oldtype = self._type
        except:
            oldtype = None
        self._type = window_type
        if self._type != oldtype:
            manager.Hooks.call_hook("client-type-changed", self)
    def getWindowType(self):
        return self._type
    window_type = property(getWindowType, setWindowType)

    def updateWindowType(self):
        '''
        http://standards.freedesktop.org/wm-spec/wm-spec-latest.html#id2551529
        Also a type "pseudo-normal" is used to indicicate a window that wants 
        to be treated as if it were normal, but isn't actually.
        '''
        types = {
            '_NET_WM_WINDOW_TYPE_DESKTOP': "desktop",
            '_NET_WM_WINDOW_TYPE_DOCK': "dock",
            '_NET_WM_WINDOW_TYPE_TOOLBAR': "toolbar", 
            '_NET_WM_WINDOW_TYPE_MENU': "menu",
            '_NET_WM_WINDOW_TYPE_UTILITY': "utility",
            '_NET_WM_WINDOW_TYPE_SPLASH': "splash",
            '_NET_WM_WINDOW_TYPE_DIALOG': "dialog",
            '_NET_WM_WINDOW_TYPE_DROPDOWN_MENU': "dropdown",
            '_NET_WM_WINDOW_TYPE_POPUP_MENU': "menu",
            '_NET_WM_WINDOW_TYPE_TOOLTIP': "tooltip",
            '_NET_WM_WINDOW_TYPE_NOTIFICATION': "notification",
            '_NET_WM_WINDOW_TYPE_COMBO': "combo",
            '_NET_WM_WINDOW_TYPE_DND': "dnd",
            '_NET_WM_WINDOW_TYPE_NORMAL': "normal",
        }
        d = self.qtile.display
        try:
            win_type = self.window.get_full_property(
                d.intern_atom('_NET_WM_WINDOW_TYPE'),
                Xatom.ATOM,
                )
        except:
            return
        if win_type is None:
            self.window_type = "normal"
            return
        type_atom = win_type.value[0]
        try:
            atom_name = d.get_atom_name(type_atom)
        except AttributeError:
            return
        self.window_type = types[atom_name]

    def updateHints(self):
        ''' 
          update the local copy of the window's WM_HINTS
          http://tronche.com/gui/x/icccm/sec-4.html#WM_HINTS
        '''
        
        def update_hint(hint, value, hook=True):
            if self.hints[hint] != value:
                self.hints[hint] = value
                if hook:
                    manager.Hooks.call_hook(
                        "client-%s-hint-changed" % hint, 
                        self)
        try:
            h = self.window.get_wm_hints()
        except (Xlib.error.BadWindow, Xlib.error.BadValue):
            return
        if h is None:
            return

        flags = h.flags
        if flags & Xutil.InputHint:
            update_hint('input', h.input)
        if flags & Xutil.StateHint:
            update_hint('state', h.initial_state)
        if flags & Xutil.IconPixmapHint:
            update_hint('icon_pixmap', h.icon_pixmap)
        if flags & Xutil.IconWindowHint:
            update_hint('icon_window', h.icon_window)
        if flags & Xutil.IconPositionHint:
            update_hint('icon_x', h.icon_x, hook=False)
            update_hint('icon_y', h.icon_y, hook=False)
        if flags & Xutil.IconMaskHint:
            update_hint('icon_mask', h.icon_mask)
        if flags & Xutil.WindowGroupHint:
            update_hint('window_group', h.window_group)
        if flags & 256: #urgency_hint
            update_hint('urgent', True)
        else:
            update_hint('urgent', False)

    @property
    def urgent(self):
        return self.hints['urgent']

    def info(self):
        return dict(
            name = self.name,
            x = self.x,
            y = self.y,
            width = self.width,
            height = self.height,
            id = str(hex(self.window.id)),
            floatDimensions = self.floatDimensions,
            next_placement = self.next_placement,
        )

    def setOpacity(self, opacity):
        if 0.0 <= opacity <= 1.0:
            real_opacity = int(opacity * 0xffffffff)
            self.window.change_property(
                self.qtile.display.get_atom('_NET_WM_WINDOW_OPACITY'),
                Xatom.CARDINAL,
                32,
                [real_opacity,],
                )
        else:
            return

    def getOpacity(self):
        opacity = self.window.get_property(
            self.qtile.display.get_atom('_NET_WM_WINDOW_OPACITY'),
            Xatom.CARDINAL,
            0,
            32
            )
        if not opacity:
            return 1.0
        else:
            value = opacity.value[0]
            as_float = round(
                (float(value)/0xffffffff),
                2  #2 decimal places
                )
            return as_float

    opacity = property(getOpacity, setOpacity)
            
    def notify(self):
        e = event.ConfigureNotify(
                window = self.window,
                event = self.window,
                x = self.x,
                y = self.y,
                width = self.width,
                height = self.height,
                border_width = self.borderwidth,
                override = False,
                above_sibling = X.NONE
        )
        self.window.send_event(e)

    def kill(self):
        if self.hasProtocol("WM_DELETE_WINDOW"):
            e = event.ClientMessage(
                    window = self.window,
                    client_type = self.qtile.display.intern_atom("WM_PROTOCOLS"),
                    data = [
                        # Use 32-bit format:
                        32,
                        # Must be exactly 20 bytes long:
                        [
                            self.qtile.display.intern_atom("WM_DELETE_WINDOW"),
                            X.CurrentTime,
                            0,
                            0,
                            0
                        ]
                    ]
            )
            self.window.send_event(e)
        else:
            self.window.kill_client()

    def hide(self):
        # We don't want to get the UnmapNotify for this unmap
        self.disableMask(X.StructureNotifyMask)
        self.window.unmap()
        self.resetMask()
        self.hidden = True

    def unhide(self):
        self.window.map()
        self.hidden = False

    def disableMask(self, mask):
        self.window.change_attributes(
            event_mask=self._windowMask&(~mask)
        )

    def resetMask(self):
        self.window.change_attributes(
            event_mask=self._windowMask
        )

    def place(self, x, y, width, height, border, borderColor):
        """
            Places the window at the specified location with the given size.
        """
        self.x, self.y, self.width, self.height = x, y, width, height
        self.window.configure(
            x=x,
            y=y,
            width=width,
            height=height,
            border_width=border
        )
        if borderColor is not None:
            self.window.change_attributes(
                border_pixel = borderColor
            )

    def focus(self, warp):
        if not self.hidden and self.hints['input']:
            self.window.set_input_focus(
                X.RevertToPointerRoot,
                X.CurrentTime
            )
            if warp:
                self.window.warp_pointer(0, 0)
        manager.Hooks.call_hook("client-focus", self)

    def hasProtocol(self, name):
        s = set()
        d = self.qtile.display
        for i in self.window.get_wm_protocols():
            s.add(d.get_atom_name(i))
        return name in s

    def setProp(self, name, data):
        self.window.change_property(
            self.qtile.atoms[name],
            self.qtile.atoms["python"],
            8,
            marshal.dumps(data)
        )

    def _items(self, name, sel):
        return None

    def _select(self, name, sel):
        return None

    def cmd_info(self):
        """
            Returns a dictionary of info for this object.
        """
        return self.info()


    def cmd_inspect(self):
        """
            Tells you more than you ever wanted to know about a window.
        """
        a = self.window.get_attributes()
        attrs = {
            "backing_store": a.backing_store,
            "visual": a.visual,
            "class": a.win_class,
            "bit_gravity": a.bit_gravity,
            "win_gravity": a.win_gravity,
            "backing_bit_planes": a.backing_bit_planes,
            "backing_pixel": a.backing_pixel,
            "save_under": a.save_under,
            "map_is_installed": a.map_is_installed,
            "map_state": a.map_state,
            "override_redirect": a.override_redirect,
            #"colormap": a.colormap,
            "all_event_masks": a.all_event_masks,
            "your_event_mask": a.your_event_mask,
            "do_not_propagate_mask": a.do_not_propagate_mask
        }
        props = [self.qtile.display.get_atom_name(x) for x in self.window.list_properties()]
        
        h = self.window.get_wm_normal_hints()
        if h:
            normalhints = dict(
                flags = h.flags,
                min_width = h.min_width,
                min_height = h.min_height,
                max_width = h.max_width,
                max_height = h.max_height,
                width_inc = h.width_inc,
                height_inc = h.height_inc,
                min_aspect = dict(num=h.min_aspect["num"], denum=h.min_aspect["denum"]),
                max_aspect = dict(num=h.max_aspect["num"], denum=h.max_aspect["denum"]),
                base_width = h.base_width,
                base_height = h.base_height,
                win_gravity = h.win_gravity
            )
        else:
            normalhints = None
        
        h = self.window.get_wm_hints()
        if h:
            hints = dict(
                flags = h.flags,
                input = h.input,
                initial_state = h.initial_state,
                icon_window = h.icon_window.id,
                icon_x = h.icon_x,
                icon_y = h.icon_y,
                window_group = h.window_group.id
            )
        else:
            hints = None

        protocols = []
        for i in self.window.get_wm_protocols():
            protocols.append(self.qtile.display.get_atom_name(i))

        state = self.window.get_wm_state()

        return dict(
            attributes=attrs,
            properties=props,
            name = self.window.get_wm_name(),
            wm_class = self.window.get_wm_class(),
            wm_transient_for = self.window.get_wm_transient_for(),
            protocols = protocols,
            wm_icon_name = self.window.get_wm_icon_name(),
            wm_client_machine = self.window.get_wm_client_machine(),
            normalhints = normalhints,
            hints = hints,
            state = state
        )


class Internal(_Window):
    """
        An internal window, that should not be managed by qtile.
    """
    _windowMask = X.StructureNotifyMask |\
                 X.PropertyChangeMask |\
                 X.EnterWindowMask |\
                 X.FocusChangeMask |\
                 X.ExposureMask |\
                 X.ButtonPressMask
    @classmethod
    def create(klass, qtile, background_pixel, x, y, width, height, opacity=1.0):
        win = qtile.root.create_window(
                    x, y, width, height, 0,
                    X.CopyFromParent, X.InputOutput,
                    X.CopyFromParent,
                    background_pixel = background_pixel,
                    event_mask = X.StructureNotifyMask | X.ExposureMask
               )
        i = Internal(win, qtile)
        i.place(x, y, width, height, 0, None)
        i.setProp("internal", True)
        i.opacity = opacity
        return i

    def __repr__(self):
        return "Internal(%s)"%self.name


class Window(_Window):
    _windowMask = X.StructureNotifyMask |\
                 X.PropertyChangeMask |\
                 X.EnterWindowMask |\
                 X.FocusChangeMask
    group = None
    def handle_EnterNotify(self, e):
        manager.Hooks.call_hook("client-mouse-enter", self)
        if self.group.currentWindow != self:
            self.group.focus(self, False)
        if self.group.screen and self.qtile.currentScreen != self.group.screen:
            self.qtile.toScreen(self.group.screen.index)

    def handle_ConfigureRequest(self, e):
        if e.value_mask & Xutil.XValue:
            self.floatDimensions['x'] = e.x
        if e.value_mask & Xutil.YValue:
            self.floatDimensions['y'] = e.y
        if e.value_mask & Xutil.WidthValue:
            self.floatDimensions['w'] = e.width
        if e.value_mask & Xutil.HeightValue:
            self.floatDimensions['h'] = e.height
        if self.group.screen:
            self.group.layout.configure(self)
            self.notify()

    def handle_PropertyNotify(self, e):
        name = self.qtile.display.get_atom_name(e.atom)
        if name == "WM_TRANSIENT_FOR":
            print >> sys.stderr, "transient"
        elif name == "WM_HINTS":
            self.updateHints()
            print >> sys.stderr, "hints"
        elif name == "WM_NORMAL_HINTS":
            print >> sys.stderr, "normal_hints"
        elif name == "WM_NAME":
            self.updateName()
            manager.Hooks.call_hook("client-name-updated", self)
        elif name == "_NET_WM_WINDOW_OPACITY":
            pass
        else:
            print >> sys.stderr, "Unknown window property: ", name

    def _items(self, name):
        if name == "group":
            return True, None
        elif name == "layout":
            return True, range(len(self.group.layouts))
        elif name == "screen":
            return True, None

    def _select(self, name, sel):
        if name == "group":
            return self.group
        elif name == "layout":
            if sel is None:
                return self.group.layout
            else:
                return utils.lget(self.group.layouts, sel)
        elif name == "screen":
            return self.group.screen

    def __repr__(self):
        return "Window(%s)"%self.name

    def cmd_kill(self):
        """
            Kill this window. Try to do this politely if the client support
            this, otherwise be brutal.
        """
        self.kill()

    def cmd_togroup(self, groupName):
        """
            Move window to a specified group.

            Examples:

                togroup("a")
        """
        group = self.qtile.groupMap.get(groupName)
        if group is None:
            raise command.CommandError("No such group: %s"%groupName)
        if self.group is not group:
            self.hide()
            self.group.remove(self)
            group.add(self)
            self.group.layoutAll()
            group.layoutAll()

    def cmd_move_floating(self, x, y):
        self.floatDimensions['x'] += x
        self.floatDimensions['y'] += y
        self.group.layoutAll()

    def cmd_move_to_screen_edge(self, edge):
        if edge == 'Left':
            self.floatDimensions['x'] = 0
        elif edge == 'Up':
            self.floatDimensions['y'] = 0
        elif edge == 'Right':
            self.floatDimensions['x'] = \
                self.group.screen.dwidth - self.floatDimensions['w']
        elif edge == 'Down':
            self.floatDimensions['y'] = \
                self.group.screen.dheight + self.group.screen.dy - self.floatDimensions['h']
        self.group.layoutAll()
        

    def cmd_resize_floating(self, xinc, yinc):
        self.floatDimensions['w'] += xinc
        self.floatDimensions['h'] += yinc
        self.group.layoutAll()

    def cmd_toggle_floating(self):
        self.floating = not self.floating
        if not self.floating and self.window_type in ("dialog", "utility"): #maybe add more here
            self.window_type = "pseudo-normal"
        elif self.window_type == "pseudo-normal":
            self.updateWindowType()
        self.group.layoutAll()

    def cmd_semitransparent(self):
        self.opacity = 0.5

    def cmd_opacity(self, opacity):
        self.opacity = opacity

    def cmd_minimise(self):
        self.minimised = True
        self.group.layoutAll()

    def cmd_unminimise(self):
        self.minimised = False
        self.group.layoutAll()

    def cmd_maximise(self):
        self.maximised = True
        self.group.layoutAll()
    
    def cmd_unmaximise(self):
        self.maximised = False
        self.group.layoutAll()

    def cmd_fullscreen(self):
        self.fullscreen = True
        self.group.layoutAll()

    def cmd_unfullscreen(self):
        self.fullscreen = True
        self.group.layoutAll()
