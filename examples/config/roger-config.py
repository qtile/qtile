from libqtile.manager import Key, Click, Drag, Screen, Group
from libqtile.command import lazy
from libqtile import layout, bar, widget

mod = 'mod4'
# The bindings below are for use with a Kinesis keyboard, and may not make
# sense for standard keyboards.
keys = [
    # First, a set of bindings to control the layouts
    Key(
        [mod], "k",
        lazy.layout.down()
    ),
    Key(
        [mod], "j",
        lazy.layout.up()
    ),
    Key(
        [mod, "control"], "k",
        lazy.layout.shuffle_down()
    ),
    Key(
        [mod, "control"], "j",
        lazy.layout.shuffle_up()
    ),
    Key(
        [mod], "space",
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

    Key([mod], "h",      lazy.to_screen(1)),
    Key([mod], "l",      lazy.to_screen(0)),
    # ~/bin/x starts a terminal program
    Key([mod], "Tab",    lazy.nextlayout()),
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


# Two simple layout instances:
layouts = [
    layout.Max(),
    layout.Stack(stacks=2),
    layout.Tile(),
]


screens = [
    Screen(
        top = bar.Bar(
                    [
                        widget.GroupBox(borderwidth=2,
                            fontsize=14,
                            padding=1, margin_x=1, margin_y=1),
                        widget.Sep(),
                        widget.WindowName(
                            fontsize=14, margin_x=6),
                        widget.Sep(),
                        widget.CPUGraph(width=50, graph_color='0066FF', 
                                                  fill_color='001188'),
                        widget.MemoryGraph(width=50, graph_color='22FF44',
                                                     fill_color='11AA11'),
                        widget.SwapGraph(width=50, graph_color='FF2020',
                                                   fill_color='C01010'),
                        widget.Sep(),
                        widget.Systray(),
                        widget.Sep(),
                        widget.Clock('%H:%M %d/%m/%y',
                            fontsize=18, padding=6),
                    ],
                    24
                ),
    ),
]


def main(qtile):
    from dgroups import DGroups, Match

    groups = {
            'h4x':  {'init': True, 'persist': True, 'spawn': 'guake'},
            'design': {},
            'emesene': {},
            'gajim': {},
           }
    apps = [
            {'match': Match(wm_class=['Gimp']),
                'group': 'design', 'float': True},
            {'match': Match(wm_class=['emesene']),
                'group': 'emesene'},
            {'match': Match(wm_class=['Gajim.py']),
                'group': 'gajim'},
            {'match': Match(wm_class=['Guake.py', 'MPlayer'],
                wm_type=['dialog']), 'float': True},
            {'match': Match(wm_class=['Wine']), 'float': True, 'group': 'wine'},
           ]
    dgroups = DGroups(qtile, groups, apps)
