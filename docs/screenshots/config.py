from libqtile.config import Key, Screen
from libqtile.lazy import lazy
from libqtile import layout, bar, widget

mod = "mod4"

keys = [
    Key([mod, "control"], "q", lazy.shutdown()),
    Key([mod], "Return", lazy.spawn("xterm")),
    Key([mod], "Left", lazy.layout.left()),
    Key([mod], "Right", lazy.layout.right()),
    Key([mod], "Up", lazy.layout.up()),
    Key([mod], "Down", lazy.layout.down()),
    Key([mod], "Tab", lazy.next_layout()),
    Key([mod, "shift"], "Tab", lazy.prev_layout()),
]

border_focus = "#ff0000"
border_normal = "#000000"
border_width = 10
margin = 20
borders = dict(
    border_focus=border_focus,
    border_normal=border_normal,
    border_width=border_width
)
style = dict(margin=margin, **borders)

layouts = [
    layout.Max(name="max"),
    layout.Bsp(name="bsp", **style),
    layout.Columns(name="columns", **style),
    layout.Floating(name="floating", **borders),
    layout.Matrix(name="matrix", **style),
    layout.MonadTall(name="monadtall", **style),
    layout.MonadWide(name="monadwide", **style),
    layout.RatioTile(name="ratiotile", **style),
    # layout.Slice(name="slice"),  # Makes the session freeze
    layout.Stack(name="stack", autosplit=True, **style),
    layout.Tile(name="tile", **style),
    layout.TreeTab(name="treetab", border_width=border_width),
    layout.VerticalTile(name="verticaltile", **style),
    layout.Zoomy(name="zoomy", margin=margin),
]

screens = [
    Screen(
        bottom=bar.Bar(
            [
                widget.GroupBox(),
                widget.Prompt(),
                widget.WindowName(),
                widget.CurrentLayout(),
                widget.Clock(format="%Y-%m-%d %a %I:%M %p"),
            ],
            24,
        )
    )
]
