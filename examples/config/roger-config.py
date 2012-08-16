from libqtile.manager import Key, Click, Drag, Screen, Group
from libqtile.command import lazy
from libqtile import layout, bar, widget

mod = 'mod4'
keys = [
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
    Key(
        [mod], "space",
        lazy.nextlayout()
    ),
    Key([mod], "Tab",
        lazy.layout.next()
    ),
    Key([mod, "shift"], "Tab",
        lazy.layout.previous()
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
        "dmenu_run -p run -nb '#202020' -nf '#ffffff' -fa 'Anonymous Pro-10'")),

    Key(
        [mod, "shift"], "k",
        lazy.spawn("amixer -c 0 -q set Master 2dB+")
    ),
    Key(
        [mod, "shift"], "j",
        lazy.spawn("amixer -c 0 -q set Master 2dB-")
    ),
    Key(
        [mod], "g",
        lazy.togroup()
    ),
    Key(
        [mod], "Left", lazy.group.prevgroup(),
    ),
    Key(
        [mod], "Right", lazy.group.nextgroup(),
    ),
]

mouse = [
    Drag([mod], "Button1", lazy.window.set_position_floating(),
        start=lazy.window.get_position()),
    Drag([mod], "Button3", lazy.window.set_size_floating(),
        start=lazy.window.get_size()),
    Click([mod], "Button2", lazy.window.bring_to_front())
]

# Next, we specify group names, and use the group name list to generate an appropriate
# set of bindings for group switching.
groups = [
#    Group("1"),
#    Group("2"),
]
for i in groups:
    keys.append(
        Key(["mod4"], i.name, lazy.group[i.name].toscreen())
    )
    keys.append(
        Key(["mod4", "shift"], i.name, lazy.window.togroup(i.name))
    )


layouts = [
    layout.Max(),
    layout.Stack(stacks=2),
    layout.Tile(ratio=0.25),
]


screens = [
    Screen(
        top=bar.Bar(
                    [
                        widget.GroupBox(borderwidth=2,
                            fontsize=14,
                            padding=1, margin_y=1),
                        widget.Sep(),
                        widget.Prompt(),
                        widget.WindowName(
                            fontsize=14, margin_x=6),
                        #widget.Sep(),
                        #widget.Mpd(fontsize=16),
                        #widget.Sep(),
                        #widget.CPUGraph(width=50, graph_color='0066FF',
                        #                          fill_color='001188'),
                        #widget.MemoryGraph(width=50, graph_color='22FF44',
                        #                             fill_color='11AA11'),
                        #widget.SwapGraph(width=50, graph_color='FF2020',
                        #                           fill_color='C01010'),
                        widget.Sep(),
                        widget.Volume(theme_path='/usr/share/icons/gnome/256x256/status/'),
                        widget.Systray(),
                        widget.Sep(),
                        widget.Clock('%H:%M %d/%m/%y',
                            fontsize=18, padding=6),
                    ],
                    24
                ),
    ),
]

# change focus on mouse over
follow_mouse_focus = True


def main(qtile):
    from dgroups import DGroups, Match, simple_key_binder
    global mod

    groups = {
            'h4x':  {'init': True, 'persist': True,
                'spawn': 'guake', 'exclusive': True},
            'design': {},
            'www': {'exclusive': True},
            # master set the master window/windows of layout
            'emesene': {'layout': 'tile', 'master': Match(role=['main'])},
            'gajim': {'layout': 'tile', 'master': Match(role=['roster'])},
           }

    apps = [
            {'match': Match(wm_class=['Guake.py',
                'MPlayer', 'Exe', 'Gnome-keyring-prompt'],
               wm_type=['dialog', 'utility', 'splash']), 'float': True},
            {'match': Match(wm_class=['Gimp']),
                'group': 'design', 'float': True},
            {'match': Match(wm_class=['emesene']),
                'group': 'emesene'},
            {'match': Match(wm_class=['Chromium-browser', 'Minefield'],
                role=['browser']), 'group': 'www'},
            {'match': Match(wm_class=['Gajim.py']),
                'group': 'gajim'},
            {'match': Match(wm_class=['Wine']), 'float': True, 'group': 'wine'},
           ]
    dgroups = DGroups(qtile, groups, apps, simple_key_binder(mod))
