from libqtile.manager import Key, Screen
from libqtile.dgroups import Group
from libqtile.command import lazy
from libqtile import layout, bar, widget

keys = [
    # Switch between windows in current stack pane
    Key(
        ["mod1"], "k",
        lazy.layout.down()
    ),
    Key(
        ["mod1"], "j",
        lazy.layout.up()
    ),

    # Move windows up or down in current stack
    Key(
        ["mod1", "control"], "k",
        lazy.layout.shuffle_down()
    ),
    Key(
        ["mod1", "control"], "j",
        lazy.layout.shuffle_up()
    ),

    # Switch window focus to other pane(s) of stack
    Key(
        ["mod1"], "space",
        lazy.layout.next()
    ),

    # Swap panes of split stack
    Key(
        ["mod1", "shift"], "space",
        lazy.layout.rotate()
    ),

    # Toggle between split and unsplit sides of stack.
    # Split = all windows displayed
    # Unsplit = 1 window displayed, like Max layout, but still with multiple stack panes
    Key(
        ["mod1", "shift"], "Return",
        lazy.layout.toggle_split()
    ),
    Key(["mod1"], "h",      lazy.to_screen(1)),
    Key(["mod1"], "l",      lazy.to_screen(0)),
    Key(["mod1"], "Return", lazy.spawn("xterm")),

    # Toggle between different layouts as defined below
    Key(["mod1"], "Tab",    lazy.nextlayout()),
    Key(["mod1"], "w",      lazy.window.kill()),

    Key(["mod1", "control"], "r", lazy.restart()),
]

groups = [
    Group("a"),
    Group("s"),
    Group("d"),
    Group("f"),
    Group("u"),
    Group("i"),
    Group("o"),
    Group("p"),
]
for i in groups:
    # mod1 + letter of group = switch to group
    keys.append(
        Key(["mod1"], i.name, lazy.group[i.name].toscreen())
    )

    # mod1 + shift + letter of group = switch to & move focused window to group
    keys.append(
        Key(["mod1", "shift"], i.name, lazy.window.togroup(i.name))
    )

dgroups_key_binder = None

layouts = [
    layout.Max(),
    layout.Stack(stacks=2)
]

screens = [
    Screen(
        bottom = bar.Bar(
                    [
                        widget.GroupBox(),
                        widget.WindowName(),
                        widget.TextBox("default", "default config"),
                        widget.Systray(),
                        widget.Clock('%Y-%m-%d %a %I:%M %p'),
                    ],
                    30,
                ),
    ),
]

main = None
follow_mouse_focus = True
cursor_warp = False
floating_layout = layout.Floating()
mouse = ()
auto_fullscreen = True
