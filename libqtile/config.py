# Copyright (c) 2012-2015 Tycho Andersen
# Copyright (c) 2013 xarvh
# Copyright (c) 2013 horsik
# Copyright (c) 2013-2014 roger
# Copyright (c) 2013 Tao Sauvage
# Copyright (c) 2014 ramnes
# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 Adi Sieker
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
#
from __future__ import annotations

import os.path
import sys
from typing import TYPE_CHECKING

from libqtile import configurable, hook, utils
from libqtile.bar import Bar
from libqtile.command.base import CommandObject
from libqtile.log_utils import logger

if TYPE_CHECKING:
    from typing import Any, Callable, Iterable

    from libqtile.backend import base
    from libqtile.bar import BarType
    from libqtile.command.base import ItemT
    from libqtile.core.manager import Qtile
    from libqtile.group import _Group
    from libqtile.lazy import LazyCall


class Key:
    """
    Defines a keybinding.

    Parameters
    ==========
    modifiers:
        A list of modifier specifications. Modifier specifications are one of:
        ``"shift"``, ``"lock"``, ``"control"``, ``"mod1"``, ``"mod2"``, ``"mod3"``,
        ``"mod4"``, ``"mod5"``.
    key:
        A key specification, e.g. ``"a"``, ``"Tab"``, ``"Return"``, ``"space"``.
    commands:
        A list :class:`LazyCall` objects to evaluate in sequence upon keypress.
    desc:
        Description to be added to the key binding. (Optional)

    """

    def __init__(
        self, modifiers: list[str], key: str, *commands: LazyCall, desc: str = ""
    ) -> None:
        self.modifiers = modifiers
        self.key = key
        self.commands = commands
        self.desc = desc

    def __repr__(self) -> str:
        return "<Key (%s, %s)>" % (self.modifiers, self.key)


class KeyChord:
    """
    Define a key chord aka Vim-like mode.

    Parameters
    ==========
    modifiers:
        A list of modifier specifications. Modifier specifications are one of:
        ``"shift"``, ``"lock"``, ``"control"``, ``"mod1"``, ``"mod2"``, ``"mod3"``,
        ``"mod4"``, ``"mod5"``.
    key:
        A key specification, e.g. ``"a"``, ``"Tab"``, ``"Return"``, ``"space"``.
    submappings:
        A list of :class:`Key` or :class:`KeyChord` declarations to bind in this chord.
    mode:
        Boolean. Setting to ``True`` will result in the chord persisting until
        Escape is pressed. Setting to ``False`` (default) will exit the chord once
        the sequence has ended.
    name:
        A string to name the chord. The name will be displayed in the Chord
        widget.
    """

    def __init__(
        self,
        modifiers: list[str],
        key: str,
        submappings: list[Key | KeyChord],
        mode: bool | str = False,
        name: str = "",
    ):
        self.modifiers = modifiers
        self.key = key

        submappings.append(Key([], "Escape"))
        self.submappings = submappings
        self.mode = mode
        self.name = name

        if isinstance(mode, str):
            logger.warning(
                "The use of `mode` to set the KeyChord name is deprecated. "
                "Please use `name='%s'` instead. "
                "'mode' should be a boolean value to set whether the chord is persistent (True) or not.",
                mode,
            )
            self.name = mode
            self.mode = True

    def __repr__(self) -> str:
        return "<KeyChord (%s, %s)>" % (self.modifiers, self.key)


class Mouse:
    def __init__(self, modifiers: list[str], button: str, *commands: LazyCall) -> None:
        self.modifiers = modifiers
        self.button = button
        self.commands = commands
        self.button_code = int(self.button.replace("Button", ""))
        self.modmask: int = 0


class Drag(Mouse):
    """
    Bind commands to a dragging action.

    On each motion event the bound commands are executed with two additional parameters
    specifying the x and y offset from the previous position.

    Parameters
    ==========
    modifiers:
        A list of modifier specifications. Modifier specifications are one of:
        ``"shift"``, ``"lock"``, ``"control"``, ``"mod1"``, ``"mod2"``, ``"mod3"``,
        ``"mod4"``, ``"mod5"``.
    button:
        The button used to start dragging e.g. ``"Button1"``.
    commands:
        A list :class:`LazyCall` objects to evaluate in sequence upon drag.
    start:
        A :class:`LazyCall` object to be evaluated when dragging begins. (Optional)

    """

    def __init__(
        self,
        modifiers: list[str],
        button: str,
        *commands: LazyCall,
        start: LazyCall | None = None,
    ) -> None:
        super().__init__(modifiers, button, *commands)
        self.start = start

    def __repr__(self) -> str:
        return "<Drag (%s, %s)>" % (self.modifiers, self.button)


class Click(Mouse):
    """
    Bind commands to a clicking action.

    Parameters
    ==========
    modifiers:
        A list of modifier specifications. Modifier specifications are one of:
        ``"shift"``, ``"lock"``, ``"control"``, ``"mod1"``, ``"mod2"``, ``"mod3"``,
        ``"mod4"``, ``"mod5"``.
    button:
        The button used to start dragging e.g. ``"Button1"``.
    commands:
        A list :class:`LazyCall` objects to evaluate in sequence upon drag.

    """

    def __repr__(self) -> str:
        return "<Click (%s, %s)>" % (self.modifiers, self.button)


class EzConfig:
    """
    Helper class for defining key and button bindings in an Emacs-like format.

    Inspired by Xmonad's XMonad.Util.EZConfig.

    Splits an emacs keydef into modifiers and keys. For example:

          "m-s-a"     -> ['mod4', 'shift'], 'a'
          "a-<minus>" -> ['mod1'], 'minus'
          "C-<Tab>"   -> ['control'], 'Tab'

    """

    modifier_keys = {
        "M": "mod4",
        "A": "mod1",
        "S": "shift",
        "C": "control",
    }

    def parse(self, spec: str) -> tuple[list[str], str]:
        mods = []
        keys: list[str] = []

        for key in spec.split("-"):
            if not key:
                break
            if key in self.modifier_keys:
                if keys:
                    msg = "Modifiers must always come before key/btn: %s"
                    raise utils.QtileError(msg % spec)
                mods.append(self.modifier_keys[key])
                continue
            if len(key) == 1:
                keys.append(key)
                continue
            if len(key) > 3 and key[0] == "<" and key[-1] == ">":
                keys.append(key[1:-1])
                continue

        if not keys:
            msg = "Invalid key/btn specifier: %s"
            raise utils.QtileError(msg % spec)

        if len(keys) > 1:
            msg = "Key chains are not supported: %s" % spec
            raise utils.QtileError(msg)

        return mods, keys[0]


class EzKey(EzConfig, Key):
    """
    Defines a keybinding using the Emacs-like format.

    Parameters
    ==========
    keydef:
        The Emacs-like key specification, e.g. ``"M-S-a"``.
    commands:
        A list :class:`LazyCall` objects to evaluate in sequence upon keypress.
    desc:
        Description to be added to the key binding. (Optional)

    """

    def __init__(self, keydef: str, *commands: LazyCall, desc: str = "") -> None:
        modkeys, key = self.parse(keydef)
        super().__init__(modkeys, key, *commands, desc=desc)


class EzClick(EzConfig, Click):
    """
    Bind commands to a clicking action using the Emacs-like format.

    Parameters
    ==========
    btndef:
        The Emacs-like button specification, e.g. ``"M-1"``.
    commands:
        A list :class:`LazyCall` objects to evaluate in sequence upon drag.

    """

    def __init__(self, btndef: str, *commands: LazyCall) -> None:
        modkeys, button = self.parse(btndef)
        button = "Button%s" % button
        super().__init__(modkeys, button, *commands)


class EzDrag(EzConfig, Drag):
    """
    Bind commands to a dragging action using the Emacs-like format.

    Parameters
    ==========
    btndef:
        The Emacs-like button specification, e.g. ``"M-1"``.
    commands:
        A list :class:`LazyCall` objects to evaluate in sequence upon drag.
    start:
        A :class:`LazyCall` object to be evaluated when dragging begins. (Optional)

    """

    def __init__(self, btndef: str, *commands: LazyCall, start: LazyCall | None = None) -> None:
        modkeys, button = self.parse(btndef)
        button = "Button%s" % button
        super().__init__(modkeys, button, *commands, start=start)


class ScreenRect:
    def __init__(self, x: int, y: int, width: int, height: int) -> None:
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def __repr__(self) -> str:
        return "<%s %d,%d %d,%d>" % (
            self.__class__.__name__,
            self.x,
            self.y,
            self.width,
            self.height,
        )

    def hsplit(self, columnwidth: int) -> tuple[ScreenRect, ScreenRect]:
        assert 0 < columnwidth < self.width
        return (
            self.__class__(self.x, self.y, columnwidth, self.height),
            self.__class__(self.x + columnwidth, self.y, self.width - columnwidth, self.height),
        )

    def vsplit(self, rowheight: int) -> tuple[ScreenRect, ScreenRect]:
        assert 0 < rowheight < self.height
        return (
            self.__class__(self.x, self.y, self.width, rowheight),
            self.__class__(self.x, self.y + rowheight, self.width, self.height - rowheight),
        )


class Screen(CommandObject):
    """
    A physical screen, and its associated paraphernalia.

    Define a screen with a given set of :class:`Bar`s of a specific geometry. Also,
    ``x``, ``y``, ``width``, and ``height`` aren't specified usually unless you are
    using 'fake screens'.

    The ``wallpaper`` parameter, if given, should be a path to an image file. How this
    image is painted to the screen is specified by the ``wallpaper_mode`` parameter. By
    default, the image will be placed at the screens origin and retain its own
    dimensions. If the mode is ``"fill"``, the image will be centred on the screen and
    resized to fill it. If the mode is ``"stretch"``, the image is stretched to fit all
    of it into the screen.

    """

    group: _Group
    index: int

    def __init__(
        self,
        top: BarType | None = None,
        bottom: BarType | None = None,
        left: BarType | None = None,
        right: BarType | None = None,
        wallpaper: str | None = None,
        wallpaper_mode: str | None = None,
        x: int | None = None,
        y: int | None = None,
        width: int | None = None,
        height: int | None = None,
    ) -> None:

        self.top = top
        self.bottom = bottom
        self.left = left
        self.right = right
        self.wallpaper = wallpaper
        self.wallpaper_mode = wallpaper_mode
        self.qtile: Qtile | None = None
        # x position of upper left corner can be > 0
        # if one screen is "right" of the other
        self.x = x if x is not None else 0
        self.y = y if y is not None else 0
        self.width = width if width is not None else 0
        self.height = height if height is not None else 0
        self.previous_group: _Group | None = None

    def _configure(
        self,
        qtile: Qtile,
        index: int,
        x: int,
        y: int,
        width: int,
        height: int,
        group: _Group,
        reconfigure_gaps: bool = False,
    ) -> None:
        self.qtile = qtile
        self.index = index
        self.x = x
        self.y = y
        self.width = width
        self.height = height

        self.set_group(group)
        for i in self.gaps:
            i._configure(qtile, self, reconfigure=reconfigure_gaps)
        if self.wallpaper:
            self.wallpaper = os.path.expanduser(self.wallpaper)
            self.paint(self.wallpaper, self.wallpaper_mode)

    def paint(self, path: str, mode: str | None = None) -> None:
        if self.qtile:
            self.qtile.paint_screen(self, path, mode)

    @property
    def gaps(self) -> Iterable[BarType]:
        return (i for i in [self.top, self.bottom, self.left, self.right] if i)

    @property
    def dx(self) -> int:
        return self.x + self.left.size if self.left else self.x

    @property
    def dy(self) -> int:
        return self.y + self.top.size if self.top else self.y

    @property
    def dwidth(self) -> int:
        val = self.width
        if self.left:
            val -= self.left.size
        if self.right:
            val -= self.right.size
        return val

    @property
    def dheight(self) -> int:
        val = self.height
        if self.top:
            val -= self.top.size
        if self.bottom:
            val -= self.bottom.size
        return val

    def get_rect(self) -> ScreenRect:
        return ScreenRect(self.dx, self.dy, self.dwidth, self.dheight)

    def set_group(
        self, new_group: _Group | None, save_prev: bool = True, warp: bool = True
    ) -> None:
        """Put group on this screen"""
        if new_group is None:
            return

        if new_group.screen == self:
            return

        if save_prev and new_group is not self.group:
            # new_group can be self.group only if the screen is getting configured for
            # the first time
            self.previous_group = self.group

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
            g1.set_screen(s2, warp)
            s1.group = g2
            g2.set_screen(s1, warp)
        else:
            assert self.qtile is not None
            old_group = self.group
            self.group = new_group
            with self.qtile.core.masked():
                # display clients of the new group and then hide from old group
                # to remove the screen flickering
                new_group.set_screen(self, warp)

                # Can be the same group only if the screen just got configured for the
                # first time - see `Qtile._process_screens`.
                if old_group is not new_group:
                    old_group.set_screen(None, warp)

        hook.fire("setgroup")
        hook.fire("focus_change")
        hook.fire("layout_change", self.group.layouts[self.group.current_layout], self.group)

    def toggle_group(self, group: _Group | None = None, warp: bool = True) -> None:
        """Switch to the selected group or to the previously active one"""
        if group in (self.group, None) and self.previous_group:
            group = self.previous_group
        self.set_group(group, warp=warp)

    def _items(self, name: str) -> ItemT:
        if name == "layout" and self.group is not None:
            return True, list(range(len(self.group.layouts)))
        elif name == "window" and self.group is not None:
            return True, [i.wid for i in self.group.windows]
        elif name == "bar":
            return False, [x.position for x in self.gaps if isinstance(x, Bar)]
        elif name == "widget":
            bars = (g for g in self.gaps if isinstance(g, Bar))
            return False, [w.name for b in bars for w in b.widgets]
        elif name == "group":
            return True, [self.group.name]
        return None

    def _select(self, name: str, sel: str | int | None) -> CommandObject | None:
        if name == "layout":
            if sel is None:
                return self.group.layout
            else:
                assert isinstance(sel, int)
                return utils.lget(self.group.layouts, sel)
        elif name == "window":
            if sel is None:
                return self.group.current_window
            else:
                for i in self.group.windows:
                    if i.wid == sel:
                        return i
        elif name == "bar":
            assert isinstance(sel, str)
            bar = getattr(self, sel)
            if isinstance(bar, Bar):
                return bar

        elif name == "widget":
            for gap in self.gaps:
                if not isinstance(gap, Bar):
                    continue
                for widget in gap.widgets:
                    if widget.name == sel:
                        return widget
        elif name == "group":
            if sel is None:
                return self.group
            else:
                return self.group if sel == self.group.name else None
        return None

    def resize(
        self,
        x: int | None = None,
        y: int | None = None,
        w: int | None = None,
        h: int | None = None,
    ) -> None:
        assert self.qtile is not None
        if x is None:
            x = self.x
        if y is None:
            y = self.y
        if w is None:
            w = self.width
        if h is None:
            h = self.height
        self._configure(self.qtile, self.index, x, y, w, h, self.group)
        for bar in [self.top, self.bottom, self.left, self.right]:
            if bar:
                bar.draw()
        self.qtile.call_soon(self.group.layout_all)

    def cmd_info(self) -> dict[str, int]:
        """Returns a dictionary of info for this screen."""
        return dict(index=self.index, width=self.width, height=self.height, x=self.x, y=self.y)

    def cmd_resize(
        self,
        x: int | None = None,
        y: int | None = None,
        w: int | None = None,
        h: int | None = None,
    ) -> None:
        """Resize the screen"""
        self.resize(x, y, w, h)

    def cmd_next_group(self, skip_empty: bool = False, skip_managed: bool = False) -> None:
        """Switch to the next group"""
        n = self.group.get_next_group(skip_empty, skip_managed)
        self.set_group(n)
        return n.name

    def cmd_prev_group(
        self, skip_empty: bool = False, skip_managed: bool = False, warp: bool = True
    ) -> None:
        """Switch to the previous group"""
        n = self.group.get_previous_group(skip_empty, skip_managed)
        self.set_group(n, warp=warp)
        return n.name

    def cmd_toggle_group(self, group_name: str | None = None, warp: bool = True) -> None:
        """Switch to the selected group or to the previously active one"""
        assert self.qtile is not None
        group = self.qtile.groups_map.get(group_name if group_name else "")
        self.toggle_group(group, warp=warp)

    def cmd_set_wallpaper(self, path: str, mode: str | None = None) -> None:
        """Set the wallpaper to the given file."""
        self.paint(path, mode)


class Group:
    """
    Represents a "dynamic" group

    These groups can spawn apps, only allow certain Matched windows to be on them, hide
    when they're not in use, etc. Groups are identified by their name.

    Parameters
    ==========
    name:
        The name of this group.
    matches:
        List of :class:`Match` objects whose matched windows will be assigned to this
        group.
    exclusive:
        When other apps are started in this group, should we allow them here or not?
    spawn:
        This will be ``exec()`` d when the group is created. Tou can pass either a
        program name or a list of programs to ``exec()``
    layout:
        The name of default layout for this group (e.g. ``"max"``). This is the name
        specified for a particular layout in ``config.py`` or if not defined it defaults
        in general to the class name in all lower case.
    layouts:
        The group layouts list overriding global layouts. Use this to define a separate
        list of layouts for this particular group.
    persist:
        Should this group stay alive when it has no member windows?
    init:
        Should this group be alive when Qtile starts?
    layout_opts:
        Options to pass to a layout.
    screen_affinity:
        Make a dynamic group prefer to start on a specific screen.
    position:
        The position of this group.
    label:
        The display name of the group. Use this to define a display name other than name
        of the group. If set to ``None``, the display name is set to the name.

    """

    def __init__(
        self,
        name: str,
        matches: list[Match] | None = None,
        exclusive: bool = False,
        spawn: str | list[str] | None = None,
        layout: str | None = None,
        layouts: list[str] | None = None,
        persist: bool = True,
        init: bool = True,
        layout_opts: dict[str, Any] | None = None,
        screen_affinity: int | None = None,
        position: int = sys.maxsize,
        label: str | None = None,
    ) -> None:
        self.name = name
        self.label = label
        self.exclusive = exclusive
        self.spawn = spawn
        self.layout = layout
        self.layouts = layouts or []
        self.persist = persist
        self.init = init
        self.matches = matches or []
        self.layout_opts = layout_opts or {}

        self.screen_affinity = screen_affinity
        self.position = position

    def __repr__(self) -> str:
        attrs = utils.describe_attributes(
            self,
            [
                "exclusive",
                "spawn",
                "layout",
                "layouts",
                "persist",
                "init",
                "matches",
                "layout_opts",
                "screen_affinity",
            ],
        )
        return "<config.Group %r (%s)>" % (self.name, attrs)


class ScratchPad(Group):
    """
    Represents a "ScratchPad" group

    ScratchPad adds a (by default) invisible group to Qtile. That group is used as a
    place for currently not visible windows spawned by a :class:`DropDown`
    configuration.

    Parameters
    ==========
    name:
        The name of this group.
    dropdowns:
        :class:`DropDown` s available on the scratchpad.
    position:
        The position of this group.
    label:
        The display name of the :class:`ScratchPad` group. Defaults to the empty string
        such that the group is hidden in :class:`~libqtile.widget.GroupBox` widget.
    single:
        If ``True``, only one of the dropdowns will be visible at a time.

    """

    def __init__(
        self,
        name: str,
        dropdowns: list[DropDown] | None = None,
        position: int = sys.maxsize,
        label: str = "",
        single: bool = False,
    ) -> None:
        Group.__init__(
            self,
            name,
            layout="floating",
            layouts=["floating"],
            init=False,
            position=position,
            label=label,
        )
        self.dropdowns = dropdowns if dropdowns is not None else []
        self.single = single

    def __repr__(self) -> str:
        return "<config.ScratchPad %r (%s)>" % (
            self.name,
            ", ".join(dd.name for dd in self.dropdowns),
        )


class Match:
    """
    Match for dynamic groups or auto-floating windows.

    It can match by title, wm_class, role, wm_type, wm_instance_class or net_wm_pid.

    :class:`Match` supports both regular expression objects (i.e. the result of
    ``re.compile()``) or strings (match as an "include"-match). If a window matches all
    specified values, it is considered a match.

    Parameters
    ==========
    title:
        Match against the WM_NAME atom (X11) or title (Wayland).
    wm_class:
        Match against the second string in WM_CLASS atom (X11) or app ID (Wayland).
    role:
        Match against the WM_ROLE atom (X11 only).
    wm_type:
        Match against the WM_TYPE atom (X11 only).
    wm_instance_class:
        Match against the first string in WM_CLASS atom (X11) or app ID (Wayland).
    net_wm_pid:
        Match against the _NET_WM_PID atom (X11) or PID (Wayland).
    func:
        Delegate the match to the given function, which receives the tested client as an
        argument and must return ``True`` if it matches, ``False`` otherwise.
    wid:
        Match against the window ID.

    """

    def __init__(
        self,
        title: str | None = None,
        wm_class: str | None = None,
        role: str | None = None,
        wm_type: str | None = None,
        wm_instance_class: str | None = None,
        net_wm_pid: int | None = None,
        func: Callable[[base.Window], bool] | None = None,
        wid: int | None = None,
    ) -> None:
        self._rules: dict[str, Any] = {}

        if title is not None:
            self._rules["title"] = title
        if wm_class is not None:
            self._rules["wm_class"] = wm_class
        if wm_instance_class is not None:
            self._rules["wm_instance_class"] = wm_instance_class
        if wid is not None:
            self._rules["wid"] = wid
        if net_wm_pid is not None:
            try:
                self._rules["net_wm_pid"] = int(net_wm_pid)
            except ValueError:
                error = 'Invalid rule for net_wm_pid: "%s" only int allowed' % str(net_wm_pid)
                raise utils.QtileError(error)
        if func is not None:
            self._rules["func"] = func

        if role is not None:
            self._rules["role"] = role
        if wm_type is not None:
            self._rules["wm_type"] = wm_type

    @staticmethod
    def _get_property_predicate(name: str, value: Any) -> Callable[..., bool]:
        if name == "net_wm_pid" or name == "wid":
            return lambda other: other == value
        elif name == "wm_class":

            def predicate(other) -> bool:  # type: ignore
                # match as an "include"-match on any of the received classes
                match = getattr(other, "match", lambda v: v in other)
                return value and any(match(v) for v in value)

            return predicate
        else:

            def predicate(other) -> bool:  # type: ignore
                # match as an "include"-match
                match = getattr(other, "match", lambda v: v in other)
                return match(value)

            return predicate

    def compare(self, client: base.Window) -> bool:
        value: Any
        for property_name, rule_value in self._rules.items():
            if property_name == "title":
                value = client.name
            elif "class" in property_name:
                wm_class = client.get_wm_class()
                if not wm_class:
                    return False
                if property_name == "wm_instance_class":
                    value = wm_class[0]
                else:
                    value = wm_class
            elif property_name == "role":
                value = client.get_wm_role()
            elif property_name == "func":
                return rule_value(client)
            elif property_name == "net_wm_pid":
                value = client.get_pid()
            elif property_name == "wid":
                value = client.wid
            else:
                value = client.get_wm_type()

            # Some of the window.get_...() functions can return None
            if value is None:
                return False

            match = self._get_property_predicate(property_name, value)
            if not match(rule_value):
                return False

        if not self._rules:
            return False
        return True

    def map(self, callback: Callable[[base.Window], Any], clients: list[base.Window]) -> None:
        """Apply callback to each client that matches this Match"""
        for c in clients:
            if self.compare(c):
                callback(c)

    def __repr__(self) -> str:
        return "<Match %s>" % self._rules


class Rule:
    """
    How to act on a match.

    A :class:`Rule` contains a list of :class:`Match` objects, and a specification about
    what to do when any of them is matched.

    Parameters
    ==========
    match:
        :class:`Match` object or a list of such associated with this rule.
    float:
        Should we auto float this window?
    intrusive:
        Should we override the group's exclusive setting?
    break_on_match:
        Should we stop applying rules if this rule is matched?

    """

    def __init__(
        self,
        match: Match | list[Match],
        group: _Group | None = None,
        float: bool = False,
        intrusive: bool = False,
        break_on_match: bool = True,
    ) -> None:
        if isinstance(match, Match):
            self.matchlist = [match]
        else:
            self.matchlist = match
        self.group = group
        self.float = float
        self.intrusive = intrusive
        self.break_on_match = break_on_match

    def matches(self, w: base.Window) -> bool:
        return any(w.match(m) for m in self.matchlist)

    def __repr__(self) -> str:
        actions = utils.describe_attributes(
            self, ["group", "float", "intrusive", "break_on_match"]
        )
        return "<Rule match=%r actions=(%s)>" % (self.matchlist, actions)


class DropDown(configurable.Configurable):
    """
    Configure a specified command and its associated window for the :class:`ScratchPad`.
    That window can be shown and hidden using a configurable keystroke or any other
    scripted trigger.
    """

    defaults = (
        (
            "x",
            0.1,
            "X position of window as fraction of current screen width. "
            "0 is the left most position.",
        ),
        (
            "y",
            0.0,
            "Y position of window as fraction of current screen height. "
            "0 is the top most position. To show the window at bottom, "
            "you have to configure a value < 1 and an appropriate height.",
        ),
        ("width", 0.8, "Width of window as fraction of current screen width"),
        ("height", 0.35, "Height of window as fraction of current screen."),
        ("opacity", 0.9, "Opacity of window as fraction. Zero is opaque."),
        (
            "on_focus_lost_hide",
            True,
            "Shall the window be hidden if focus is lost? If so, the :class:`DropDown` "
            "is hidden if window focus or the group is changed.",
        ),
        (
            "warp_pointer",
            True,
            "Shall pointer warp to center of window on activation? "
            "This only has effect if any of the ``on_focus_lost_xxx`` options are "
            "``True``",
        ),
        (
            "match",
            None,
            "Use a :class:`Match` to identify the spawned window and move it to the "
            "scratchpad, instead of relying on the window's PID. This works around "
            "some programs that may not be caught by the window's PID if it does "
            "not match the PID of the spawned process.",
        ),
    )

    def __init__(self, name: str, cmd: str, **config: dict[str, Any]) -> None:
        """
        Initialize :class:`DropDown` window wrapper.

        Define a command to spawn a process for the first time the class:`DropDown` is
        shown.

        Parameters
        ==========
        name:
            The name of the dropdown.
        cmd:
            Command to spawn a window to be captured by the dropdown.
        """
        configurable.Configurable.__init__(self, **config)
        self.name = name
        self.command = cmd
        self.add_defaults(self.defaults)

    def info(self) -> dict[str, Any]:
        return dict(
            name=self.name,
            command=self.command,
            x=self.x,
            y=self.y,
            width=self.width,
            height=self.height,
            opacity=self.opacity,
            on_focus_lost_hide=self.on_focus_lost_hide,
            warp_pointer=self.warp_pointer,
        )
