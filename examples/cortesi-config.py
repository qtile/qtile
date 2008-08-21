import libqtile

keys = [
    libqtile.Key(
        ["mod1"], "k",
        libqtile.command.Call("stack_down"),
    ),
    libqtile.Key(
        ["mod1"], "j",
        libqtile.command.Call("stack_up"),
    ),
    libqtile.Key(
        ["mod1", "control"], "k",
        libqtile.command.Call("stack_shuffle_down"),
    ),
    libqtile.Key(
        ["mod1", "control"], "j",
        libqtile.command.Call("stack_shuffle_up"),
    ),
    libqtile.Key(
        ["mod1"], "space",
        libqtile.command.Call("stack_next")
    ),
    libqtile.Key(
        ["mod1", "shift"], "space",
        libqtile.command.Call("stack_rotate")
    ),
    libqtile.Key(
        ["mod1", "shift"], "Return",
        libqtile.command.Call("stack_toggle_split")
    ),
    libqtile.Key(["mod1"], "n",      libqtile.command.Call("spawn", "firefox")),
    libqtile.Key(["mod1"], "h",      libqtile.command.Call("to_screen", 0)),
    libqtile.Key(["mod1"], "l",      libqtile.command.Call("to_screen", 1)),
    libqtile.Key(["mod1"], "Return", libqtile.command.Call("spawn", "~/bin/x")),
    libqtile.Key(["mod1"], "Tab",    libqtile.command.Call("nextlayout")),
    libqtile.Key(["mod1"], "w",      libqtile.command.Call("kill")),
    libqtile.Key(
        ["mod1", "shift"], "k",
        libqtile.command.Call("spawn", "amixer -qc 0 set PCM 2dB+")
    ),
    libqtile.Key(
        ["mod1", "shift"], "j",
        libqtile.command.Call("spawn", "amixer -qc 0 set PCM 2dB-")
    ),
    libqtile.Key(
        ["mod1", "shift"], "n",
        libqtile.command.Call("spawn", "amarok -t")
    ),
    libqtile.Key(
        ["mod1", "shift"], "l",
        libqtile.command.Call("spawn", "amarok -f")
    ),
    libqtile.Key(
        ["mod1", "shift"], "h",
        libqtile.command.Call("spawn", "amarok -r")
    ),
]
groups = ["a", "s", "d", "f", "u", "i", "o", "p"]
for i in groups:
    keys.append(
        libqtile.Key(["mod1"], i, libqtile.command.Call("pullgroup", i))
    )
layouts = [
    libqtile.layout.Stack(stacks=1, borderWidth=0),
    libqtile.layout.Stack(stacks=2, borderWidth=2)
]
commands = []
screens = [
    libqtile.Screen(
        bottom = libqtile.bar.Bar(
                    [
                        libqtile.bar.GroupBox(),
                        libqtile.bar.WindowName()
                    ],
                    30,
                ),
    ),
    libqtile.Screen(
        bottom = libqtile.bar.Bar(
                    [
                        libqtile.bar.GroupBox(),
                        libqtile.bar.WindowName()
                    ],
                    30,
                ),
    )
]
