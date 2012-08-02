import re

from libqtile.command import lazy
from libqtile.manager import Key, Click, Drag, Screen

from libqtile import layout, bar, widget

from libqtile.dgroups import DGroups, Match, simple_key_binder

mod = 'mod4'
keys = [
    # vim like movement
    Key(
        [mod], "h", lazy.group.prevgroup(),
    ),
    Key(
        [mod], "l", lazy.group.nextgroup(),
    ),
    Key(
        [mod], "k",
        lazy.layout.down()
    ),
    Key(
        [mod], "j",
        lazy.layout.up()
    ),
    Key(
        [mod], "f",
        lazy.window.toggle_floating()
    ),

    # layout stuff
    Key(
        [mod, "shift"], "f",
        lazy.window.toggle_fullscreen()
    ),
    Key(
        [mod], "space",
        lazy.nextlayout()
    ),
    Key([mod], "Tab",
        lazy.layout.previous()
    ),
    Key([mod, "shift"], "Tab",
        lazy.layout.next()
    ),
    Key(
        [mod, "shift"], "space",
        lazy.layout.rotate()
    ),
    Key(
        [mod, "shift"], "Return",
        lazy.layout.toggle_split()
    ),

    Key([mod, "shift"], "Right",
        lazy.layout.increase_ratio()),
    Key([mod, "shift"], "Left",
        lazy.layout.decrease_ratio()),

    Key([mod], "w",      lazy.window.kill()),
    Key([mod], "F2",     lazy.spawn(
        "dmenu_run -p run -fn 'terminous-13' -nb '#202020' -nf '#ffffff'")),
    Key(["mod4"], "r",      lazy.spawncmd("Run:")),

    Key([mod], "s", lazy.spawn("imgurscropt")),
    Key([mod, 'shift'], "s", lazy.spawn("imgurscropt window")),

    Key([mod], "p", lazy.spawn("/home/roger/local/bin/paste_clipboard")),
    Key([mod, 'shift'], "p", lazy.spawn("paste_clipboard bash")),

    Key([mod], "z", lazy.spawn("scroting")),
    #Key([mod, 'shift'], "z", lazy.spawn("scroting window")),

    # Suspend
    Key([mod, 'shift'], "z", lazy.spawn(
        "dbus-send --dest=org.freedesktop.PowerManagement "\
        "/org/freedesktop/PowerManagement "\
        "org.freedesktop.PowerManagement.Suspend")),

    # move to group
    Key([mod], "g", lazy.togroup()),

    # media keys
    Key([], "XF86AudioRaiseVolume",
        lazy.spawn("amixer sset Master 5%+")),
    Key([], "XF86AudioLowerVolume",
        lazy.spawn("amixer sset Master 5%-")),
    Key([], "XF86AudioMute",
        lazy.spawn("amixer sset Master toggle")),
    Key(["shift"], "XF86AudioRaiseVolume",
        lazy.spawn("mpc next")),
    Key(["shift"], "XF86AudioLowerVolume",
        lazy.spawn("mpc prev")),
    # Have not mute key
    #Key(["shift"], "XF86AudioMute",

    Key([mod], "p",
        lazy.spawn("mpc toggle")),

    # just for testing
    Key(["mod4", "control"], "a", lazy.execute("/usr/bin/awesome", ("awesome",))),

    # restart qtile
    Key(["mod4", "control"], "r", lazy.restart()),
]

mouse = [
    Drag([mod], "Button1", lazy.window.set_position_floating(),
        start=lazy.window.get_position()),
    Drag([mod], "Button3", lazy.window.set_size_floating(),
        start=lazy.window.get_size()),
    Click([mod], "Button2", lazy.window.bring_to_front())
]

groups = []

data = {"border_width": 2, "margin": 3,
        "border_focus": "#005F0C", "border_normal": "#555555"}

layouts = [
    layout.Max(),
    layout.Stack(stacks=2),
    layout.Tile(ratio=0.25, **data),
]


screens = [
    Screen(
        top = bar.Bar(
                    [
                        widget.GroupBox(borderwidth=2,
                            fontsize=12,
                            padding=1, margin_y=1),
                        widget.Sep(),
                        widget.Prompt(),
                        widget.WindowName(
                            fontsize=12, margin_x=6),
                        widget.Sep(),
                        #widget.Mpd(fontsize=16),
                        widget.CPUGraph(width=42, line_width=2,
                            graph_color='0066FF', fill_color='001188'),
                        widget.MemoryGraph(width=42, line_width=2,
                            graph_color='22FF44', fill_color='11AA11'),
                        widget.SwapGraph(width=42, line_width=2,
                            graph_color='FF2020', fill_color='C01010'),
                        widget.Sep(),
                        widget.Volume(update_interval=1, theme_path=\
                                '/usr/share/icons/LowContrast/48x48/stock/'),
                        #widget.Sep(),
                        widget.Systray(icon_size=14),
                        #widget.Sep(),
                        widget.Clock('%d/%m/%y %H:%M',
                            fontsize=14, padding=6),
                    ],
                    18
                ),
    ),
]


def to_urgent(qtile):
    cg = qtile.currentGroup
    for group in qtile.groupMap.values():
        if group == cg:
            continue
        if len([w for w in group.windows if w.urgent]) > 0:
            qtile.currentScreen.setGroup(group)
            return


class TermHack(object):
    def __init__(self, qtile, group):
        self.qtile = qtile
        self.group = group
        self.last_group = None

    def group_by_name(self, name):
        for group in self.qtile.groups:
            if group.name == name:
                return group

    def __call__(self, qtile):
        group = self.group_by_name(self.group)
        cg = qtile.currentGroup
        if cg != group:
            qtile.currentScreen.setGroup(group)
            self.last_group = cg
        elif self.last_group:
            qtile.currentScreen.setGroup(self.last_group)


def main(qtile):
    groups = {
            'h4x':  {'init': True, 'persist': True,
                'exclusive': True},
            'design': {},
            'www': {'exclusive': True},
            # master set the master window/windows of layout
            'emesene': {'layout': 'tile', 'master': Match(role=['main'])},
            'gajim': {'layout': 'tile', 'master': Match(role=['roster']), 
                'exclusive': True},
           }

    apps = [
            {'match': Match(wm_class=['Gimp']),
                'group': 'design', 'float': True},
            {'match': Match(wm_class=['Terminator', 'Qterminal']), 
                                                    'group': 'h4x'},
            {'match': Match(wm_class=['emesene']), 'group': 'emesene'},
            {'match': Match(wm_class=['Chromium-browser', 'Minefield'],
                role=['browser']), 'group': 'www'},
            {'match': Match(wm_class=['Gajim.py']), 'group': 'gajim'},
            {'match': Match(wm_class=['Wine']), 'float': True, 'group': 'wine'},
            {'match': Match(wm_class=['Xephyr']), 'float': True},
            # Everything i want to be float, but don't want to change group
            {'match': Match(title=['nested', 'gscreenshot'], 
                wm_class=['Guake.py', 'MPlayer', 'Exe', 
                    re.compile('Gnome-keyring-prompt.*?'),
                    'Terminal'], wm_type=['dialog', 'utility', 'splash']),
                'float': True, 'intrusive': True},
           ]
    dgroups = DGroups(qtile, groups, apps, simple_key_binder(mod))

    # fast switching from/to terminal
    key = Key([], "F12", lazy.function(TermHack(qtile, 'h4x')))
    qtile.mapKey(key)

    # fast switching to urgent
    key = Key(['shift'], "F12", lazy.function(to_urgent))
    qtile.mapKey(key)
