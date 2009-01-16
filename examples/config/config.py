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
]

groups = ["zero", "one", "two", "three", "four", "five", "six"]

for i in range(len(groups)):
    keys.append(Key([modkey], str(i), lazy.group[groups[i]].toscreen()))
    keys.append(Key([modkey, "shift"], str(i), lazy.window.togroup(groups[i])))
 
theme = Theme(
    {'fg_normal': '#989898',
     'fg_focus': '#8fea26',
     'fg_active': '#ffffff',
     'bg_normal': '#181818',
     'bg_focus': '#252525',
     'bg_active': '#181818',
     'border_normal': '#181818',
     'border_focus': '#8fea26',
     'border_width': 2,
     'font': '-*-nimbus sans l-*-r-*-*-*-*-*-*-*-*-*-*',
     }
    )
 
layouts = [
    layout.Magnify(theme),
    layout.Magnify(theme, gap=150),
]


screens = [
    Screen(
        top=bar.Bar(
            [
                widget.GroupBox(theme),
                widget.WindowName()
                ],
            15, theme=theme),
        bottom=bar.Bar(
            [widget.WindowName(), ],
            15, theme=theme  )
        )
    ]
 
