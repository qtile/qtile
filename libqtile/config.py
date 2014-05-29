import command
import hook
import sys
import utils
import xcbq


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

        It focuses clicked window by default
        If you want to prevent it pass focus=None as an argument
    """
    def __init__(self, modifiers, button, *commands, **kwargs):
        self.start = kwargs.get("start", None)
        self.focus = kwargs.get("focus", "before")
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

        It focuses clicked window by default
        If you want to prevent it pass focus=None as an argument
    """
    def __init__(self, modifiers, button, *commands, **kwargs):
        self.focus = kwargs.get("focus", "before")
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
            self.x, self.y,
            self.width, self.height
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
    def __init__(self, top=None, bottom=None, left=None, right=None,
                 x=None, y=None, width=None, height=None):
        """
            - top, bottom, left, right: Instances of bar objects, or None.

            Note that bar.Bar objects can only be placed at the top or the
            bottom of the screen (bar.Gap objects can be placed anywhere).

            x,y,width and height aren't specified usually unless you are
            using 'fake screens'.
        """

        self.group = None
        self.previous_group = None

        self.top = top
        self.bottom = bottom
        self.left = left
        self.right = right
        self.qtile = None
        self.index = None
        # x position of upper left corner can be > 0
        # if one screen is "right" of the other
        self.x = x
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
        lst.extend([
            i for i in [self.top, self.bottom, self.left, self.right] if i
        ])
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
        hook.fire(
            "layout_change",
            self.group.layouts[self.group.currentLayout],
            self.group
        )

    def _items(self, name):
        if name == "layout":
            return (True, range(len(self.group.layouts)))
        elif name == "window":
            return (True, [i.window.wid for i in self.group.windows])
        elif name == "bar":
            return (False, [x.position for x in self.gaps])

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
    def __init__(self, name, match=None, exclusive=False,
                 spawn=None, layout=None, layouts=None, persist=True, init=True,
                 layout_opts=None, screen_affinity=None, position=sys.maxint):
        """
        :param name: the name of this group
        :type name: string
        :param match: Windows matching this ``Match`` or ``MatchList`` object will be assigned to the group
        :type match: default ``None``
        :param exclusive: when other apps are started in this group, should we allow them here or not?
        :type exclusive: boolean
        :param spawn: this will be ``exec()`` d when the group is created
        :type spawn: string
        :param layout: the default layout for this group (e.g. 'max' or 'stack')
        :type layout: string
        :param layouts: the group layouts list overriding global layouts
        :type layouts: list
        :param persist: should this group stay alive with no member windows?
        :type persist: boolean
        :param init: is this group alive when qtile starts?
        :type init: boolean
        :param position: group position
        :type position: int

        """
        self.name = name
        self.exclusive = exclusive
        self.spawn = spawn
        self.layout = layout
        self.layouts = layouts or []
        self.persist = persist
        self.init = init
        self.match = match or Match()
        self.layout_opts = layout_opts or {}

        self.screen_affinity = screen_affinity
        self.position = position

class Match(object):
    """
        Match object for usage in dynamic groups but also in
        ordinary groups, rules and layouts

        ``Match`` supports both regular expression objects
        (``re.compile()``) or strings (match as a "include" match).
        If a window matches any of the things in any of the lists,
        it is considered a match.
    """
    class Match(Exception): pass
    class NoMatch(Exception): pass

    def __init__(self, title=None, wm_class=None, role=None, wm_type=None,
                 wm_instance_class=None, net_wm_pid=None):
        """"
        :param title: things to match against the title
        :param wm_class: things to match against the second string in
                         WM_CLASS atom
        :param role: things to match against the WM_ROLE atom
        :param wm_type: things to match against the WM_TYPE atom
        :param wm_instance_class: things to match against the first string in
               WM_CLASS atom
        :param net_wm_pid: things to match against the
               _NET_WM_PID (Integer) atom
        """
        self.title = title
        self.wm_class = wm_class
        self.role = role
        self.wm_type = wm_type
        self.wm_instance_class = wm_instance_class
        self.net_wm_pid = net_wm_pid

        self.match_all = False

    def _match_func_decorator(func, *args, **kwargs):
        """ Decorator
            Raises Match or NoMatch depending on match_all.
            To prevent wasteful processing in compare().
        """
        def wrapper(self, *args, **kwargs):
            result = func(self, *args, **kwargs)
            if result is True:
                if(not self.match_all):
                    raise self.Match
            if result is False:
                if(self.match_all):
                    raise self.NoMatch
            return result
        return wrapper

    @_match_func_decorator
    def _match_func(self, matchitem, matchsubject):
        """ Test matchitem is equal or contains items equal matchsubject """
        if matchitem:
            try:
                if matchitem.match(matchsubject):
                    return True
            except AttributeError:
                if matchitem == matchsubject:
                    return True
                try:
                    for item in matchitem:
                        try:
                            if item.match(matchsubject):
                                return True
                        except AttributeError:
                            if item == matchsubject:
                                return True
                except TypeError:
                    pass
            return False

    def compare(self, client):
        """ Return True if client matches this Match object """
        wm_class = client.window.get_wm_class()
        try:
            self._match_func(self.title, client.name)
            self._match_func(self.role, client.window.get_wm_window_role())
            self._match_func(self.wm_type, client.window.get_wm_type())
            self._match_func(self.net_wm_pid, client.window.get_net_wm_pid())
            if wm_class:
                self._match_func(self.wm_class, wm_class[1])
                self._match_func(self.wm_instance_class, wm_class[0])
        except self.NoMatch:
            return False
        except self.Match:
            return True

    def map(self, callback, clients):
        """
        Apply callback to each client that matches this Match.
        Callback must return False to continue processing.
        """
        for c in clients:
            if self.compare(c):
                if callback(c):
                    break

    def __add__(self, match):
        """ Concatenate Match objects - ``Match()+Match()``"""
        if not isinstance(match, self.__class__):
            raise utils.QtileError('Can not concatenate Match object. '
            'Only concatenate of same type.')
        params = {}
        for item in ('title', 'wm_class', 'role', 'wm_type', 'wm_instance_class', 'net_wm_pid'):
            if getattr(match, item, None) and getattr(self, item, None):
               try:
                   params[item]  = getattr(self, item)[:].extend(getattr(match, item))
               except TypeError:
                   params[item] = [getattr(self, item), getattr(match, item)]
            elif getattr(self, item, None):
                params[item] = getattr(self, item)
            elif getattr(match, item, None):
                params[item] = getattr(match, item)
        return Match(**params)

    def __call__(self, client):
        return self.compare(client)

    def __repr__(self):
        l = []
        l.append('%s(' %(self.__class__.__name__,))
        for item in ('title', 'wm_class', 'role', 'wm_type', 'wm_instance_class', 'net_wm_pid'):
            if getattr(self, item, None):
                l.append('%s=%s%s' %(item, repr(getattr(self, item)), ','))
        l.append(')')
        return ''.join(l).strip()

class MatchAll(Match):
    """

    ``Match`` supports both regular expression objects
    (``re.compile()``) or strings (match as a "include" match).
    If a window matches all of the things in any of the lists,
    it is considered a match.

    """
    def __init__(self, *args, **kwargs):
        """
        :param title: things to match against the title
        :param wm_class: things to match against the second string in
                         WM_CLASS atom
        :param role: things to match against the WM_ROLE atom
        :param wm_type: things to match against the WM_TYPE atom
        :param wm_instance_class: things to match against the first string in
               WM_CLASS atom
        :param net_wm_pid: things to match against the
               _NET_WM_PID (Integer) atom
        """
        super(MatchAll, self).__init__(*args, **kwargs)
        self.match_all = True

class MatchEverything(Match):
    """
    Everything is considered a match.
    """
    def __init__(self, *args, **kwargs):
        pass

    def compare(self, client):
        return True

    def map(self, callback, clients):
        """
        Apply callback to each client that matches this Match.
        Callback must return False to continue processing.
        """
        for c in clients:
            if callback(c):
                break

    def __add__(self, match):
        return self

    def __sub__(self, match):
        if isinstance(match, MatchEverything):
            return Match()
        return self

    def __repr__(self):
        return '%s()' %self.__class__.__name__

class MatchNothing(Match):
    """
    Nothing is considered a match.
    """
    def __init__(self, *args, **kwargs):
        pass

    def compare(self, client):
        return False

    def map(self, callback, clients):
        pass

    def __add__(self, match):
        if isinstance(match, MatchEverything):
            return MatchEverything()
        return self

    def __sub__(self, match):
        return self

    def __repr__(self):
        return '%s()' %self.__class__.__name__

class MatchList(list):
    """Container for Match objects and
    provide comparision on these objects."""
    def __init__(self, *args):
        super(MatchList, self).__init__()
        self.has_matcheverything = 0
        self.has_matchnothing    = 0
        for item in args:
            if isinstance(item, MatchEverything):
                self.has_matcheverything += 1
                self.append(item)
            elif isinstance(item, MatchNothing):
                self.has_matchnothing += 1
                self.append(item)
            elif isinstance(item, Match):
                self.append(item)
            else:
                raise utils.QtileError(
                "Invalid object put into %s" %self.__class__.__name__)

    def compare(self, client):
        if self.has_matcheverything > self.has_matchnothing:
            return True
        elif self.has_matchnothing > self.has_matcheverything:
            return False
        for match in self:
            if match.compare(client):
                return True

    def map(self, callback, clients):
        """
        Apply callback to each client that matches this MatchList.
        Callback must return False to continue processing.
        """
        for c in clients:
            if self.compare(c):
                if callback(c):
                    break

    def __call__(self, client):
        return self.compare(client)
    
    def __repr__(self):
        string = super(MatchList, self).__repr__()
        string = string.lstrip('[').rstrip(']')
        string = '%s(%s)' %(self.__class__.__name__, string)
        return string

class Rule(object):
    """
        A Rule contains a Match object, and a specification about what to do
        when that object is matched.
    """
    def __init__(self, match, group=None, float=False,
                 intrusive=False, break_on_match=True):
        """
        :param match: ``MatchList`` or ``Match`` object associated with this ``Rule``
        :param float: auto float this window?
        :param intrusive: override the group's exclusive setting?
        :param break_on_match: Should we stop applying rules if this rule is
               matched?
        """
        self.match = match
        self.group = group
        self.float = float
        self.intrusive = intrusive
        self.break_on_match = break_on_match

    def compare(self, client):
        return self.match.compare(client)

    def __call__(self, client):
        return self.compare(client)

    def __repr__(self):
        l = []
        l.append('%s(' %self.__class__.__name__)
        for item in ('match', 'group', 'float', 'intrusive', 'break_on_match'):
            if getattr(self, item, None):
                l.append('%s=%s%s' %(item, repr(getattr(self, item)), ','))
        l.append(')')
        return ''.join(l)

