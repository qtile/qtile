# -*- coding: utf-8 -*-
from libqtile.manager import Key, Click, Drag, Screen, Group
from libqtile.command import lazy
from libqtile import layout, bar, widget, hook

from libqtile import xcbq
xcbq.keysyms["XF86AudioRaiseVolume"] = 0x1008ff13
xcbq.keysyms["XF86AudioLowerVolume"] = 0x1008ff11
xcbq.keysyms["XF86AudioMute"] = 0x1008ff12


def window_sorter(win):
    patterns = (
        ('Яндекс.Почта', 'E-mail'),
        ('Gmail', 'E-mail'),
        ('SquirrelMail', 'E-mail'),
        ('zeromq', 'Docs'),
        ('PyYAML', 'Docs'),
        ('documentation', 'Docs'),
        ('-ietf-', 'Docs'),
        ('GNOME Live!', 'Docs'),
        ('Guide', 'Docs'),
        )
    for k, v in patterns:
        if k in win.name:
            return v

mod = "mod4"
keys = [
    Key([mod], "j",
        lazy.layout.down()),
    Key([mod], "k",
        lazy.layout.up()),
    Key([mod, "shift"], "j",
        lazy.layout.move_down()),
    Key([mod, "shift"], "k",
        lazy.layout.move_up()),
    Key([mod, "control"], "j",
        lazy.layout.section_down()),
    Key([mod, "control"], "k",
        lazy.layout.section_up()),
    Key([mod], "h",
        lazy.layout.collapse_branch()),  # for tree layout
    Key([mod], "l",
        lazy.layout.expand_branch()),  # for tree layout
    Key([mod], "r",
        lazy.layout.sort_windows(window_sorter)),  # for tree layout
    Key([mod, "shift"], "h",
        lazy.layout.move_left()),
    Key([mod, "shift"], "l",
        lazy.layout.move_right()),
    Key([mod, "control"], "l",
        lazy.layout.increase_ratio()),
    Key([mod, "control"], "h",
        lazy.layout.decrease_ratio()),
    Key([mod], "comma",
        lazy.layout.increase_nmaster()),
    Key([mod], "period",
        lazy.layout.decrease_nmaster()),
    Key([mod], "Tab",
        lazy.group.next_window()),
    Key([mod, "shift"], "Tab",
        lazy.group.prev_window()),
    Key([mod, "shift"], "Return",
        lazy.layout.rotate()),
    Key([mod, "shift"], "space",
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
        lazy.spawn("exec dmenu_run "
            "-fn 'Consolas:size=13' -nb '#000000' -nf '#ffffff' -b")),
    Key([mod], "b",
        lazy.spawn("~/note/conf/uzbl/open_history")),
    Key([mod, "shift"], "b",
        lazy.spawn("~/note/conf/uzbl/open_bookmark")),
    Key([mod], "s",
        lazy.spawn("~/note/conf/uzbl/open_ddg")),
    Key([mod, "shift"], "s",
        lazy.spawn("~/note/conf/uzbl/open_goog")),
    Key([mod], "q",
        lazy.spawn('xtrlock')),
    Key([mod], "y",
        lazy.spawn('xclip -o -selection primary | '
                   'xclip -selection clipboard')),
    Key([mod], "u",
        lazy.spawn('xclip -o -selection clipboard | '
                   'xclip -selection primary')),

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

border = dict(
    border_normal='#808080',
    border_width=2,
    )

layouts = [
    layout.Tile(**border),
    layout.Max(),
    layout.Stack(**border),
    layout.TreeTab(sections=['Surfing', 'E-mail', 'Docs', 'Incognito']),
    layout.Slice('left', 320, wmclass='pino',
        fallback=layout.Slice('right', 320, role='roster',
        fallback=layout.Stack(1, **border))),
    layout.Slice('left', 192, role='gimp-toolbox',
        fallback=layout.Slice('right', 256, role='gimp-dock',
        fallback=layout.Stack(1, **border))),
    ]
floating_layout = layout.Floating(**border)

groups = [
    Group('1'),
    Group('2', layout='max'),
    Group('3'),
    Group('4', layout='treetab'),
    Group('5'),
    Group('6'),
    Group('7'),
    Group('8'),
    Group('9'),
    ]

for i in groups:
    keys.append(
        Key([mod], i.name, lazy.group[i.name].toscreen())
    )
    keys.append(
        Key([mod, "shift"], i.name, lazy.window.togroup(i.name))
    )

screens = [
    Screen(
        top=bar.Bar(
            [
                widget.GroupBox(borderwidth=2,
                                font='Consolas', fontsize=18,
                                padding=1, margin_x=1, margin_y=1),
                widget.Sep(),
                widget.WindowName(
                    font='Consolas', fontsize=18, margin_x=6),
                widget.Sep(),
                widget.Battery(
                    font='Consolas', fontsize=18, margin_x=6),
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
    if(window.window.get_wm_type() == 'dialog'
        or window.window.get_wm_transient_for()):
        window.floating = True
