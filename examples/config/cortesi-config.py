from libqtile.manager import Key, Screen
from libqtile.command import lazy
from libqtile import layout, bar, widget

# The bindings below are for use with a Kinesis keyboard, and may not make
# sense for standard keyboards.
keys = [
    # First, a set of bindings to control the layouts
    Key(
        ["mod1"], "k",
        lazy.layout.down()
    ),
    Key(
        ["mod1"], "j",
        lazy.layout.up()
    ),
    Key(
        ["mod1", "control"], "k",
        lazy.layout.shuffle_down()
    ),
    Key(
        ["mod1", "control"], "j",
        lazy.layout.shuffle_up()
    ),
    Key(
        ["mod1"], "space",
        lazy.layout.next()
    ),
    Key(
        ["mod1", "shift"], "space",
        lazy.layout.rotate()
    ),
    Key(
        ["mod1", "shift"], "Return",
        lazy.layout.toggle_split()
    ),

    Key(["mod1"], "n",      lazy.spawn("firefox")),
    Key(["mod1"], "h",      lazy.to_screen(1)),
    Key(["mod1"], "l",      lazy.to_screen(0)),
    # ~/bin/x starts a terminal program
    Key(["mod1"], "Return", lazy.spawn("~/bin/x")),
    Key(["mod1"], "Tab",    lazy.nextlayout()),
    Key(["mod1"], "w",      lazy.window.kill()),

    # The bindings below control Amarok, and my sound volume.
    Key(
        ["mod1", "shift"], "k",
        lazy.spawn("amixer -c 1 -q set Speaker 2dB+")
    ),
    Key(
        ["mod1", "shift"], "j",
        lazy.spawn("amixer -c 1 -q set Speaker 2dB-")
    ),
    Key(
        ["mod1", "shift"], "n",
        #lazy.spawn("mocp -G")
        lazy.spawn("amarok -t")
    ),
    Key(
        ["mod1", "shift"], "l",
        #lazy.spawn("mocp -f")
        lazy.spawn("amarok -f")
    ),
    Key(
        ["mod1", "shift"], "h",
        #lazy.spawn("mocp -r")
        lazy.spawn("amarok -r")
    ),
]

# Next, we specify group names, and use the group name list to generate an appropriate
# set of bindings for group switching.
groups = ["a", "s", "d", "f", "u", "i", "o", "p"]
for i in groups:
    keys.append(
        Key(["mod1"], i, lazy.group[i].toscreen())
    )
    keys.append(
        Key(["mod1", "shift"], i, lazy.window.togroup(i))
    )


# Two simple layout instances:
layouts = [
    layout.Max(),
    #layout.Stack(stacks=2, borderWidth=2)
    layout.Stack(stacks=2)
]


# I have two screens, each of which has a Bar at the bottom. Each Bar has two
# simple widgets - a GroupBox, and a WindowName.
screens = [
    Screen(
        bottom = bar.Bar(
                    [
                        widget.GroupBox(),
                        widget.WindowName()
                    ],
                    30,
                ),
    ),
    Screen(
        bottom = bar.Bar(
                    [
                        widget.GroupBox(),
                        widget.WindowName()
                    ],
                    30,
                ),
    )
]
