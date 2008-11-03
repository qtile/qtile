from libqtile.manager import Key, Screen
from libqtile.command import lazy
from libqtile import layout, bar

# The bindings below are for use with a Kinesis keyboard, and may
# not make sense for standard keyboards.
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
    Key(["mod1"], "h",      lazy.to_screen(0)),
    Key(["mod1"], "l",      lazy.to_screen(1)),
    # ~/bin/x starts a terminal program
    Key(["mod1"], "Return", lazy.spawn("~/bin/x")),
    Key(["mod1"], "Tab",    lazy.nextlayout()),
    Key(["mod1"], "w",      lazy.window.kill()),

    # The bindings below control Amarok, and my sound volume.
    Key(
        ["mod1", "shift"], "k",
        lazy.spawn("amixer -qc 0 set PCM 2dB+")
    ),
    Key(
        ["mod1", "shift"], "j",
        lazy.spawn("amixer -qc 0 set PCM 2dB-")
    ),
    Key(
        ["mod1", "shift"], "n",
        lazy.spawn("amarok -t")
    ),
    Key(
        ["mod1", "shift"], "l",
        lazy.spawn("amarok -f")
    ),
    Key(
        ["mod1", "shift"], "h",
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


# Two simple layout instances:
layouts = [
    # A layout instance with a single stack (filling the screen), and no border.
    layout.Stack(stacks=1, borderWidth=0),
    # A 2-stack layout instance
    layout.Stack(stacks=2, borderWidth=2)
]


# I have two screens, each of which has a Bar at the bottom. Each Bar has two
# simple widgets - a GroupBox, and a WindowName.
screens = [
    Screen(
        bottom = bar.Bar(
                    [
                        bar.GroupBox(),
                        bar.WindowName()
                    ],
                    30,
                ),
    ),
    Screen(
        bottom = bar.Bar(
                    [
                        bar.GroupBox(),
                        bar.WindowName()
                    ],
                    30,
                ),
    )
]
