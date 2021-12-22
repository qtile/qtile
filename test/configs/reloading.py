# This is used for test_manager.py::test_cmd_reload_config
#
# The exported configuration variables have a different value depending on whether
# libqtile has a 'test_data' attribute (see below)

import sys
from pathlib import Path

from libqtile import bar, layout, qtile, widget
from libqtile.config import Drag, DropDown, Group, Key, Match, Rule, ScratchPad, Screen
from libqtile.dgroups import simple_key_binder
from libqtile.lazy import lazy

keys = [
    Key(["mod4"], "h", lazy.layout.left(), desc="Move focus to left"),
]

groups = [Group(i) for i in "12345"]

layouts = [
    layout.Columns(border_focus_stack=["#d75f5f", "#8f3d3d"], border_width=4),
]

screens = [
    Screen(
        bottom=bar.Bar(
            [
                widget.CurrentLayout(),
                widget.GroupBox(),
                widget.Clock(format="%Y-%m-%d %a %I:%M %p"),
                widget.QuickExit(),
            ],
            24,
        ),
    ),
]

widget_defaults = dict()

mouse = [
    Drag(
        ["mod4"],
        "Button1",
        lazy.window.set_position_floating(),
        start=lazy.window.get_position(),
    ),
]

windowpy = Path(__file__).parent.parent / "scripts" / "window.py"
script = " ".join([sys.executable, windowpy.as_posix(), "--name", "dd", "dd", "normal"])
dropdowns = [DropDown("dropdown1", script)]

dgroups_key_binder = None
dgroups_app_rules = []
floating_layout = layout.Floating(float_rules=[Match(title="one")])
wmname = "LG3D"


if hasattr(qtile, "test_data"):
    # Add more items or change values qtile.test_data is set
    keys.append(
        Key(["mod4"], "l", lazy.layout.right(), desc="Move focus to right"),
    )

    groups.extend([Group(i) for i in "6789"])

    layouts.append(layout.Max())

    screens = [
        Screen(top=bar.Bar([widget.CurrentLayout()], 32)),
    ]

    widget_defaults["background"] = "#ff0000"

    mouse.append(
        Drag(
            ["mod4"],
            "Button3",
            lazy.window.set_size_floating(),
            start=lazy.window.get_size(),
        ),
    )

    dropdowns.append(DropDown("dropdown2", script))

    dgroups_key_binder = simple_key_binder
    dgroups_app_rules = [Rule(Match(wm_class="test"), float=True)]
    floating_layout = layout.Floating()
    wmname = "TEST"

groups.append(ScratchPad("S", dropdowns))
