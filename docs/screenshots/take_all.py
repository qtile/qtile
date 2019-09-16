#!/usr/bin/env python3

import sys
import time
import traceback
from pathlib import Path

from screenshot import Screenshooter, Client

from libqtile.command_object import SelectError, CommandError


def take(layout, commands, name="", comment="", before=None, geometry="300x200", delay=1, windows=3):
    if not before:
        before = []

    try:
        client.prepare_layout(layout, windows, before)
    except (SelectError, CommandError):
        traceback.print_exc()
        return False

    name = name or "_".join(commands) or layout
    if comment:
        name += "-" + comment
    output_prefix = output_dir / layout / name

    time.sleep(0.5)

    screen = Screenshooter(output_prefix, geometry, delay)
    screen.shoot(numbered=bool(commands))
    if commands:
        for cmd in commands:
            client.run_layout_command(cmd)
            time.sleep(0.05)
            screen.shoot()
        screen.animate(clear=True)

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
    take("matrix", ["left"])
    take("matrix", ["right"])
    take("matrix", ["up"])
    take("matrix", ["down"])
    take("matrix", ["delete"])
    take("matrix", ["add"])

# ----------------------------------------------------------------------------
# MONAD TALL LAYOUT ----------------------------------------------------------
# ----------------------------------------------------------------------------
if not args or "monadtall" in args:
    take("monadtall", ["normalize"])
    take("monadtall", ["reset"])
    take("monadtall", ["maximize"])
    take("monadtall", ["grow"])
    take("monadtall", ["grow_main"])
    take("monadtall", ["shrink_main"])
    take("monadtall", ["shrink"])
    take("monadtall", ["shuffle_up"])
    take("monadtall", ["shuffle_down"])
    take("monadtall", ["swap"])
    take("monadtall", ["swap_left"])
    take("monadtall", ["swap_right"])
    take("monadtall", ["swap_main"])
    take("monadtall", ["left"])
    take("monadtall", ["right"])

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
