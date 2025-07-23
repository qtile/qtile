# Copyright (c) 2010, 2012, 2014 roger
# Copyright (c) 2011 Kirk Strauser
# Copyright (c) 2011 Florian Mounier
# Copyright (c) 2011 Mounier Florian
# Copyright (c) 2011 Roger Duran
# Copyright (c) 2012-2015 Tycho Andersen
# Copyright (c) 2013 Tao Sauvage
# Copyright (c) 2013 Craig Barnes
# Copyright (c) 2014-2015 Sean Vig
# Copyright (c) 2014 Adi Sieker
# Copyright (c) 2014 dmpayton
# Copyright (c) 2014 Jody Frankowski
# Copyright (c) 2016 Christoph Lassner
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import re
import subprocess

from libqtile import bar
from libqtile.command.base import expose_command
from libqtile.log_utils import logger
from libqtile.widget import base

__all__ = [
    "Volume",
]

re_vol = re.compile(r"(\d?\d?\d?)%")


class Volume(base._TextBox):
    """Widget that display and change volume

    By default, this widget uses ``amixer`` to get and set the volume so users
    will need to make sure this is installed. Alternatively, users may set the
    relevant parameters for the widget to use a different application.

    If theme_path is set it draw widget as icons.
    """

    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ("cardid", None, "Card Id"),
        ("device", "default", "Device Name"),
        ("channel", "Master", "Channel"),
        ("padding", 3, "Padding left and right. Calculated if None."),
        ("update_interval", 0.2, "Update time in seconds."),
        ("theme_path", None, "Path of the icons"),
        (
            "emoji",
            False,
            "Use emoji to display volume states, only if ``theme_path`` is not set."
            "The specified font needs to contain the correct unicode characters.",
        ),
        (
            "emoji_list",
            ["\U0001f507", "\U0001f508", "\U0001f509", "\U0001f50a"],
            "List of emojis/font-symbols to display volume states, only if ``emoji`` is set."
            " List contains 4 symbols, from lowest volume to highest.",
        ),
        ("mute_command", None, "Mute command"),
        ("mute_foreground", None, "Foreground color for mute volume."),
        ("mute_format", "M", "Format to display when volume is muted."),
        ("unmute_format", "{volume}%", "Format of text to display when volume is not muted."),
        ("volume_app", None, "App to control volume"),
        ("volume_up_command", None, "Volume up command"),
        ("volume_down_command", None, "Volume down command"),
        (
            "get_volume_command",
            None,
            "Command to get the current volume. "
            "The expected output should include 1-3 numbers and a ``%`` sign.",
        ),
        ("check_mute_command", None, "Command to check mute status"),
        (
            "check_mute_string",
            "[off]",
            "String expected from check_mute_command when volume is muted."
            "When the output of the command matches this string, the"
            "audio source is treated as muted.",
        ),
        (
            "step",
            2,
            "Volume change for up an down commands in percentage."
            "Only used if ``volume_up_command`` and ``volume_down_command`` are not set.",
        ),
    ]

    def __init__(self, **config):
        base._TextBox.__init__(self, "", **config)
        self.add_defaults(Volume.defaults)
        self.surfaces = {}
        self.volume = None
        self.is_mute = False

        self.add_callbacks(
            {
                "Button1": self.mute,
                "Button3": self.run_app,
                "Button4": self.increase_vol,
                "Button5": self.decrease_vol,
            }
        )

    def _configure(self, qtile, parent_bar):
        if self.theme_path:
            self.length_type = bar.STATIC
            self.length = 0
        base._TextBox._configure(self, qtile, parent_bar)
        self.unmute_foreground = self.foreground

    def timer_setup(self):
        self.timeout_add(self.update_interval, self.update)
        if self.theme_path:
            self.setup_images()

    def create_amixer_command(self, *args):
        cmd = ["amixer"]

        if self.cardid is not None:
            cmd.extend(["-c", str(self.cardid)])

        if self.device is not None:
            cmd.extend(["-D", str(self.device)])

        cmd.extend([x for x in args])
        return subprocess.list2cmdline(cmd)

    def button_press(self, x, y, button):
        base._TextBox.button_press(self, x, y, button)
        self.draw()

    def update(self):
        vol, muted = self.get_volume()
        if vol != self.volume or muted != self.is_mute:
            self.volume = vol
            self.is_mute = muted
            # Update the underlying canvas size before actually attempting
            # to figure out how big it is and draw it.
            self._update_drawer()
            self.bar.draw()
        self.timeout_add(self.update_interval, self.update)

    def _update_drawer(self):
        if self.mute_foreground is not None:
            self.layout.colour = self.mute_foreground if self.is_mute else self.unmute_foreground

        if self.theme_path:
            self.drawer.clear(self.background or self.bar.background)
            if self.volume <= 0 or self.is_mute:
                img_name = "audio-volume-muted"
            elif self.volume <= 30:
                img_name = "audio-volume-low"
            elif self.volume < 80:
                img_name = "audio-volume-medium"
            else:  # self.volume >= 80:
                img_name = "audio-volume-high"

            self.drawer.ctx.set_source(self.surfaces[img_name])
            self.drawer.ctx.paint()
        elif self.emoji:
            if len(self.emoji_list) < 4:
                self.emoji_list = ["\U0001f507", "\U0001f508", "\U0001f509", "\U0001f50a"]
                logger.warning(
                    "Emoji list given has less than 4 items. Falling back to default emojis."
                )

            if self.volume <= 0 or self.is_mute:
                self.text = self.emoji_list[0]
            elif self.volume <= 30:
                self.text = self.emoji_list[1]
            elif self.volume < 80:
                self.text = self.emoji_list[2]
            elif self.volume >= 80:
                self.text = self.emoji_list[3]
        else:
            self.text = (
                self.mute_format if self.is_mute or self.volume < 0 else self.unmute_format
            ).format(volume=self.volume)

    def setup_images(self):
        from libqtile import images

        names = (
            "audio-volume-high",
            "audio-volume-low",
            "audio-volume-medium",
            "audio-volume-muted",
        )
        d_images = images.Loader(self.theme_path)(*names)
        new_height = self.bar.size - 2
        for name, img in d_images.items():
            img.resize(height=new_height)
            if img.width > self.length:
                self.length = img.width + self.padding * 2
            self.surfaces[name] = img.pattern

    def get_volume(self):
        try:
            if self.get_volume_command is not None:
                get_volume_cmd = self.get_volume_command
            else:
                get_volume_cmd = self.create_amixer_command("sget", self.channel)

            mixer_out = subprocess.getoutput(get_volume_cmd)
        except subprocess.CalledProcessError:
            return -1, False

        check_mute = mixer_out
        if self.check_mute_command:
            check_mute = subprocess.getoutput(self.check_mute_command)

        muted = self.check_mute_string in check_mute

        volgroups = re_vol.search(mixer_out)
        if volgroups:
            return int(volgroups.groups()[0]), muted
        else:
            # this shouldn't happen
            return -1, muted

    def draw(self):
        if self.theme_path:
            self.draw_at_default_position()
        else:
            base._TextBox.draw(self)

    @expose_command()
    def increase_vol(self):
        if self.volume_up_command is not None:
            volume_up_cmd = self.volume_up_command
        else:
            volume_up_cmd = self.create_amixer_command(
                "-q", "sset", self.channel, f"{self.step}%+"
            )

        subprocess.call(volume_up_cmd, shell=True)

    @expose_command()
    def decrease_vol(self):
        if self.volume_down_command is not None:
            volume_down_cmd = self.volume_down_command
        else:
            volume_down_cmd = self.create_amixer_command(
                "-q", "sset", self.channel, f"{self.step}%-"
            )

        subprocess.call(volume_down_cmd, shell=True)

    @expose_command()
    def mute(self):
        if self.mute_command is not None:
            mute_cmd = self.mute_command
        else:
            mute_cmd = self.create_amixer_command("-q", "sset", self.channel, "toggle")

        subprocess.call(mute_cmd, shell=True)

    @expose_command()
    def run_app(self):
        if self.volume_app is not None:
            subprocess.Popen(self.volume_app, shell=True)
