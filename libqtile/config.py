import command, hook, utils, xcbq

class Key:
    """
        Defines a keybinding.
    """
    def __init__(self, modifiers, key, *commands):
        """
            - modifiers: A list of modifier specifications. Modifier
            specifications are one of: "shift", "lock", "control", "mod1",
            "mod2", "mod3", "mod4", "mod5".

            - key: A key specification, e.g. "a", "Tab", "Return", "space".

            - *commands: A list of lazy command objects generated with the
            command.lazy helper. If multiple Call objects are specified, they
            are run in sequence.
        """
        self.modifiers = modifiers
        self.key = key
        self.commands = commands
        if key not in xcbq.keysyms:
            raise utils.QtileError("Unknown key: %s" % key)
        self.keysym = xcbq.keysyms[key]
        try:
            self.modmask = utils.translateMasks(self.modifiers)
        except KeyError, v:
            raise utils.QtileError(v)

    def __repr__(self):
        return "Key(%s, %s)" % (self.modifiers, self.key)

class Drag(object):
    """
        Defines binding of a mouse to some dragging action

        On each motion event command is executed
        with two extra parameters added
        x and y offset from previous move
    """
    def __init__(self, modifiers, button, *commands, **kw):
        self.start = kw.pop('start', None)
        if kw:
            raise TypeError("Unexpected arguments: %s" % ', '.join(kw))
        self.modifiers = modifiers
        self.button = button
        self.commands = commands
        try:
            self.button_code = int(self.button.replace('Button', ''))
            self.modmask = utils.translateMasks(self.modifiers)
        except KeyError, v:
            raise utils.QtileError(v)

    def __repr__(self):
        return "Drag(%s, %s)" % (self.modifiers, self.button)


class Click(object):
    """
        Defines binding of a mouse click
    """
    def __init__(self, modifiers, button, *commands):
        self.modifiers = modifiers
        self.button = button
        self.commands = commands
        try:
            self.button_code = int(self.button.replace('Button', ''))
            self.modmask = utils.translateMasks(self.modifiers)
        except KeyError, v:
            raise utils.QtileError(v)

    def __repr__(self):
        return "Click(%s, %s)" % (self.modifiers, self.button)


class ScreenRect(object):

    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def __repr__(self):
        return '<%s %d,%d %d,%d>' % (
                self.__class__.__name__,
                self.x, self.y, self.width, self.height
        )

    def hsplit(self, columnwidth):
        assert columnwidth > 0
        assert columnwidth < self.width
        return (
                self.__class__(self.x, self.y, columnwidth, self.height),
                self.__class__(
                    self.x + columnwidth, self.y,
                    self.width - columnwidth, self.height
                )
        )

    def vsplit(self, rowheight):
        assert rowheight > 0
        assert rowheight < self.height
        return (
                self.__class__(self.x, self.y, self.width, rowheight),
                self.__class__(
                    self.x, self.y + rowheight,
                    self.width, self.height - rowheight
                )
        )


class Screen(command.CommandObject):
    """
        A physical screen, and its associated paraphernalia.
    """
    group = None
    previous_group = None

    def __init__(self, top=None, bottom=None, left=None, right=None,
                 x=None, y=None, width=None, height=None):
        """
            - top, bottom, left, right: Instances of bar objects, or None.

            Note that bar.Bar objects can only be placed at the top or the
            bottom of the screen (bar.Gap objects can be placed anywhere).

            x,y,width and height aren't specified usually unless you are
            using 'fake screens'.
        """
        self.top = top
        self.bottom = bottom
        self.left = left
        self.right = right
        self.qtile = None
        self.index = None
        self.x = x  # x position of upper left corner can be > 0
                    # if one screen is "right" of the other
        self.y = y
        self.width = width
        self.height = height

    def _configure(self, qtile, index, x, y, width, height, group):
        self.qtile = qtile
        self.index = index
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.setGroup(group)
        for i in self.gaps:
            i._configure(qtile, self)

    @property
    def gaps(self):
        lst = []
        for i in [self.top, self.bottom, self.left, self.right]:
            if i:
                lst.append(i)
        return lst

    @property
    def dx(self):
        return self.x + self.left.size if self.left else self.x

    @property
    def dy(self):
        return self.y + self.top.size if self.top else self.y

    @property
    def dwidth(self):
        val = self.width
        if self.left:
            val -= self.left.size
        if self.right:
            val -= self.right.size
        return val

    @property
    def dheight(self):
        val = self.height
        if self.top:
            val -= self.top.size
        if self.bottom:
            val -= self.bottom.size
        return val

    def get_rect(self):
        return ScreenRect(self.dx, self.dy, self.dwidth, self.dheight)

    def setGroup(self, new_group):
        """
        Put group on this screen
        """
        if new_group.screen == self:
            return

        self.previous_group = self.group

        if new_group is None:
            return

        if new_group.screen:
            # g1 <-> s1 (self)
            # g2 (new_group) <-> s2 to
            # g1 <-> s2
            # g2 <-> s1
            g1 = self.group
            s1 = self
            g2 = new_group
            s2 = new_group.screen

            s2.group = g1
            g1._setScreen(s2)
            s1.group = g2
            g2._setScreen(s1)
        else:
            old_group = self.group
            self.group = new_group

            # display clients of the new group and then hide from old group
            # to remove the screen flickering
            new_group._setScreen(self)

            if old_group is not None:
                old_group._setScreen(None)

        hook.fire("setgroup")
        hook.fire("focus_change")
        hook.fire("layout_change",
                  self.group.layouts[self.group.currentLayout],
                  self.group)

    def _items(self, name):
        if name == "layout":
            return True, range(len(self.group.layouts))
        elif name == "window":
            return True, [i.window.wid for i in self.group.windows]
        elif name == "bar":
            return False, [x.position for x in self.gaps]

    def _select(self, name, sel):
        if name == "layout":
            if sel is None:
                return self.group.layout
            else:
                return utils.lget(self.group.layouts, sel)
        elif name == "window":
            if sel is None:
                return self.group.currentWindow
            else:
                for i in self.group.windows:
                    if i.window.wid == sel:
                        return i
        elif name == "bar":
            return getattr(self, sel)

    def resize(self, x=None, y=None, w=None, h=None):
        x = x or self.x
        y = y or self.y
        w = w or self.width
        h = h or self.height
        self._configure(self.qtile, self.index, x, y, w, h, self.group)
        for bar in [self.top, self.bottom, self.left, self.right]:
            if bar:
                bar.draw()
        self.group.layoutAll()

    def cmd_info(self):
        """
            Returns a dictionary of info for this screen.
        """
        return dict(
            index=self.index,
            width=self.width,
            height=self.height,
            x=self.x,
            y=self.y
        )

    def cmd_resize(self, x=None, y=None, w=None, h=None):
        """
            Resize the screen.
        """
        self.resize(x, y, w, h)

    def cmd_nextgroup(self, skip_empty=False, skip_managed=False):
        """
            Switch to the next group.
        """
        n = self.group.nextGroup(skip_empty, skip_managed)
        self.setGroup(n)
        return n.name

    def cmd_prevgroup(self, skip_empty=False, skip_managed=False):
        """
            Switch to the previous group.
        """
        n = self.group.prevGroup(skip_empty, skip_managed)
        self.setGroup(n)
        return n.name

    def cmd_togglegroup(self, groupName=None):
        """
            Switch to the selected group or to the previously active one.
        """
        group = self.qtile.groupMap.get(groupName)
        if group in (self.group, None):
            group = self.previous_group
        self.setGroup(group)


class Group(object):
    """
    Represents a "dynamic" group. These groups can spawn apps, only allow
    certain Matched windows to be on them, hide when they're not in use, etc.
    """
    def __init__(self, name, matches=None, exclusive=False,
                 spawn=None, layout=None, persist=True, init=True,
                 layout_opts=None, screen_affinity=None):
        """
        :param name: the name of this group
        :type name: string
        :param matches: list of ``Match`` objects whose  windows will be assigned to this group
        :type matches: default ``None``
        :param exclusive: when other apps are started in this group, should we allow them here or not?
        :type exclusive: boolean
        :param spawn: this will be ``exec()`` d when the group is created
        :type spawn: string
        :param layout: the default layout for this group (e.g. 'max' or 'stack')
        :type layout: string
        :param persist: should this group stay alive with no member windows?
        :type persist: boolean
        :param init: is this group alive when qtile starts?
        :type init: boolean

        """
        self.name = name
        self.exclusive = exclusive
        self.spawn = spawn
        self.layout = layout
        self.persist = persist
        self.init = init
        if matches is None:
            matches = []
        self.matches = matches
        self.layout_opts = layout_opts or {}

        self.screen_affinity = screen_affinity

class Match(object):
    """
        Match for dynamic groups
        It can match by title, class or role.
    """
    def __init__(self, title=None, wm_class=None, role=None, wm_type=None):
        """

        ``Match`` supports both regular expression objects (i.e. the result of
        ``re.compile()``) or strings (match as a "include" match). If a window
        matches any of the things in any of the lists, it is considered a
        match.

        :param title: things to match against the title
        :param wm_classes: things to match against the WM_CLASS atom
        :param role: things to match against the WM_ROLE atom
        :param wm_type: things to match against the WM_TYPE atom
        """
        if not title:
            title = []
        if not wm_class:
            wm_class = []
        if not role:
            role = []
        if not wm_type:
            wm_type = []
        self._rules = [('title', t) for t in title]
        self._rules += [('wm_class', w) for w in wm_class]
        self._rules += [('role', r) for r in  role]
        self._rules += [('wm_type', r) for r in  wm_type]

    def compare(self, client):
        for _type, rule in self._rules:
            match_func = getattr(rule, 'match', None) or getattr(rule, 'count')

            if _type == 'title':
                value = client.name
            elif _type == 'wm_class':
                value = client.window.get_wm_class()
                if value and len(value) > 1:
                    value = value[1]
                elif value:
                    value = value[0]
            elif _type == 'wm_type':
                value = client.window.get_wm_type()
            else:
                value = client.window.get_wm_window_role()

            if value and match_func(value):
                return True
        return False

    def map(callback, clients):
        """ Apply callback to each client that matches this Match """
        for c in clients:
            if self.compare(c):
                callback(c)

class Rule(object):
    """
        A Rule contains a Match object, and a specification about what to do
        when that object is matched.
    """
    def __init__(self, match, group=None, float=False, intrusive=False):
        """
        :param match: ``Match`` object associated with this ``Rule``
        :param float: auto float this window?
        :param intrusive: override the group's exclusive setting?
        """
        self.match = match
        self.group = group
        self.float = float
        self.intrusive = intrusive

    def matches(self, w):
        return self.match.compare(w)
