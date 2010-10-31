from libqtile.manager import Key, Screen, Group
from libqtile.command import lazy
from libqtile import layout, bar, widget

# The bindings below are for use with a Kinesis keyboard, and may not make
# sense for standard keyboards.
keys = [
    # First, a set of bindings to control the layouts
    Key(
        ["mod4"], "k",
        lazy.layout.down()
    ),
    Key(
        ["mod4"], "j",
        lazy.layout.up()
    ),
    Key(
        ["mod4", "control"], "k",
        lazy.layout.shuffle_down()
    ),
    Key(
        ["mod4", "control"], "j",
        lazy.layout.shuffle_up()
    ),
    Key(
        ["mod4"], "space",
        lazy.layout.next()
    ),
    Key(
        ["mod4", "shift"], "space",
        lazy.layout.rotate()
    ),
    Key(
        ["mod4", "shift"], "Return",
        lazy.layout.toggle_split()
    ),

    Key(["mod4"], "h",      lazy.to_screen(1)),
    Key(["mod4"], "l",      lazy.to_screen(0)),
    # ~/bin/x starts a terminal program
    Key(["mod4"], "Tab",    lazy.nextlayout()),
    Key(["mod4"], "w",      lazy.window.kill()),
    Key(["mod4"], "F2",     lazy.spawn(
        "dmenu_run -p run -nb '#202020' -nf '#ffffff' -fa 'Anonymous Pro-10'")),

    Key(
        ["mod4", "shift"], "k",
        lazy.spawn("amixer -c 0 -q set Master 2dB+")
    ),
    Key(
        ["mod4", "shift"], "j",
        lazy.spawn("amixer -c 0 -q set Master 2dB-")
    ),
    Key(
        ["mod4"], "Left", lazy.prevgroup(),
    ),
    Key(
        ["mod4"], "Right", lazy.nextgroup(),
    ),
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
                        widget.Clock(),
                        widget.Systray(),
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
            {'match': Match(wm_class=['Gimp']), 'group': 'design'},
            {'match': Match(title=[re.compile('T.*')]), 'group': 'h4x'},
           ]
    dgroups = DGroups(qtile, groups, apps)
