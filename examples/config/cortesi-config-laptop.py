from libqtile.manager import Key, Screen
from libqtile.command import lazy
from libqtile import layout, bar, widget

keys = [
    Key(
        ["mod1"], "k",
        lazy.layout.down(),
    ),
    Key(
        ["mod1"], "j",
        lazy.layout.up(),
    ),
    Key(
        ["mod1", "control"], "k",
        lazy.layout.shuffle_down(),
    ),
    Key(
        ["mod1", "control"], "j",
        lazy.layout.shuffle_up(),
    ),
    Key(
        ["mod1"], "space",
        lazy.layout.next(),
    ),
    Key(
        ["mod1", "shift"], "space",
        lazy.layout.rotate(),
    ),
    Key(
        ["mod1", "shift"], "Return",
        lazy.layout.toggle_split(),
    ),
    Key(["mod1"], "n",      lazy.spawn("firefox")),
    Key(["mod1"], "h",      lazy.to_screen(0)),
    Key(["mod1"], "l",      lazy.to_screen(1)),
    Key(["mod1"], "Return", lazy.spawn("~/bin/x")),
    Key(["mod1"], "Tab",    lazy.nextlayout()),
    Key(["mod1"], "w",      lazy.window.kill()),
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

groups = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]
for i in groups:
    keys.append(
        Key([], "F"+i, lazy.group[i].toscreen())
    )

layouts = [
    layout.Max(),
    layout.Stack(stacks=2, borderWidth=2)
]

commands = []
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
]
