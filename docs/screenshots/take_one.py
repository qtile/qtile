#!/usr/bin/env python3
import argparse
import os
import sys
import time

from screenshots import Client, Screenshooter


def env(name, default):
    return os.environ.get(name, default)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-a",
        "--commands-after",
        dest="commands_after",
        default="",
        help="Commands to run after finishing to take screenshots. Space-separated string.",
    )
    parser.add_argument(
        "-b",
        "--commands-before",
        dest="commands_before",
        default="",
        help="Commands to run before starting to take screenshots. Space-separated string.",
    )
    parser.add_argument(
        "-c",
        "--clear",
        dest="clear",
        action="store_true",
        default=False,
        help="Whether to delete the PNG files after animating them into GIFs.",
    )
    parser.add_argument(
        "-C",
        "--comment",
        dest="comment",
        default="",
        help="Comment to append at the end of the screenshot filenames.",
    )
    parser.add_argument(
        "-d",
        "--delay",
        dest="delay",
        default=env("DELAY", "1x1"),
        help="Delay between each frame of the animated GIF. Default: 1x1.",
    )
    parser.add_argument(
        "-g",
        "--screenshot-group",
        dest="screenshot_group",
        default="s",
        help="Group to switch to to take screenshots.",
    )
    parser.add_argument(
        "-G",
        "--geometry",
        dest="geometry",
        default=env("GEOMETRY", "240x135"),
        help="The size of the generated screenshots (WIDTHxHEIGHT).",
    )
    parser.add_argument(
        "-n",
        "--name",
        dest="name",
        default="",
        help="The name of the generated screenshot files . Don't append the extension.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        dest="output_dir",
        default="docs/screenshots/layout",
        help="Directory in which to write the screenshot files.",
    )
    parser.add_argument(
        "-w",
        "--windows",
        dest="windows",
        type=int,
        default=3,
        help="Number of windows to spawn.",
    )
    parser.add_argument(
        "layout",
        choices=[
            "bsp",
            "columns",
            "matrix",
            "monadtall",
            "monadwide",
            "ratiotile",
            # "slice",
            "stack",
            "tile",
            "treetab",
            "verticaltile",
            "zoomy",
        ],
        help="Layout to use.",
    )
    parser.add_argument(
        "commands",
        nargs=argparse.ONE_OR_MORE,
        help="Commands to run and take screenshots for.",
    )

    args = parser.parse_args()
    client = Client()

    # keep current group in memory, to switch back to it later
    original_group = client.current_group()

    # prepare layout
    client.switch_to_group(args.screenshot_group)
    client.prepare_layout(
        args.layout,
        args.windows,
        args.commands_before.split(" ") if args.commands_before else [],
    )

    # wait a bit to make sure everything is in place
    time.sleep(0.5)

    # prepare screenshot output path prefix
    output_dir = os.path.join(args.output_dir, args.layout)
    os.makedirs(output_dir, exist_ok=True)
    name = args.name or "_".join(args.commands) or args.layout
    if args.comment:
        name += "-{}".format(args.comment)
    output_prefix = os.path.join(output_dir, name)
    print("Shooting {}".format(output_prefix))

    # run commands and take a screenshot between each, animate into a gif at the end
    screen = Screenshooter(output_prefix, args.geometry, args.delay)
    screen.shoot()
    for cmd in args.commands:
        client.run_layout_command(cmd)
        time.sleep(0.05)
        screen.shoot()
    screen.animate(clear=args.clear)

    if args.commands_after:
        for cmd in args.commands_after.split(" "):
            client.run_layout_command(cmd)
            time.sleep(0.05)

    # kill windows
    client.kill_group_windows()

    # switch back to original group
    client.switch_to_group(original_group)

    sys.exit(0)
