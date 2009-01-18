from libqtile.manager import Key, Screen
from libqtile.command import lazy
from libqtile import layout, bar, widget
from libqtile.theme import Theme
 
modkey = "mod4"
 
 
keys = [
    # First, a set of bindings to control the layouts
    Key([modkey], "k", lazy.layout.down()),
    Key([modkey], "j", lazy.layout.up()),
    Key([modkey, "shift"], "k", lazy.layout.shuffle_down()),
    Key([modkey, "shift"], "j", lazy.layout.shuffle_up()),
    Key([modkey], "space", lazy.layout.next()),
    Key([modkey, "shift"], "space", lazy.layout.rotate()),
    Key([modkey, "shift"], "Return", lazy.layout.toggle_split()),
    Key([modkey], "p", lazy.spawn("exe=`dmenu_path | dmenu` && eval \"exec $exe\"")),
    Key([modkey], "Return", lazy.spawn("urxvt")),
    Key([modkey], "Tab", lazy.nextlayout()),
    Key([modkey, "shift"], "c", lazy.window.kill()),
    Key(["mod1"],"F4", lazy.window.kill()), 
    Key(["control"], "grave", lazy.spawn("urxvt")),
    Key(["mod1"], "grave", lazy.spawn("exe=`dmenu_path | dmenu` && eval \"exec $exe\"")),
    Key([modkey], "Right", lazy.group.nextgroup()),
    Key([modkey], "Left", lazy.group.prevgroup()),
]

groups = ["zero", "one", "two", "three", "four", "five", "six"]

for i in range(len(groups)):
    keys.append(Key([modkey], str(i), lazy.group[groups[i]].toscreen()))
    keys.append(Key([modkey, "shift"], str(i), lazy.window.togroup(groups[i])))
 
theme = Theme(
    {'fg_normal': '#989898',
     'fg_focus': '#00d691',
     'fg_active': '#ffffff',
     'bg_normal': '#181818',
     'bg_focus': '#252525',
     'bg_active': '#181818',
     'border_normal': '#181818',
     'border_focus': '#0096d1',
     'border_width': 2,
     'font': '-*-zekton-*-r-normal-*-14-*-*-*-*-0-*-*',
     },
    specials = {'magnify': 
                {'border_width': 5,
                 }
                },
    )
 
layouts = [
    layout.Tile(theme),
    layout.Tile(theme, masterWindows=2),
    layout.Magnify(theme),
    layout.Magnify(theme, gap=150),
    layout.Stack(stacks=2, theme=theme),
    layout.Max(),
]


import Image

screens = [
    Screen(
        top=bar.Bar(
            [
                widget.IconBox("archicon", "/home/ben/Pictures/archicon.png"),
                widget.GroupBox(theme),
                widget.ClickableIcon("irssi", 
                                     "/home/ben/Pictures/irssi_white.png",
                                     lazy.spawn("~/Scripts/irssi.sh"),
                                     ),
                widget.ClickableIcon("browser",
                                     "/usr/share/icons/HighContrastLargePrintInverse/48x48/apps/mozilla-icon.png",
                                     lazy.spawn("conkeror"),
                                     ),
                widget.WindowName(),
                ],
            20, theme=theme),
        ),
    ]
 
