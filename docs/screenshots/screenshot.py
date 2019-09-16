#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys
import time
import traceback

from libqtile.ipc import find_sockfile
from libqtile.ipc import Client as IPCClient
from libqtile.command_client import InteractiveCommandClient
from libqtile.command_interface import IPCCommandInterface
from libqtile.command_object import SelectError, CommandError


class Screenshooter:
    def __init__(self, output_prefix, geometry, animation_delay):
        self.output_prefix = output_prefix
        self.geometry = geometry
        self.number = 1
        self.animation_delay = animation_delay
        self.output_paths = []

    def shoot(self, numbered=True):
        if numbered:
            output_path = "{}.{}.png".format(self.output_prefix, self.number)
        else:
            output_path = "{}.png".format(self.output_prefix)
        thumbnail_path = output_path.replace(".png", "-thumb.png")

        # overwrite previous screenshot if any
        try:
            os.remove(output_path)
        except FileNotFoundError:
            pass

        # take screenshot with scrot
        subprocess.call(["scrot", "-t", self.geometry, output_path])

        # only keep the thumbnail
        os.rename(thumbnail_path, output_path)

        # add this path to the animation command
        self.output_paths.append(output_path)

        self.number += 1

    def animate(self, delays=None, clear=False):
        # TODO: use delays to build animation with custom delay between each frame

        animate_command = [
            "convert",
            "-loop",
            "0",
            "-colors",
            "80",
            "-delay",
            "{}x1".format(self.animation_delay),
        ] + self.output_paths

        # last screenshot lasts one more second in the gif, to see when the loop ends
        animate_command.extend(
            [
                "-delay",
                "{}x1".format(int(self.animation_delay) + 1),
                animate_command.pop(),
                "{}.gif".format(self.output_prefix),
            ]
        )

        subprocess.call(animate_command)

        if clear:
            for output_path in self.output_paths:
                os.remove(output_path)


class Client:
    COLORS = [
        "#44cc44",  # green
        "#cc44cc",  # magenta
        "#4444cc",  # blue
        "#cccc44",  # yellow
        "#44cccc",  # cyan
        "#cccccc",  # white
        "#777777",  # gray
        "#ffa500",  # orange
        "#333333",  # black
    ]

    def __init__(self):
        self.client = InteractiveCommandClient(IPCCommandInterface(IPCClient(find_sockfile())))

    def current_group(self):
        return self.client.group[self.client.group.info().get("name")]

    def switch_to_group(self, group):
        if isinstance(group, str):
            self.client.group[group].toscreen()
        else:
            group.toscreen()

    def spawn_window(self, color):
        if isinstance(color, int):
            color = Client.COLORS[color]
        self.client.spawn(
            "xterm +ls -hold -e printf '\e]11;{}\007'".format(color)
        )

    def prepare_layout(self, layout, windows, commands=None):
        # set selected layout
        self.client.group.setlayout(layout)

        # spawn windows
        for i in range(windows):
            self.spawn_window(i)
            time.sleep(0.05)

        # prepare layout
        if commands:
            color = windows
            for cmd in commands:
                if cmd == "spawn":
                    self.spawn_window(color)
                    color += 1
                else:
                    self.run_layout_command(cmd)
                time.sleep(0.05)

    def run_layout_command(self, cmd):
        getattr(self.client.layout, cmd)()

    def kill_group_windows(self):
        while len(self.client.layout.info().get("clients")) > 0:
            try:
                self.client.window.kill()
            except CommandError:
                pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-b",
        "--commands-before",
        dest="commands_before",
        default="",
        help="Commands to run before starting to take screenshots.",
    )
    parser.add_argument(
        "-c",
        "--comment",
        dest="comment",
        default="",
        help="Comment to add at the end of the screenshot filenames.",
    )
    parser.add_argument(
        "-C",
        "--clear",
        dest="clear",
        action="store_true",
        default=False,
        help="Whether to delete the PNG files after animating them into GIFs.",
    )
    parser.add_argument(
        "-d",
        "--delay",
        dest="delay",
        default="1",
        help="Delay between each frame of the animated GIF in seconds.",
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
        default="300x200",
        help="The size of the generated screenshots (WIDTHxHEIGHT).",
    )
    parser.add_argument(
        "-n",
        "--name",
        dest="name",
        default="",
        help="The name of the generated screenshot files (don't append the extension)."
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
    try:
        client.prepare_layout(
            args.layout, args.windows, args.commands_before.split(" ") if args.commands_before else []
        )
    except (SelectError, CommandError):
        traceback.print_exc()
        sys.exit(1)

    # wait a bit to make sure everything is in place
    time.sleep(0.5)

    # prepare screenshot output path prefix
    output_dir = os.path.join(args.output_dir, args.layout)
    os.makedirs(output_dir, exist_ok=True)
    name = args.name or "_".join(args.commands) or args.layout
    if args.comment:
        name += "-{}".format(args.comment)
    output_prefix = os.path.join(output_dir, name)

    # run commands and take a screenshot between each, animate into a gif at the end
    screen = Screenshooter(output_prefix, args.geometry, args.delay)
    screen.shoot()
    for cmd in args.commands:
        client.run_layout_command(cmd)
        time.sleep(0.05)
        screen.shoot()
    screen.animate(clear=args.clear)

    # kill windows
    client.kill_group_windows()

    # switch back to original group
    client.switch_to_group(original_group)

    sys.exit(0)
