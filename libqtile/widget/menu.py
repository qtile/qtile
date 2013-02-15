from .. import bar, manager, drawer, window, hook
import base
import button


class _MenuMarkup():
    """
    An object representing a menu's structure
    will contain what to do with entries when clicked

    For example _MenuMarkup(["File",["New",[[".py",newpyfunc],
        [".c",newcfunc]]],["Quit",quitfunc]],
        ["Edit",["Copy",copyfunc],["Paste",pastefunc]]
    )
    Represents the menu with File and Edit as top level entries
        where file has New and Quit as
    submenu entries, and Edit has Copy and Paste as submenu entries.

    In addition, New has .py and .c as submenu entries.

    All of the submenu entries, when clicked,
        call their corresponding functions.
    """

    def __init__(self, *entries):
        self.tree = entries
        self.names = [i[0] for i in entries]
        self.entries = [i[1:] for i in entries]  # misnomer


class _Menu(base._Widget):

    defaults = manager.Defaults()

    def __init__(self, menu=None):
        self.menu = menu
        self.buttons = []
        for i in xrange(len(self.menu.names)):
            self.buttons.append(_MenuButton(
                self.menu.names[i],
                self.menu.entries[i], self)
            )
        base._Widget.__init__(self, bar.CALCULATED)

    def _configure(self, qtile, bar):
        self.qtile, self.bar = qtile, bar
        self.drawer = drawer.Drawer(
            self.qtile,
            self.win.wid,
            self.bar.width,
            self.bar.height
        )
        w = 0
        for i in self.buttons:
            i._configure(qtile, bar)
            i.set_draweroffset((self.offset or 0) + w)
            w += i.width

    def calculate_width(self):
        self.zones = []
        w = 0
        for i in self.buttons:
            self.zones.append(w)
            w += i.calculate_width()
        return w

    def draw(self):
        self.drawer.clear(self.bar.background)
        off = 0
        for i in self.buttons:
            i.drawer.clear(i.background)
            i.layout.draw(
                i.actual_padding or 0,
                int(i.bar.height / 2.0 - i.layout.height / 2.0)
            )
            i.drawer.draw(off, i.calculate_width())
            off = off + i.calculate_width()

    def click(self, x, y, button):
        self.calculate_width()
        i = 0
        for i in range(len(self.buttons) - 1):
            if x > self.zones[i + 1]:
                i += 1
            else:
                break
        self.buttons[i].click((self.zones[i]), y, button)


class _MenuButton(button._Button):

    defaults = manager.Defaults(
        ("font", "Arial", "Menu font"),
        ("fontsize", None, "Menu pixel size. Calculated if None."),
        ("padding", 7, "Menu padding. Calculated if None."),
        ("background", "000000", "Background colour"),
        ("foreground", "ffffff", "Foreground colour")
    )

    def __init__(self, name=None, submenu=None, parent=None):
        button._Button.__init__(self, name, bar.CALCULATED, self.open_submenu)
        self.name = name
        self.submenu = submenu
        self.parent = parent or []
        self.buttons = []
        self.mdrawer = _MenuDrawer(0, 0, 0, 0)
        self.b = False

    def set_draweroffset(self, x):
        del self.mdrawer
        self.mdrawer = _MenuDrawer(
            x,
            self.bar.height, 300,
            len(self.submenu) * self.bar.height
        )
        self.mdrawer._configure(self.qtile, self.bar.screen)
        for i in self.buttons:
            i._configure(self.qtile, self.mdrawer)
        self.mdrawer.addwidgets(self.buttons)

    def open_submenu(self, x, y, butto):
        for i in self.parent.buttons:
            if i != self and hasattr(i, 'mdrawer') and i.mdrawer.visible:
                self.b = True
                i.b = not i.b
                i.mdrawer.set_visible(False)
        self.mdrawer.set_visible(self.b)
        self.b = not self.b

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)
        self.layout = self.drawer.textlayout(
            self.text,
            self.foreground,
            self.font,
            self.fontsize
        )
        for i in self.submenu:
            k = _MenuEntry(i[0], 100, self.bar.height)
            self.buttons.append(k)

    def draw(self):
        self.drawer.clear(self.background or self.bar.background)
        self.layout.draw(
            self.actual_padding or 0,
            int(self.bar.height / 2.0 - self.layout.height / 2.0)
        )
        self.drawer.draw(self.offset, self.width)


class _MenuEntry(base._TextBox):

    defaults = manager.Defaults(
        ("font", "Arial", "Main font"),
        ("fontsize", 10, "Font size. Calculated if None."),
        ("padding", None, "Padding Calculated if None."),
        ("background", "000000", "Background colour"),
        ("foreground", "ffffff", "Foreground colour")
    )

    def __init__(self, text=" ", width=bar.CALCULATED, height=None, **config):
        self.layout = None
        base._Widget.__init__(self, width, **config)
        self.text = text
        self.height = height

    def click(self, x, y, button):
        print self.text

    def _configure(self, qtile, bar):
        self.qtile, self.bar = qtile, bar
        self.height = self.height or bar.height
        self.drawer = drawer.OffsetDrawer(
            self.qtile,
            self.win.wid,
            self.bar.width,
            self.height,
            drawer.OFFSET_Y
        )
        self.layout = self.drawer.textlayout(
            self.text,
            self.foreground,
            self.font,
            self.fontsize
        )

    def draw(self):
        self.drawer.clear(self.background or self.bar.background)
        self.layout.draw(
            self.actual_padding or 0,
            int(self.height / 2.0 - self.layout.height / 2.0)
        )
        self.drawer.draw(self.offset, self.width)

    @property
    def fontsize(self):
        if self._fontsize is None:
            return self.height - self.height / 5
        else:
            return self._fontsize

    @fontsize.setter
    def fontsize(self, value):
        self._fontsize = value
        if self.layout:
            self.layout.font_size = value


class _MenuDrawer(bar._AnywhereBar):

    def handle_ButtonPress(self, e):
        for i in self.widgets:
            if e.event_y < i.offset + i.height:
                i.click(e.event_x, e.event_y - i.offset, e.detail)
                break

####################################
#                                  #
#    Specific Menus start here     #
#                                  #
####################################

class SampleMenu(_Menu):
    """
    Shitty example
    """

    def __init__(self):
        _Menu.__init__(self, _MenuMarkup(
            ["ab", ["a"], ["b"], ["c"]],
            ["cats", ["doop"], ["loop"], ["hoop"]]
        )
        )


##Make a debian/gnome menu class which opens programs like the gnome2 menu##

##Make a global menu##
