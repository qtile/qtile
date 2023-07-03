#!/usr/bin/env python3

import logging
import os
import sys
import time
import traceback
from collections import namedtuple
from pathlib import Path

from screenshots import Client, Screenshooter


def env(name, default):
    return os.environ.get(name, default)


Spec = namedtuple(
    "Spec",
    "commands before after geometry delay windows",
    defaults=[None, None, None, env("GEOMETRY", "240x135"), env("DELAY", "1x1"), 3],
)


specs = {
    "bsp": {
        "2-windows": Spec(windows=2),
        "3-windows": Spec(windows=3),
        "4-windows": Spec(windows=4),
        "5-windows": Spec(windows=5),
        "8-windows": Spec(
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
        "toggle_split-from-down-left": Spec(commands=["toggle_split"]),
        "toggle_split-from-right": Spec(commands=["toggle_split"], before=["right"]),
        # "next": Spec(commands=["next"]),  # no effects?
        # "previous": Spec(commands=["previous"]),  # no effects?
        "left": Spec(commands=["left"], before=["right"]),
        "right": Spec(commands=["right"]),
        "up": Spec(commands=["up"]),
        "down": Spec(commands=["down"], before=["up"]),
        "shuffle_left": Spec(commands=["shuffle_left"], before=["right"]),
        "shuffle_right": Spec(commands=["shuffle_right"]),
        "shuffle_up": Spec(commands=["shuffle_up"]),
        "shuffle_down": Spec(commands=["shuffle_down"], before=["up"]),
        "grow_left": Spec(commands=["grow_left"], before=["right"]),
        "grow_right": Spec(commands=["grow_right"]),
        "grow_up": Spec(commands=["grow_up"]),
        "grow_down": Spec(commands=["grow_down"], before=["up"]),
        "flip_left": Spec(commands=["flip_left"], before=["right"]),
        "flip_right": Spec(commands=["flip_right"]),
        "flip_up": Spec(commands=["flip_up"]),
        "flip_down": Spec(commands=["flip_down"], before=["up"]),
        "normalize": Spec(
            commands=["normalize"],
            before=["grow_up", "grow_up", "grow_right", "grow_right"],
        ),
    },
    "columns": {
        "2-windows": Spec(windows=2),
        "3-windows": Spec(windows=3),
        "4-windows": Spec(windows=4),
        "5-windows": Spec(windows=4, before=["left", "spawn"]),
        "toggle_split": Spec(
            commands=[
                "toggle_split",
                "toggle_split",
                "down",
                "toggle_split",
                "toggle_split",
            ],
            windows=4,
        ),
        "left": Spec(commands=["left"]),
        "right": Spec(commands=["right"], before=["left"]),
        "up": Spec(commands=["up"], before=["down"]),
        "down": Spec(commands=["down"]),
        "next": Spec(commands=["next"]),
        "previous": Spec(commands=["previous"]),
        "shuffle_left": Spec(commands=["shuffle_left"]),
        "shuffle_right": Spec(commands=["shuffle_right"], before=["left"]),
        "shuffle_up": Spec(commands=["shuffle_up"], before=["down"]),
        "shuffle_down": Spec(commands=["shuffle_down"]),
        "grow_left": Spec(commands=["grow_left"]),
        "grow_right": Spec(commands=["grow_right"], before=["left"]),
        "grow_up": Spec(commands=["grow_up"], before=["down"]),
        "grow_down": Spec(commands=["grow_down"]),
        "normalize": Spec(
            commands=["normalize"],
            before=["grow_down", "grow_down", "grow_left", "grow_left"],
        ),
    },
    "floating": {
        # Floating info clients lists clients from all groups,
        # breaking our "kill windows" method.
        # "2-windows": Spec(windows=2),
        # "3-windows": Spec(windows=3),
        # "4-windows": Spec(windows=4),
    },
    "matrix": {
        "2-windows": Spec(windows=2),
        "3-windows": Spec(windows=3),
        "4-windows": Spec(windows=4),
        "5-windows": Spec(windows=5),
        "5-windows-add": Spec(windows=5, before=["add"]),
        "left": Spec(commands=["left"], windows=4),
        "right": Spec(commands=["right"], before=["up", "left"], windows=4),
        "up": Spec(commands=["up"], windows=4),
        "down": Spec(commands=["down"], before=["up"], windows=4),
        "add-delete": Spec(
            commands=["add", "add", "delete", "delete", "delete", "add"],
            after=["delete"],
            windows=5,
        ),
    },
    "max": {"max": Spec(windows=1)},
    "monadtall": {
        "2-windows": Spec(windows=2),
        "3-windows": Spec(windows=3),
        "4-windows": Spec(windows=4),
        "5-windows": Spec(windows=5),
        "normalize": Spec(
            commands=["normalize"],
            windows=4,
            before=["maximize", "shrink_main", "shrink_main"],
            after=["reset"],
        ),
        "normalize-from-main": Spec(
            commands=["normalize"],
            windows=4,
            before=["maximize", "shrink_main", "shrink_main", "left"],
            after=["reset"],
        ),
        "reset": Spec(
            commands=["reset"],
            windows=4,
            before=["maximize", "shrink_main", "shrink_main"],
        ),
        "maximize": Spec(commands=["maximize"], windows=4, after=["reset"]),
        "maximize-main": Spec(commands=["maximize"], windows=4, before=["left"], after=["reset"]),
        "grow": Spec(commands=["grow", "grow", "grow", "grow"], delay="1x2"),
        "grow_main": Spec(
            commands=["grow_main", "grow_main", "grow_main"],
            after=["reset"],
            delay="1x2",
        ),
        "shrink_main": Spec(
            commands=["shrink_main", "shrink_main", "shrink_main"],
            after=["reset"],
            delay="1x2",
        ),
        "shrink": Spec(commands=["shrink", "shrink", "shrink", "shrink"], delay="1x2"),
        "shuffle_up": Spec(commands=["shuffle_up"]),
        "shuffle_down": Spec(commands=["shuffle_down"], before=["up"]),
        "flip": Spec(commands=["flip"], after=["flip"]),
        # "swap": Spec(commands=["swap"]),  # requires 2 args: window1 and window2
        "swap_left": Spec(commands=["swap_left"], after=["reset"]),
        "swap_right": Spec(commands=["swap_right"], before=["left"], after=["reset"]),
        "swap_main": Spec(commands=["swap_main"], after=["reset"]),
        "left": Spec(commands=["left"]),
        "right": Spec(commands=["right"], before=["left"]),
    },
    "monadwide": {
        # There seems to be a problem with directions. Up cycles through windows
        # clock-wise, down cycles through windows counter-clock-wise, left and right
        # works normally in the secondary columns, while left from main does nothing
        # and right from main moves to the center of the second column. It's like
        # the directions are mixed between normal orientation
        # and a 90° rotation to the left, like monadtall. Up and down are reversed
        # compared to monadtall.
        "2-windows": Spec(windows=2),
        "3-windows": Spec(windows=3),
        "4-windows": Spec(windows=4),
        "5-windows": Spec(windows=5),
        "normalize": Spec(
            commands=["normalize"],
            windows=4,
            before=["maximize", "shrink_main", "shrink_main"],
            after=["reset"],
        ),
        "normalize-from-main": Spec(
            commands=["normalize"],
            windows=4,
            before=["maximize", "shrink_main", "shrink_main", "down"],
            after=["reset"],
        ),
        "reset": Spec(
            commands=["reset"],
            windows=4,
            before=["maximize", "shrink_main", "shrink_main"],
        ),
        "maximize": Spec(commands=["maximize"], windows=4, after=["reset"]),
        "maximize-main": Spec(commands=["maximize"], windows=4, before=["down"], after=["reset"]),
        "grow": Spec(commands=["grow", "grow", "grow", "grow"], delay="1x2"),
        "grow_main": Spec(
            commands=["grow_main", "grow_main", "grow_main"],
            after=["reset"],
            delay="1x2",
        ),
        "shrink_main": Spec(
            commands=["shrink_main", "shrink_main", "shrink_main"],
            after=["reset"],
            delay="1x2",
        ),
        "shrink": Spec(commands=["shrink", "shrink", "shrink", "shrink"], delay="1x2"),
        "shuffle_up": Spec(commands=["shuffle_up"]),
        "shuffle_down": Spec(commands=["shuffle_down"], before=["down"]),
        "flip": Spec(commands=["flip"], after=["flip"]),
        # "swap": Spec(commands=["swap"]),  # requires 2 args: window1 and window2
        "swap_left": Spec(commands=["swap_left"], before=["flip"], after=["flip"]),
        "swap_right": Spec(commands=["swap_right"], before=["left"]),
        "swap_main": Spec(commands=["swap_main"]),
        "left": Spec(commands=["left"]),
        "right": Spec(commands=["right"], before=["left"]),
    },
    "ratiotile": {
        "2-windows": Spec(windows=2),
        "3-windows": Spec(windows=3),
        "4-windows": Spec(windows=4),
        "5-windows": Spec(windows=5),
        "6-windows": Spec(windows=6),
        "7-windows": Spec(windows=7),
        "shuffle_down": Spec(
            commands=["shuffle_down", "shuffle_down", "shuffle_down"],
            windows=5,
            delay="1x2",
        ),
        "shuffle_up": Spec(
            commands=["shuffle_up", "shuffle_up", "shuffle_up"], windows=5, delay="1x2"
        ),
        # decrease_ratio does not seem to work
        # "decrease_ratio": Spec(
        # commands=["decrease_ratio", "decrease_ratio", "decrease_ratio", "decrease_ratio"],
        # windows=5, delay="1x2"),
        # increase_ratio does not seem to work
        # "increase_ratio": Spec(
        # commands=["increase_ratio", "increase_ratio", "increase_ratio", "increase_ratio"],
        # windows=5, delay="1x2"),
    },
    "slice": {
        # Slice layout freezes the session
        # "next": Spec(commands=["next"]),
        # "previous": Spec(commands=["previous"]),
    },
    "stack": {
        # There seems to be a confusion between Stack and Columns layouts.
        # The Columns layout says: "Extension of the Stack layout"
        # and "The screen is split into columns, which can be dynamically added
        # or removed", but there are no commands available to add or remove columns.
        # Inversely, the Stack layout says: "Unlike the columns layout
        # the number of stacks is fixed", yet the two commands
        # "cmd_add" and "cmd_delete" allow for a dynamic number of stacks!
        "2-windows": Spec(windows=2),
        "3-windows": Spec(windows=3),
        "4-windows": Spec(windows=4),
        "5-windows": Spec(windows=5),
        "toggle_split": Spec(
            commands=["toggle_split"],
            windows=4,
            before=["down", "down"],
            after=["toggle_split"],
        ),
        "down": Spec(commands=["down"], windows=4),
        "up": Spec(commands=["up"], before=["down"], windows=4),
        "shuffle_down": Spec(commands=["shuffle_down"], windows=4),
        "shuffle_up": Spec(commands=["shuffle_up"], before=["down"], windows=4),
        "add-delete": Spec(
            commands=["add", "add", "spawn", "spawn", "spawn", "delete", "delete"]
        ),
        "rotate": Spec(commands=["rotate"]),
        "next": Spec(commands=["next"], before=["add", "spawn"], after=["delete"]),
        "previous": Spec(commands=["previous"], before=["add", "spawn"], after=["delete"]),
        "client_to_next": Spec(
            commands=["client_to_next"], before=["add", "spawn"], after=["delete"]
        ),
        "client_to_previous": Spec(
            commands=["client_to_previous"], before=["add", "spawn"], after=["delete"]
        ),
        # "client_to_stack": Spec(commands=["client_to_stack"]),  # requires 1 argument
    },
    "tile": {
        # Tile: no docstring at all in the code.
        "2-windows": Spec(windows=2),
        "3-windows": Spec(windows=3),
        "4-windows": Spec(windows=4),
        "5-windows": Spec(windows=5),
        "shuffle_down": Spec(
            commands=["shuffle_down", "shuffle_down", "shuffle_down"], windows=4
        ),
        "shuffle_up": Spec(commands=["shuffle_up", "shuffle_up", "shuffle_up"], windows=4),
        "increase-decrease-ratio": Spec(
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
        "increase-decrease-nmaster": Spec(
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
        # "1-window": Spec(windows=1),
        # "2-windows": Spec(windows=2),
        # "3-windows": Spec(windows=3),
        # "4-windows": Spec(windows=4),
        # "down": Spec(commands=["down"]),
        # "up": Spec(commands=["up"]),
        # "move_down": Spec(commands=["move_down"]),
        # "move_up": Spec(commands=["move_up"]),
        # "move_left": Spec(commands=["move_left"]),
        # "move_right": Spec(commands=["move_right"]),
        # "add_section": Spec(commands=["add_section"]),
        # "del_section": Spec(commands=["del_section"]),
        # "section_up": Spec(commands=["section_up"]),
        # "section_down": Spec(commands=["section_down"]),
        # "sort_windows": Spec(commands=["sort_windows"]),
        # "expand_branch": Spec(commands=["expand_branch"]),
        # "collapse_branch": Spec(commands=["collapse_branch"]),
        # "decrease_ratio": Spec(commands=["decrease_ratio"]),
        # "increase_ratio": Spec(commands=["increase_ratio"]),
    },
    "verticaltile": {
        "3-windows": Spec(windows=3),
        "4-windows": Spec(before=["up", "maximize"], windows=4),
        "shuffle_down": Spec(commands=["shuffle_down", "shuffle_down"], before=["up", "up"]),
        "shuffle_up": Spec(commands=["shuffle_up", "shuffle_up"]),
        "shuffle_down-maximize": Spec(
            commands=["shuffle_down", "shuffle_down"], before=["up", "maximize", "up"]
        ),
        "shuffle_up-maximize": Spec(
            commands=["shuffle_up", "shuffle_up"], before=["up", "maximize", "down"]
        ),
        "maximize": Spec(commands=["maximize"]),
        "normalize": Spec(commands=["normalize"], before=["up", "maximize", "shrink", "shrink"]),
        "grow-shrink": Spec(
            commands=["grow", "grow", "shrink", "shrink"],
            before=["maximize", "shrink", "shrink"],
            after=["normalize"],
            delay="1x2",
        ),
    },
    "zoomy": {
        "3-windows": Spec(windows=3),
        "4-windows": Spec(windows=4),
        "next-or-down": Spec(commands=["next", "next"], windows=4),
        "previous-or-up": Spec(commands=["previous", "previous"], windows=4),
    },
}


client = Client()
output_dir = Path("docs") / "screenshots" / "layout"


def take(name, layout, spec):
    """Take the specified screenshots and optionally animate them."""
    # prepare the layout
    try:
        client.prepare_layout(layout, spec.windows, spec.before or [])
    except Exception:
        client.kill_group_windows()
        return False, "While preparing layout:\n" + traceback.format_exc()
    time.sleep(0.5)

    # initialize screenshooter, create output directory
    layout_dir = output_dir / layout
    layout_dir.mkdir(parents=True, exist_ok=True)
    commands = spec.commands or []
    screen = Screenshooter(layout_dir / name, spec.geometry, spec.delay)
    errors = []

    # take initial screenshot (without number if it's the only one)
    screen.shoot(numbered=bool(commands))

    # take screenshots for each command, animate them at the end
    if commands:
        for command in commands:
            try:
                client.run_layout_command(command)
            except Exception:
                errors.append(
                    "While running command {}:\n{}".format(command, traceback.format_exc())
                )
                break
            time.sleep(0.05)
            screen.shoot()
        screen.animate(clear=True)

    # cleanup the layout
    try:
        client.clean_layout(spec.after or [])
    except Exception:
        errors.append("While cleaning layout:\n" + traceback.format_exc())

    if errors:
        return False, "\n\n".join(errors)
    return True, ""


def get_selection(args):
    """Parse args of the form LAYOUT, LAYOUT:NAME or LAYOUT:NAME1,NAME2."""
    if not args:
        return [(layout, sorted(specs[layout].keys())) for layout in sorted(specs.keys())]

    errors = []
    selection = []
    for arg in args:
        if ":" in arg:
            layout, names = arg.split(":")
            if layout not in specs:
                errors.append("There is no spec for layout " + layout)
                continue
            names = names.split(",")
            for name in names:
                if name not in specs[layout]:
                    errors.append("There is no spec for {}:{}".format(layout, name))
            selection.append((layout, names))
        else:
            if arg not in specs:
                errors.append("There is no spec for layout " + arg)
                continue
            selection.append((arg, sorted(specs[arg].keys())))

    if errors:
        raise LookupError("\n".join(errors))

    return selection


def main(args=None):
    logging.basicConfig(
        filename=env("LOG_PATH", "docs/screenshots/take_all.log"),
        format="%(asctime)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

    # get selection of specs, exit if they don't exist
    try:
        selection = get_selection(args)
    except LookupError:
        logging.exception("Wrong selection:")
        return 1

    # switch to group
    original_group = client.current_group()
    client.switch_to_group("s")

    # take screenshots/animations for each selected spec
    ok = True
    for layout, names in selection:
        for name in names:
            success, errors = take(name, layout, specs[layout][name])
            if success:
                logging.info("Shooting %s:%s - OK!", layout, name)
            else:
                ok = False
                logging.error("Shooting %s:%S - failed:\n%s", layout, name, errors)

    # switch back to original group
    client.switch_to_group(original_group)

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
