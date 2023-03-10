import os
import subprocess
import time

from libqtile.command_client import InteractiveCommandClient
from libqtile.command_interface import IPCCommandInterface
from libqtile.ipc import Client as IPCClient
from libqtile.ipc import find_sockfile


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
        self.color = 0
        self.client = InteractiveCommandClient(IPCCommandInterface(IPCClient(find_sockfile())))

    def current_group(self):
        return self.client.group[self.client.group.info().get("name")]

    def switch_to_group(self, group):
        if isinstance(group, str):
            self.client.group[group].toscreen()
        else:
            group.toscreen()

    def spawn_window(self, color=None):
        if color is None:
            color = self.color
            self.color += 1
        if isinstance(color, int):
            color = Client.COLORS[color]
        self.client.spawn("xterm +ls -hold -e printf '\e]11;{}\007'".format(color))  # noqa: W605

    def prepare_layout(self, layout, windows, commands=None):
        # set selected layout
        self.client.group.setlayout(layout)

        # spawn windows
        for i in range(windows):
            self.spawn_window()
            time.sleep(0.05)

        # prepare layout
        if commands:
            for cmd in commands:
                self.run_layout_command(cmd)
                time.sleep(0.05)

    def clean_layout(self, commands=None):
        if commands:
            for cmd in commands:
                self.run_layout_command(cmd)
                time.sleep(0.05)
        self.kill_group_windows()

    def run_layout_command(self, cmd):
        if cmd == "spawn":
            self.spawn_window()
        else:
            getattr(self.client.layout, cmd)()

    def kill_group_windows(self):
        while len(self.client.layout.info().get("clients")) > 0:
            try:
                self.client.window.kill()
            except Exception:
                pass
        self.color = 0


class Screenshooter:
    def __init__(self, output_prefix, geometry, animation_delay):
        self.output_prefix = output_prefix
        self.geometry = geometry
        self.number = 1
        self.animation_delay = animation_delay
        self.output_paths = []

    def shoot(self, numbered=True, compress="lossless"):
        if numbered:
            output_path = "{}.{}.png".format(self.output_prefix, self.number)
        else:
            output_path = "{}.png".format(self.output_prefix)
        thumbnail_path = output_path.replace(".png", "-thumb.png")

        # take screenshot with scrot
        subprocess.call(["scrot", "-o", "-t", self.geometry, output_path])

        # only keep the thumbnail
        os.rename(thumbnail_path, output_path)

        # compress PNG (only if pngquant is available)
        if compress:
            self.compress(compress, output_path)

        # add this path to the animation command
        self.output_paths.append(output_path)

        self.number += 1

    def compress(self, method, file_path):
        compress_command = [
            "pngquant",
            {"lossless": "--speed=1", "lossy": "--quality=0-90"}.get(method),
            "--strip",
            "--skip-if-larger",
            "--force",
            "--output",
            file_path,
            file_path,
        ]

        try:
            subprocess.call(compress_command)
        except FileNotFoundError:
            pass

    def animate(self, delays=None, clear=False):
        # TODO: use delays to build animation with custom delay between each frame

        animate_command = [
            "convert",
            "-loop",
            "0",
            "-colors",
            "80",
            "-delay",
            self.animation_delay,
        ] + self.output_paths

        # last screenshot lasts two seconds in the gif, to see when the loop ends
        animate_command.extend(
            [
                "-delay",
                "2x1",
                animate_command.pop(),
                "{}.gif".format(self.output_prefix),
            ]
        )

        subprocess.call(animate_command)

        if clear:
            for output_path in self.output_paths:
                os.remove(output_path)
