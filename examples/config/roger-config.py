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
        [mod], "Left", lazy.prevgroup(),
    ),
    Key(
        [mod], "Right", lazy.nextgroup(),
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
    Group("1"),
    Group("2"),
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


# I have two screens, each of which has a Bar at the bottom. Each Bar has two
# simple widgets - a GroupBox, and a WindowName.
screens = [
    Screen(
        top = bar.Bar(
                    [
                        widget.GroupBox(),
                        widget.WindowName(),
                        #widget.Spacer(),
                        widget.Systray(),
                        widget.Clock(),
                    ],
                    20,
                ),
    ),
]


def main(qtile):
    from dgroups import DGroups, Match
    import re
    groups = {
            'design':  {'init': True, 'persist': True},
            'h4x':  {'init': True, 'spawn': 'Terminal', 'exclusive': True},
            'lol':  {},
           }
    apps = [
            {'match': Match(wm_class=['Gimp']),
                'group': 'design', 'float': True},
            {'match': Match(title=[re.compile('T.*')]), 'group': 'h4x'},
            {'match': Match(wm_type=['dialog']), 'float': True},
           ]
    dgroups = DGroups(qtile, groups, apps)
