from libqtile.manager import Key, Screen
from libqtile.command import lazy
from libqtile import layout, bar, widget

# The bindings below are for use with a Kinesis keyboard, and may not make
# sense for standard keyboards.
keys = [
    # First, a set of bindings to control the layouts
    Key(
        ["shift", "control"], "k",
        lazy.layout.down()
    ),
    Key(
        ["shift", "control"], "j",
        lazy.layout.up()
    ),
    Key(
        ["control", "control"], "k",
        lazy.layout.shuffle_down()
    ),
    Key(
        ["control", "control"], "j",
        lazy.layout.shuffle_up()
    ),
    Key(
        ["control"], "space",
        lazy.layout.next()
    ),
    Key(
        ["control", "shift"], "space",
        lazy.layout.rotate()
    ),
    Key(
        ["control", "shift"], "Return",
        lazy.layout.toggle_split()
    ),

    Key(["control"], "n",      lazy.spawn("firefox")),
    Key(["control"], "h",      lazy.to_screen(1)),
    Key(["control"], "l",      lazy.to_screen(0)),
    # ~/bin/x starts a terminal program
    Key(["control"], "Return", lazy.spawn("startx")),
    Key(["control"], "Tab",    lazy.nextlayout()),
    Key(["control"], "w",      lazy.window.kill()),
]

# Next, we specify group names, and use the group name list to generate an appropriate
# set of bindings for group switching.
groups = ["a", "s", "d", "f", "u", "i", "o", "p"]
for i in groups:
    keys.append(
        Key(["control"], i, lazy.group[i].toscreen())
    )
    keys.append(
        Key(["control", "shift"], i, lazy.window.togroup(i))
    )


# Two simple layout instances:
layouts = [
    layout.Stack(stacks=2),
    layout.Max(),
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
