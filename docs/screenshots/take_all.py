#!/usr/bin/env python3

import sys
import time
import traceback
from pathlib import Path

from screenshot import Screenshooter, Client

from libqtile.command_object import SelectError, CommandError


def take(layout, commands, name="", comment="", before=None, after=None, geometry="300x200", delay="1x1", windows=3):
    if not before:
        before = []
    if not after:
        after = []

    try:
        client.prepare_layout(layout, windows, before)
    except (SelectError, CommandError):
        traceback.print_exc()
        return False

    name = name or "_".join(commands) or layout
    if comment:
        name += "-" + comment
    layout_dir = output_dir / layout
    output_prefix = layout_dir / name

    layout_dir.mkdir(parents=True, exist_ok=True)

    time.sleep(0.5)

    screen = Screenshooter(output_prefix, geometry, delay)
    screen.shoot(numbered=bool(commands))
    if commands:
        for cmd in commands:
            try:
                client.run_layout_command(cmd)
            except Exception:
                traceback.print_exc()
                break
            time.sleep(0.05)
            screen.shoot()
        screen.animate(clear=True)

    if after:
        for cmd in after:
            try:
                client.run_layout_command(cmd)
            except Exception:
                traceback.print_exc()
            time.sleep(0.05)

    # kill windows
    client.kill_group_windows()

    return True


# retrieve args if any
args = sys.argv[1:] if len(sys.argv) > 1 else []

# init variables used in function take
client = Client()
output_dir = Path("docs") / "screenshots" / "layout"

# keep current group in memory, to switch back to it later
original_group = client.current_group()

# prepare layout
client.switch_to_group("s")

# ----------------------------------------------------------------------------
# BSP LAYOUT -----------------------------------------------------------------
# ----------------------------------------------------------------------------
if not args or "bsp" in args:
    # layout screenshots
    take("bsp", [], comment="2-windows", windows=2)
    take("bsp", [], comment="3-windows", windows=3)
    take("bsp", [], comment="4-windows", windows=4)
    take("bsp", [], comment="5-windows", windows=5)
    take(
        "bsp",
        [],
        comment="8-windows",
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
            "toggle_split"
        ]
    )
    # commands animations
    take("bsp", ["toggle_split"], comment="from-down-left")
    take("bsp", ["toggle_split"], comment="from-right", before=["right"])
    # take("bsp", ["next"])  # no effects?
    # take("bsp", ["previous"])  # no effects?
    take("bsp", ["left"], before=["right"])
    take("bsp", ["right"])
    take("bsp", ["up"])
    take("bsp", ["down"], before=["up"])
    take("bsp", ["shuffle_left"], before=["right"])
    take("bsp", ["shuffle_right"])
    take("bsp", ["shuffle_up"])
    take("bsp", ["shuffle_down"], before=["up"])
    take("bsp", ["grow_left"], before=["right"])
    take("bsp", ["grow_right"])
    take("bsp", ["grow_up"])
    take("bsp", ["grow_down"], before=["up"])
    take("bsp", ["flip_left"], before=["right"])
    take("bsp", ["flip_right"])
    take("bsp", ["flip_up"])
    take("bsp", ["flip_down"], before=["up"])
    take("bsp", ["normalize"], before=["grow_up", "grow_up", "grow_right", "grow_right"])

# ----------------------------------------------------------------------------
# COLUMNS LAYOUT -------------------------------------------------------------
# ----------------------------------------------------------------------------
if not args or "columns" in args:
    # layout screenshots
    take("columns", [], comment="2-windows", windows=2)
    take("columns", [], comment="3-windows", windows=3)
    take("columns", [], comment="4-windows", windows=4)
    take("columns", [], comment="5-windows", windows=4, before=["left", "spawn"])
    # commands animations
    take("columns", ["toggle_split", "toggle_split", "down", "toggle_split", "toggle_split"], windows=4, name="toggle_split")
    take("columns", ["left"])
    take("columns", ["right"], before=["left"])
    take("columns", ["up"], before=["down"])
    take("columns", ["down"])
    take("columns", ["next"])
    take("columns", ["previous"])
    take("columns", ["shuffle_left"])
    take("columns", ["shuffle_right"], before=["left"])
    take("columns", ["shuffle_up"], before=["down"])
    take("columns", ["shuffle_down"])
    take("columns", ["grow_left"])
    take("columns", ["grow_right"], before=["left"])
    take("columns", ["grow_up"], before=["down"])
    take("columns", ["grow_down"])
    take("columns", ["normalize"], before=["grow_down", "grow_down", "grow_left", "grow_left"])

# ----------------------------------------------------------------------------
# MATRIX LAYOUT --------------------------------------------------------------
# ----------------------------------------------------------------------------
if not args or "matrix" in args:
    # layout screenshots
    take("matrix", [], windows=2, comment="2-windows")
    take("matrix", [], windows=3, comment="3-windows")
    take("matrix", [], windows=4, comment="4-windows")
    take("matrix", [], windows=5, comment="5-windows")
    take("matrix", [], windows=5, comment="5-windows", before=["add"])
    # commands animations
    take("matrix", ["left"], windows=4)
    take("matrix", ["right"], windows=4)
    take("matrix", ["up"], windows=4)
    take("matrix", ["down"], windows=4)
    take("matrix", ["add", "add", "delete", "delete", "delete", "add"], name="add-delete", windows=5)

# ----------------------------------------------------------------------------
# MONAD TALL LAYOUT ----------------------------------------------------------
# ----------------------------------------------------------------------------
if not args or "monadtall" in args:
    # layout screenshots
    take("monadtall", [], windows=2, comment="2-windows")
    take("monadtall", [], windows=3, comment="3-windows")
    take("monadtall", [], windows=4, comment="4-windows")
    take("monadtall", [], windows=5, comment="5-windows")
    # commands animations
    take("monadtall", ["normalize"], windows=4, before=["maximize", "shrink_main", "shrink_main"], after=["reset"])
    take("monadtall", ["normalize"], comment="from-main", windows=4, before=["maximize", "shrink_main", "shrink_main", "left"], after=["reset"])
    take("monadtall", ["reset"], windows=4, before=["maximize", "shrink_main", "shrink_main"])
    take("monadtall", ["maximize"], windows=4, after=["reset"])
    take("monadtall", ["maximize"], windows=4, comment="main", before=["left"], after=["reset"])
    take("monadtall", ["grow", "grow", "grow", "grow"], name="grow", delay="1x2")
    take("monadtall", ["grow_main", "grow_main", "grow_main"], name="grow_main", after=["reset"], delay="1x2")
    take("monadtall", ["shrink_main", "shrink_main", "shrink_main"], name="shrink_main", after=["reset"], delay="1x2")
    take("monadtall", ["shrink", "shrink", "shrink", "shrink"], name="shrink", delay="1x2")
    take("monadtall", ["shuffle_up"])
    take("monadtall", ["shuffle_down"], before=["up"])
    # take("monadtall", ["swap"])  # requires 2 args: window1 and window2
    take("monadtall", ["swap_left"])
    take("monadtall", ["swap_right"], before=["left"])
    take("monadtall", ["swap_main"])
    take("monadtall", ["left"])
    take("monadtall", ["right"], before=["left"])

# ----------------------------------------------------------------------------
# MONAD WIDE LAYOUT ----------------------------------------------------------
# ----------------------------------------------------------------------------
if not args or "monadwide" in args:
    take("monadwide", ["normalize"])
    take("monadwide", ["reset"])
    take("monadwide", ["maximize"])
    take("monadwide", ["grow"])
    take("monadwide", ["grow_main"])
    take("monadwide", ["shrink_main"])
    take("monadwide", ["shrink"])
    take("monadwide", ["shuffle_up"])
    take("monadwide", ["shuffle_down"])
    take("monadwide", ["swap"])
    take("monadwide", ["swap_left"])
    take("monadwide", ["swap_right"])
    take("monadwide", ["swap_main"])
    take("monadwide", ["left"])
    take("monadwide", ["right"])

# ----------------------------------------------------------------------------
# RATIO TILE LAYOUT ----------------------------------------------------------
# ----------------------------------------------------------------------------
if not args or "ratiotile" in args:
    take("ratiotile", ["shuffle_down"])
    take("ratiotile", ["shuffle_up"])
    take("ratiotile", ["decrease_ratio"])
    take("ratiotile", ["increase_ratio"])

# ----------------------------------------------------------------------------
# SLICE LAYOUT ---------------------------------------------------------------
# ----------------------------------------------------------------------------
# Slice layout freezes the session
# if not args or "slice" in args:
#     take("slice", ["next"])
#     take("slice", ["previous"])

# ----------------------------------------------------------------------------
# STACK LAYOUT ---------------------------------------------------------------
# ----------------------------------------------------------------------------
if not args or "stack" in args:
    take("stack", ["toggle_split"])
    take("stack", ["down"])
    take("stack", ["up"])
    take("stack", ["suffle_down"])
    take("stack", ["suffle_up"])
    take("stack", ["delete"])
    take("stack", ["add"])
    take("stack", ["rotate"])
    take("stack", ["next"])
    take("stack", ["previous"])
    take("stack", ["client_to_next"])
    take("stack", ["client_to_previous"])
    take("stack", ["client_to_stack"])

# ----------------------------------------------------------------------------
# TILE LAYOUT ----------------------------------------------------------------
# ----------------------------------------------------------------------------
if not args or "tile" in args:
    take("tile", ["shuffle_down"])
    take("tile", ["shuffle_up"])
    take("tile", ["decrease_ratio"])
    take("tile", ["increase_ratio"])
    take("tile", ["decrease_nmaster"])
    take("tile", ["increase_nmaster"])

# ----------------------------------------------------------------------------
# TREE TAB LAYOUT ------------------------------------------------------------
# ----------------------------------------------------------------------------
if not args or "treetab" in args:
    take("treetab", ["down"])
    take("treetab", ["up"])
    take("treetab", ["move_down"])
    take("treetab", ["move_up"])
    take("treetab", ["move_left"])
    take("treetab", ["move_right"])
    take("treetab", ["add_section"])
    take("treetab", ["del_section"])
    take("treetab", ["section_up"])
    take("treetab", ["section_down"])
    take("treetab", ["sort_windows"])
    take("treetab", ["expand_branch"])
    take("treetab", ["collapse_branch"])
    take("treetab", ["decrease_ratio"])
    take("treetab", ["increase_ratio"])

# ----------------------------------------------------------------------------
# VERTICAL TILE LAYOUT -------------------------------------------------------
# ----------------------------------------------------------------------------
if not args or "verticaltile" in args:
    take("verticaltile", ["shuffle_down"])
    take("verticaltile", ["shuffle_up"])
    take("verticaltile", ["maximize"])
    take("verticaltile", ["normalize"])
    take("verticaltile", ["grow"])
    take("verticaltile", ["shrink"])

# ----------------------------------------------------------------------------
# ZOOMY LAYOUT ---------------------------------------------------------------
# ----------------------------------------------------------------------------
if not args or "zoomy" in args:
    take("zoomy", ["next"])
    take("zoomy", ["previous"])
    take("zoomy", ["down"])
    take("zoomy", ["up"])


client.switch_to_group(original_group)
