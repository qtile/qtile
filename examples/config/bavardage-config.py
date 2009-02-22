# -*- coding: utf-8 -*-

from libqtile.manager import Key, Screen, Theme
try:
    from libqtile.manager import Hooks
except:
    pass
from libqtile.command import lazy
from libqtile import layout, bar, widget

 
modkey = "mod4"
 
keys = [
##########
# Control Layouts
##########
    Key([modkey], "k", lazy.layout.down()),
    Key([modkey], "j", lazy.layout.up()),
    Key([modkey, "shift"], "k", lazy.layout.shuffle_down()),
    Key([modkey, "shift"], "j", lazy.layout.shuffle_up()),
    Key([modkey], "space", lazy.layout.next()),
    Key([modkey, "shift"], "space", lazy.layout.rotate()),
    Key([modkey, "shift"], "Return", lazy.layout.toggle_split()),
    Key([modkey], "Tab", lazy.nextlayout()),
    #--- sublayouts
    Key([modkey, "shift"], "Tab", lazy.layout.nextsublayout()),
    Key(["mod1"], "Up", lazy.layout.command_sublayout('*', 'incratio', 0.02)),
    Key(["mod1"], "Down", lazy.layout.command_sublayout('*', 'incratio', -0.02)),
    Key([modkey], "m", lazy.layout.command_sublayout('*', 'incnmaster')),
    Key([modkey, "shift"], "m", lazy.layout.command_sublayout('*', 'incnmaster', -1)),

##########
# App launching
##########
    Key([modkey], "Return", lazy.spawn("urxvt")),
    Key(["mod1"], "grave", lazy.spawn("exe=`dmenu_path | dmenu` && eval \"exec $exe\"")),
    Key(["control"], "grave", lazy.spawn("urxvt")),
    Key([modkey], "c", lazy.spawn("emacs .config/qtile/config.py")),
    Key([modkey], "p", lazy.spawn("xmms2 toggleplay")),
    Key([modkey], "s", lazy.spawn("xmms2 stop")),
    Key([modkey], "n", lazy.spawn("xmms2 next")),

##########
# Client Control
##########
    Key([modkey, "shift"], "c", lazy.window.kill()),
    Key(["mod1"],"F4", lazy.window.kill()), 
]

##########
# Floating
##########
keys.append(Key([modkey, "control"], "space", lazy.window.toggle_floating()))
keys.append(Key([modkey, "shift"], "space", lazy.layout.command_sublayout('*', 'nextarrangement')))

for key, x, y in [("Left", -10, 0), 
                  ("Right", 10, 0), 
                  ("Up", 0, -10),
                  ("Down", 0, 10)]:
    keys.append(Key([modkey, "control"], key, lazy.window.move_floating(x, y)))
    keys.append(Key([modkey, "shift"], key, lazy.window.resize_floating(x, y)))
    keys.append(Key([modkey, "mod1"], key, lazy.window.move_to_screen_edge(key)))

##########
## Groups
##########

groups = ["1:irc", "2:web", "3", "4", "5", "6", "7:mail"]

keys.append(Key([modkey], "Right", lazy.group.nextgroup()))
keys.append(Key([modkey], "Left", lazy.group.prevgroup()))


for i in range(len(groups)):
    keys.append(Key([modkey], str(i+1), lazy.group[groups[i]].toscreen()))
    keys.append(Key([modkey, "shift"], str(i+1), lazy.window.togroup(groups[i])))


#########
# Theme
#########
theme = Theme(
    values = {'fg_normal': '#989898',
              'fg_focus': '#00d691',
              'fg_active': '#ffffff',
              'bg_normal': '#181818',
              'bg_focus': '#252525',
              'bg_active': '#181818',
              'border_normal': '#181818',
              'border_focus': '#0096d1',
              'border_width': 2,
              'font': '-*-zekton-*-r-normal-*-14-*-*-*-*-0-*-*',
              #'ttffont': '/usr/share/fonts/TTF/zektonbo.ttf',
#              'ttffont': '/usr/share/fonts/TTF/eurofc35.ttf',
              'ttffont': '/home/ben/.fonts/Diavlo_MEDIUM_II_37.ttf',
              'ttffontsize': 20,
              },
    specials = {
        'magnify': {'border_width': 5,},
        'bar': {'opacity': 0.8,},
        }
    )

#########
# Layouts
#########
layouts = [
    layout.ClientStack(
        [
            (layout.SubTile, {}),
            (layout.SubMagnify, {}),
            (layout.SubVertTile, {}),
            (layout.SubMax, {}),
            (layout.SubFloating, {}),
            (layout.SubTile, {'expand': False}),
            (layout.HybridLayoutDemo, {}),
            ],
        focus_mode = layout.ClientStack.FOCUS_TO_LAST_FOCUSED,
        ),
    layout.Tile(),
]


##########
# Screens
##########
screens = [
    Screen(
        top=bar.Bar(
            [
                widget.IconBox("archicon", "/home/ben/Pictures/archicon.png"),
                widget.TTFGroupBox(),
                widget.ClickableIcon("irssi", 
                                     "/home/ben/Pictures/irssi_white.png",
                                     lazy.spawn("~/Scripts/irssi.sh"),
                                     ),
                widget.ClickableIcon("browser",
                                     "/usr/share/icons/HighContrastLargePrintInverse/48x48/apps/mozilla-icon.png",
                                     lazy.spawn("conkeror"),
                                     ),
                widget.ClickableIcon("email",
                                     "/usr/share/icons/HighContrastLargePrintInverse/48x48/apps/evolution.png",
                                     lazy.spawn("thunderbird"),
                                     ),
                widget.ClickableIcon("term",
                                     "/usr/share/icons/HighContrastLargePrintInverse/48x48/apps/terminal.png",
                                     lazy.spawn("urxvt"),
                                     ),
                widget.TextBox("spacer", " ", 5),
                widget.TTFWindowName(),
              #  widget.TTFTextBox("ttffont", "hello guys"),
                widget.TTFTextBox("clock", " Mon Jan 01 00:00AM "), #hopefully the default width'll be right
                ],
            25),
        ),
    ]

try:
##########
# Client Rules
##########
    class ClientSpec:
        def __init__(self, name=None, wmclass=None, floating=False, group=None):
            self.name = name
            self.wmclass = wmclass
            self.floating = floating
            self.group = group
            if self.name is None and self.wmclass is None:
                raise TypeError, "Either a name or a wmclass must be specified"

        def matches(self, client):
            if client.name == self.name:
                return True
            elif self.wmclass is not None:
                cliclass = client.window.get_wm_class()
                if isinstance(self.wmclass, tuple):
                    if self.wmclass == cliclass:
                        return True
                elif self.wmclass == cliclass[0] or self.wmclass == cliclass[1]:
                    return True
            return False

        def apply(self, client):
            if self.matches(client):
                if self.floating:
                    client.floating = True
                if self.group:
                    client.cmd_togroup(self.group)
            else:
                pass
            

    Hooks.setitem('client-rules', 
                  [ClientSpec(wmclass='Conkeror', group="2:web"),
                   ClientSpec(wmclass='Gimp', floating=True),
                   ClientSpec(name='irc', group="1:irc"),
                   ClientSpec(wmclass='MPlayer', floating=True),
                   ClientSpec(wmclass='Thunderbird-bin', group="7:mail"),
                   ClientSpec(name='Compose: (no subject)', floating=True),
                   ]
                  )



    @Hooks("client-new")
    def client_new(datadict, qtile, client=None):
        if client is None:
            return
        if 'client-rules' in datadict:
            for rule in datadict['client-rules']:
                        rule.apply(client)

    @Hooks("mainloop-tick")
    def mainloop_tick(datadict, qtile):
        import time
        key = 'mainloop_tick-ticks'
        ticks = datadict.get(key, 0)
        if not ticks: #if == 0
            time = time.strftime("%a %b %d %I:%M%p")
            qtile.widgetMap.get("clock").update(time)
        datadict[key] = (ticks + 1) % 100 #run every 100 ticks, i.e. every second

    @Hooks("client-killed")
    def client_killed(datadict, qtile, client=None):
        if client is None:
            return
        print "client %s killed" % client.name

    @Hooks("client-focus")
    def client_focus(datadict, qtile, client=None):
        if client is None:
            return
        print "client %s focused" % client.name

    @Hooks("client-mouse-enter")
    def client_mouse_enter(datadict, qtile, client=None):
        if client is None:
            return
        print "mouse entered %s" % client.name

    @Hooks("client-name-updated")
    def client_name_updated(datadict, qtile, client=None):
        if client is None:
            return
        print "name updated: %s" % client.name

    @Hooks("client-urgent-hint-changed")
    def client_urgency(datadict, qtile, client=None):
        if client is None:
            print "client is none"
            return
        print "URGENCY CHANGED FOR %s" % client.name
        print "client is urgent?", client.urgent

except:
    print "oh dear no hooks"
