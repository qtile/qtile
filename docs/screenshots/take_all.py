#!/usr/bin/env python3
import sys
import time
from pathlib import Path

from screenshot import Screenshooter, get_client


def take(layout, commands, comment=None, before=None, geometry="300x200", delay=1, windows=3):
    if not before:
        before = []

    try:
        client.prepare_layout(layout, windows, before)
    except (SelectError, CommandError) as error:
        traceback.print_exc()
        return False

    name = "_".join(commands)
    if comment:
        name += "-{}".format(comment)
    output_prefix = output_dir / layout / name

    time.sleep(0.5)

    screen = Screenshooter(output_prefix, geometry, delay)
    screen.shoot()
    if commands:
        for cmd in commands:
            client.run_layout_command(cmd)
            time.sleep(0.2)
            screen.shoot()
        screen.animate()

    # kill windows
    client.kill_group_windows()

    return True


# init variables used in function take
client = get_client()
output_dir = Path("docs") / "screenshots" / "layout"

# keep current group in memory, to switch back to it later
original_group = client.current_group()

# prepare layout
client.switch_to_group("s")

take("bsp", ["toggle_split"], comment="from-down-left")
take("bsp", ["toggle_split"], comment="from-right", before=["right"])
# take("bsp", ["next"])  # no effetcs?
# take("bsp", ["previous"])  # no effetcs?
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
# take("bsp", ["normalize"])  # no effects?

# the rest is not ready yet
client.switch_to_group(original_group)
sys.exit(0)

take("columns", ["toggle_split"])
take("columns", ["left"])
take("columns", ["right"])
take("columns", ["up"])
take("columns", ["down"])
take("columns", ["next"])
take("columns", ["previous"])
take("columns", ["shuffle_left"])
take("columns", ["shuffle_right"])
take("columns", ["shuffle_up"])
take("columns", ["shuffle_down"])
take("columns", ["grow_left"])
take("columns", ["grow_right"])
take("columns", ["grow_up"])
take("columns", ["grow_down"])
take("columns", ["normalize"])

take("matrix", ["left"])
take("matrix", ["right"])
take("matrix", ["up"])
take("matrix", ["down"])
take("matrix", ["delete"])
take("matrix", ["add"])

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

take("ratiotile", ["shuffle_down"])
take("ratiotile", ["shuffle_up"])
take("ratiotile", ["decrease_ratio"])
take("ratiotile", ["increase_ratio"])

# Slice layout freezes the session
# take("slice", ["next"])
# take("slice", ["previous"])

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

take("tile", ["shuffle_down"])
take("tile", ["shuffle_up"])
take("tile", ["decrease_ratio"])
take("tile", ["increase_ratio"])
take("tile", ["decrease_nmaster"])
take("tile", ["increase_nmaster"])

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

take("verticaltile", ["shuffle_down"])
take("verticaltile", ["shuffle_up"])
take("verticaltile", ["maximize"])
take("verticaltile", ["normalize"])
take("verticaltile", ["grow"])
take("verticaltile", ["shrink"])

take("zoomy", ["next"])
take("zoomy", ["previous"])
take("zoomy", ["down"])
take("zoomy", ["up"])
