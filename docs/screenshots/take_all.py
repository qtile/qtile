#!/usr/bin/env python3

import logging
import os
import sys
import time
import traceback
from pathlib import Path

from screenshot import Screenshooter, Client


def take(name, layout, commands=None, before=None, after=None, geometry="300x200", delay="1x1", windows=3):
    if not commands:
        commands = []
    if not before:
        before = []
    if not after:
        after = []

    try:
        client.prepare_layout(layout, windows, before)
    except Exception:
        client.kill_group_windows()
        return False, "While preparing layout:\n" + traceback.format_exc()

    layout_dir = output_dir / layout
    output_prefix = layout_dir / name
    layout_dir.mkdir(parents=True, exist_ok=True)

    time.sleep(0.5)

    errors = []

    screen = Screenshooter(output_prefix, geometry, delay)
    screen.shoot(numbered=bool(commands))
    if commands:
        for cmd in commands:
            try:
                client.run_layout_command(cmd)
            except Exception:
                errors.append("While running command {}:\n{}".format(cmd, traceback.format_exc()))
                break
            time.sleep(0.05)
            screen.shoot()
        screen.animate(clear=True)

    if after:
        for cmd in after:
            try:
                client.run_layout_command(cmd)
            except Exception:
                errors.append("While running command {}:\n{}".format(cmd, traceback.format_exc()))
            time.sleep(0.05)

    client.kill_group_windows()

    if errors:
        return False, "\n\n".join(errors)
    return True, ""


# init variables used in function take
client = Client()
output_dir = Path("docs") / "screenshots" / "layout"


specs = {
    "bsp": {
        "2-windows": dict(windows=2),
        "3-windows": dict(windows=3),
        "4-windows": dict(windows=4),
        "5-windows": dict(windows=5),
        "8-windows": dict(
            windows=8,
            before=[
                "up",
                "grow_down",
                "left",
                "grow_left",
                "down",
                "right",
                "grow_left",
                "grow_left",
                "toggle_split",
                "left",
                "left",
                "grow_right",
                "grow_right",
                "grow_up",
                "grow_up",
                "up",
                "toggle_split",
            ],
        ),
        "toggle_split-from-down-left": dict(commands=["toggle_split"]),
        "toggle_split-from-right": dict(commands=["toggle_split"], before=["right"]),
        # "next": dict(commands=["next"]),  # no effects?
        # "previous": dict(commands=["previous"]),  # no effects?
        "left": dict(commands=["left"], before=["right"]),
        "right": dict(commands=["right"]),
        "up": dict(commands=["up"]),
        "down": dict(commands=["down"], before=["up"]),
        "shuffle_left": dict(commands=["shuffle_left"], before=["right"]),
        "shuffle_right": dict(commands=["shuffle_right"]),
        "shuffle_up": dict(commands=["shuffle_up"]),
        "shuffle_down": dict(commands=["shuffle_down"], before=["up"]),
        "grow_left": dict(commands=["grow_left"], before=["right"]),
        "grow_right": dict(commands=["grow_right"]),
        "grow_up": dict(commands=["grow_up"]),
        "grow_down": dict(commands=["grow_down"], before=["up"]),
        "flip_left": dict(commands=["flip_left"], before=["right"]),
        "flip_right": dict(commands=["flip_right"]),
        "flip_up": dict(commands=["flip_up"]),
        "flip_down": dict(commands=["flip_down"], before=["up"]),
        "normalize": dict(
            commands=["normalize"],
            before=["grow_up", "grow_up", "grow_right", "grow_right"],
        ),
    },
    "columns": {
        "2-windows": dict(windows=2),
        "3-windows": dict(windows=3),
        "4-windows": dict(windows=4),
        "5-windows": dict(windows=4, before=["left", "spawn"]),
        "toggle_split": dict(
            commands=[
                "toggle_split",
                "toggle_split",
                "down",
                "toggle_split",
                "toggle_split",
            ],
            windows=4,
        ),
        "left": dict(commands=["left"]),
        "right": dict(commands=["right"], before=["left"]),
        "up": dict(commands=["up"], before=["down"]),
        "down": dict(commands=["down"]),
        "next": dict(commands=["next"]),
        "previous": dict(commands=["previous"]),
        "shuffle_left": dict(commands=["shuffle_left"]),
        "shuffle_right": dict(commands=["shuffle_right"], before=["left"]),
        "shuffle_up": dict(commands=["shuffle_up"], before=["down"]),
        "shuffle_down": dict(commands=["shuffle_down"]),
        "grow_left": dict(commands=["grow_left"]),
        "grow_right": dict(commands=["grow_right"], before=["left"]),
        "grow_up": dict(commands=["grow_up"], before=["down"]),
        "grow_down": dict(commands=["grow_down"]),
        "normalize": dict(
            commands=["normalize"],
            before=["grow_down", "grow_down", "grow_left", "grow_left"],
        ),
    },
    "matrix": {
        "2-windows": dict(windows=2),
        "3-windows": dict(windows=3),
        "4-windows": dict(windows=4),
        "5-windows": dict(windows=5),
        "5-windows": dict(windows=5, before=["add"]),
        "left": dict(commands=["left"], windows=4),
        "right": dict(commands=["right"], windows=4),
        "up": dict(commands=["up"], windows=4),
        "down": dict(commands=["down"], windows=4),
        "add-delete": dict(
            commands=["add", "add", "delete", "delete", "delete", "add"], windows=5
        ),
    },
    "monadtall": {
        "2-windows": dict(windows=2),
        "3-windows": dict(windows=3),
        "4-windows": dict(windows=4),
        "5-windows": dict(windows=5),
        "normalize": dict(
            commands=["normalize"],
            windows=4,
            before=["maximize", "shrink_main", "shrink_main"],
            after=["reset"],
        ),
        "normalize-from-main": dict(
            commands=["normalize"],
            windows=4,
            before=["maximize", "shrink_main", "shrink_main", "left"],
            after=["reset"],
        ),
        "reset": dict(
            commands=["reset"],
            windows=4,
            before=["maximize", "shrink_main", "shrink_main"],
        ),
        "maximize": dict(commands=["maximize"], windows=4, after=["reset"]),
        "maximize-main": dict(
            commands=["maximize"], windows=4, before=["left"], after=["reset"]
        ),
        "grow": dict(commands=["grow", "grow", "grow", "grow"], delay="1x2"),
        "grow_main": dict(
            commands=["grow_main", "grow_main", "grow_main"],
            after=["reset"],
            delay="1x2",
        ),
        "shrink_main": dict(
            commands=["shrink_main", "shrink_main", "shrink_main"],
            after=["reset"],
            delay="1x2",
        ),
        "shrink": dict(commands=["shrink", "shrink", "shrink", "shrink"], delay="1x2"),
        "shuffle_up": dict(commands=["shuffle_up"]),
        "shuffle_down": dict(commands=["shuffle_down"], before=["up"]),
        "flip": dict(commands=["flip"], after=["flip"]),
        # "swap": dict(commands=["swap"]),  # requires 2 args: window1 and window2
        "swap_left": dict(commands=["swap_left"], after=["reset"]),
        "swap_right": dict(commands=["swap_right"], before=["left"], after=["reset"]),
        "swap_main": dict(commands=["swap_main"], after=["reset"]),
        "left": dict(commands=["left"]),
        "right": dict(commands=["right"], before=["left"]),
    },
    "monadwide": {
        # There seems to be a problem with directions. Up cycles through windows
        # clock-wise, down cycles through windows counter-clock-wise, left and right
        # works normally in the secondary columns, while left from main does nothing
        # and right from main moves to the center of the second column. It's like
        # the directions are mixed between normal orientation
        # and a 90° rotation to the left, like monadtall. Up and down are reversed
        # compared to monadtall.
        "2-windows": dict(windows=2),
        "3-windows": dict(windows=3),
        "4-windows": dict(windows=4),
        "5-windows": dict(windows=5),
        "normalize": dict(
            commands=["normalize"],
            windows=4,
            before=["maximize", "shrink_main", "shrink_main"],
            after=["reset"],
        ),
        "normalize-from-main": dict(
            commands=["normalize"],
            windows=4,
            before=["maximize", "shrink_main", "shrink_main", "down"],
            after=["reset"],
        ),
        "reset": dict(
            commands=["reset"],
            windows=4,
            before=["maximize", "shrink_main", "shrink_main"],
        ),
        "maximize": dict(commands=["maximize"], windows=4, after=["reset"]),
        "maximize-main": dict(
            commands=["maximize"], windows=4, before=["down"], after=["reset"]
        ),
        "grow": dict(commands=["grow", "grow", "grow", "grow"], delay="1x2"),
        "grow_main": dict(
            commands=["grow_main", "grow_main", "grow_main"],
            after=["reset"],
            delay="1x2",
        ),
        "shrink_main": dict(
            commands=["shrink_main", "shrink_main", "shrink_main"],
            after=["reset"],
            delay="1x2",
        ),
        "shrink": dict(commands=["shrink", "shrink", "shrink", "shrink"], delay="1x2"),
        "shuffle_up": dict(commands=["shuffle_up"]),
        "shuffle_down": dict(commands=["shuffle_down"], before=["down"]),
        "flip": dict(commands=["flip"], after=["flip"]),
        # "swap": dict(commands=["swap"]),  # requires 2 args: window1 and window2
        "swap_left": dict(commands=["swap_left"], before=["flip"], after=["flip"]),
        "swap_right": dict(commands=["swap_right"], before=["left"]),
        "swap_main": dict(commands=["swap_main"]),
        "left": dict(commands=["left"]),
        "right": dict(commands=["right"], before=["left"]),
    },
    "ratiotile": {
        "2-windows": dict(windows=2),
        "3-windows": dict(windows=3),
        "4-windows": dict(windows=4),
        "5-windows": dict(windows=5),
        "6-windows": dict(windows=6),
        "7-windows": dict(windows=7),
        "shuffle_down": dict(
            commands=["shuffle_down", "shuffle_down", "shuffle_down"],
            windows=5,
            delay="1x2",
        ),
        "shuffle_up": dict(
            commands=["shuffle_up", "shuffle_up", "shuffle_up"], windows=5, delay="1x2"
        ),
        # decrease_ratio does not seem to work
        # "decrease_ratio": dict(commands=["decrease_ratio", "decrease_ratio", "decrease_ratio", "decrease_ratio"], windows=5, delay="1x2"),
        # increase_ratio does not seem to work
        # "increase_ratio": dict(commands=["increase_ratio", "increase_ratio", "increase_ratio", "increase_ratio"], windows=5, delay="1x2"),
    },
    "slice": {
        # Slice layout freezes the session
        # "next": dict(commands=["next"]),
        # "previous": dict(commands=["previous"]),
    },
    "stack": {
        # There seems to be a confusion between Stack and Columns layouts.
        # The Columns layout says: "Extension of the Stack layout"
        # and "The screen is split into columns, which can be dynamically added
        # or removed", but there no commands available to add or remove columns.
        # Inversely, the Stack layout says: "Unlike the columns layout
        # the number of stacks is fixed", yet the two commands
        # "cmd_add" and "cmd_delete" allow for a dynamic number of stacks!
        "2-windows": dict(windows=2),
        "3-windows": dict(windows=3),
        "4-windows": dict(windows=4),
        "5-windows": dict(windows=5),
        "toggle_split": dict(
            commands=["toggle_split"],
            windows=4,
            before=["down", "down"],
            after=["toggle_split"],
        ),
        "down": dict(commands=["down"], windows=4),
        "up": dict(commands=["up"], before=["down"], windows=4),
        "shuffle_down": dict(commands=["shuffle_down"], windows=4),
        "shuffle_up": dict(commands=["shuffle_up"], before=["down"], windows=4),
        "add-delete": dict(
            commands=["add", "add", "spawn", "spawn", "spawn", "delete", "delete"]
        ),
        "rotate": dict(commands=["rotate"]),
        "next": dict(commands=["next"], before=["add", "spawn"], after=["delete"]),
        "previous": dict(
            commands=["previous"], before=["add", "spawn"], after=["delete"]
        ),
        "client_to_next": dict(
            commands=["client_to_next"], before=["add", "spawn"], after=["delete"]
        ),
        "client_to_previous": dict(
            commands=["client_to_previous"], before=["add", "spawn"], after=["delete"]
        ),
        # "client_to_stack": dict(commands=["client_to_stack"]),  # requires 1 argument
    },
    "tile": {
        # Tile: no docstring at all in the code.
        "2-windows": dict(windows=2),
        "3-windows": dict(windows=3),
        "4-windows": dict(windows=4),
        "5-windows": dict(windows=5),
        "shuffle_down": dict(
            commands=["shuffle_down", "shuffle_down", "shuffle_down"], windows=4
        ),
        "shuffle_up": dict(
            commands=["shuffle_up", "shuffle_up", "shuffle_up"], windows=4
        ),
        "increase-decrease-ratio": dict(
            commands=[
                "increase_ratio",
                "increase_ratio",
                "increase_ratio",
                "decrease_ratio",
                "decrease_ratio",
                "decrease_ratio",
            ],
            before=["down"],
            delay="1x3",
        ),
        "increase-decrease-nmaster": dict(
            commands=[
                "increase_nmaster",
                "increase_nmaster",
                "increase_nmaster",
                "decrease_nmaster",
                "decrease_nmaster",
                "decrease_nmaster",
            ],
            delay="1x3",
        ),
    },
    "treetab": {
        # TreeTab info clients lists clients from all groups,
        # breaking our "kill windows" method.
        # See https://github.com/qtile/qtile/issues/1459
        # "1-window": dict(windows=1),
        # "2-windows": dict(windows=2),
        # "3-windows": dict(windows=3),
        # "4-windows": dict(windows=4),
        # "down": dict(commands=["down"]),
        # "up": dict(commands=["up"]),
        # "move_down": dict(commands=["move_down"]),
        # "move_up": dict(commands=["move_up"]),
        # "move_left": dict(commands=["move_left"]),
        # "move_right": dict(commands=["move_right"]),
        # "add_section": dict(commands=["add_section"]),
        # "del_section": dict(commands=["del_section"]),
        # "section_up": dict(commands=["section_up"]),
        # "section_down": dict(commands=["section_down"]),
        # "sort_windows": dict(commands=["sort_windows"]),
        # "expand_branch": dict(commands=["expand_branch"]),
        # "collapse_branch": dict(commands=["collapse_branch"]),
        # "decrease_ratio": dict(commands=["decrease_ratio"]),
        # "increase_ratio": dict(commands=["increase_ratio"]),
    },
    "verticaltile": {
        "3-windows": dict(windows=3),
        "4-windows": dict(before=["up", "maximize"], windows=4),
        "shuffle_down": dict(
            commands=["shuffle_down", "shuffle_down"], before=["up", "up"]
        ),
        "shuffle_up": dict(commands=["shuffle_up", "shuffle_up"]),
        "shuffle_down-maximize": dict(
            commands=["shuffle_down", "shuffle_down"], before=["up", "maximize", "up"]
        ),
        "shuffle_up-maximize": dict(
            commands=["shuffle_up", "shuffle_up"], before=["up", "maximize", "down"]
        ),
        "maximize": dict(commands=["maximize"]),
        "normalize": dict(
            commands=["normalize"], before=["up", "maximize", "shrink", "shrink"]
        ),
        "grow-shrink": dict(
            commands=["grow", "grow", "shrink", "shrink"],
            before=["maximize", "shrink", "shrink"],
            after=["normalize"],
            delay="1x2",
        ),
    },
    "zoomy": {
        "3-windows": dict(windows=3),
        "4-windows": dict(windows=4),
        "next-or-down": dict(commands=["next", "next"], windows=4),
        "previous-or-up": dict(commands=["previous", "previous"], windows=4),
    },
}

# init logging
logging.basicConfig(
    filename=os.environ.get("LOG_PATH"),
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


# retrieve args if any
if len(sys.argv) > 1:
    selected = []
    for arg in sys.argv[1:]:
        if ":" in arg:
            layout, names = arg.split(":")
            names = names.split(",")
            selected.append((layout, names))
        else:
            selected.append((arg, sorted(specs[arg].keys())))
else:
    selected = [(layout, sorted(specs[layout].keys())) for layout in sorted(specs.keys())]

# keep current group in memory, to switch back to it later
original_group = client.current_group()

# move to group s
client.switch_to_group("s")

for layout, names in selected:
    for name in names:
        success, errors = take(name=name, layout=layout, **specs[layout][name])
        if success:
            logging.info("Shooting {}:{} - OK!".format(layout, name))
        else:
            logging.error("Shooting {}:{} - failed:\n{}".format(layout, name, errors))

# move back to original group
client.switch_to_group(original_group)
