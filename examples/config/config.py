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
    Key([modkey, "shift"], "c", lazy.window.kill())
]

groups = [str(i) for i in xrange(1, 10)]

for i in groups:
    keys.append(Key([modkey], i, lazy.group[i].toscreen()))
    keys.append(Key([modkey, "shift"], i, lazy.window.togroup(i)))
 
layouts = [
    layout.Stack(stacks=1, borderWidth=1),
    layout.Stack(stacks=2, borderWidth=1),
    layout.Stack(stacks=3, borderWidth=1),
]

theme = Theme(
    {'fg_normal': '#989898',
     'fg_focus': '#8fea26',
     'fg_active': '#ffffff',
     'bg_normal': '#181818',
     'bg_focus': '#252525',
     'bg_active': '#181818',
     'border': '#8fea26',
     }
    )
 
screens = [
    Screen(
        top=bar.Bar(
            [
                widget.GroupBox(theme),
                widget.WindowName()
                ],
            15),
        bottom=bar.Bar(
            [widget.WindowName(), ],
            15
            )
    )
]
 
