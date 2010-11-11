from libqtile.manager import Key, Click, Drag, Screen, Group
from libqtile.command import lazy
from libqtile import layout, bar, widget, hook

from libqtile import xcbq
xcbq.keysyms["XF86AudioRaiseVolume"] = 0x1008ff13
xcbq.keysyms["XF86AudioLowerVolume"] = 0x1008ff11
xcbq.keysyms["XF86AudioMute"] = 0x1008ff12

mod = "mod4"
keys = [
    # First, a set of bindings to control the layouts
    Key([mod], "k",
        lazy.layout.down()),
    Key([mod], "j",
        lazy.layout.up()),
    Key([mod], "k",
        lazy.layout.down()),
    Key([mod], "l",
        lazy.layout.increase_ratio()),
    Key([mod], "h",
        lazy.layout.decrease_ratio()),
    Key([mod], "comma",
        lazy.layout.increase_nmaster()),
    Key([mod], "period",
        lazy.layout.decrease_nmaster()),
    Key([mod], "Tab",
        lazy.layout.next()),
    Key([mod, "shift"], "space",
        lazy.layout.rotate()),
    Key([mod, "shift"], "Return",
        lazy.layout.toggle_split()),

    Key([mod], "w",
        lazy.to_screen(0)),
    Key([mod], "e",
        lazy.to_screen(1)),
    Key([mod], "space",
        lazy.nextlayout()),
    Key([mod], "c",
        lazy.window.kill()),
    Key([mod], "t",
        lazy.window.disable_floating()),
    Key([mod, "shift"], "t",
        lazy.window.enable_floating()),
    Key([mod], "p",
        lazy.spawn("exe=`dmenu_path | dmenu` && eval \"exec $exe\"")),
    Key([mod], "q",
        lazy.spawn('xtrlock')),

    Key([], "XF86AudioRaiseVolume",
        lazy.spawn("amixer sset Master 5%+")),
    Key([], "XF86AudioLowerVolume",
        lazy.spawn("amixer sset Master 5%-")),
    Key([], "XF86AudioMute",
        lazy.spawn("amixer sset Master toggle")),
    Key(["shift"], "XF86AudioRaiseVolume",
        lazy.spawn("mpc volume +5")),
    Key(["shift"], "XF86AudioLowerVolume",
        lazy.spawn("mpc volume -5")),
    Key(["shift"], "XF86AudioMute",
        lazy.spawn("mpc toggle")),

    Key([mod], "Left",
        lazy.prevgroup()),
    Key([mod], "Right",
        lazy.nextgroup()),
]

mouse = [
    Drag([mod], "Button1", lazy.window.set_position_floating(),
        start=lazy.window.get_position()),
    Drag([mod], "Button3", lazy.window.set_size_floating(),
        start=lazy.window.get_size()),
    Click([mod], "Button2", lazy.window.bring_to_front())
]


groups = [Group(str(i)) for i in xrange(1, 10)]

for i in groups:
    keys.append(
        Key([mod], i.name, lazy.group[i.name].toscreen())
    )
    keys.append(
        Key([mod, "shift"], i.name, lazy.window.togroup(i.name))
    )


layouts = [
    layout.Tile(border_normal='#808080', border_width=2),
    layout.Max(),
]

screens = [
    Screen(
        top = bar.Bar(
                    [
                        widget.GroupBox(borderwidth=2,
                            font='Consolas',fontsize=18,
                            padding=1, margin_x=1, margin_y=1),
                        widget.Sep(),
                        widget.WindowName(
                            font='Consolas',fontsize=18, margin_x=6),
                        widget.Sep(),
                        widget.CPUGraph(),
                        widget.MemoryGraph(),
                        widget.SwapGraph(foreground='C02020'),
                        widget.Sep(),
                        widget.Systray(),
                        widget.Sep(),
                        widget.Clock('%H:%M:%S %d.%m.%Y',
                            font='Consolas', fontsize=18, padding=6),
                    ],
                    24,
                ),
    ),
]

@hook.subscribe.client_new
def dialogs(window):
    if window.window.get_wm_type() == 'dialog':
        window.floating = True
