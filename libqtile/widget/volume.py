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

from . import base
from .. import bar

__all__ = [
    'Volume',
]

re_vol = re.compile(r'\[(\d?\d?\d?)%\]')
BUTTON_UP = 4
BUTTON_DOWN = 5
BUTTON_MUTE = 1
BUTTON_RIGHT = 3


class Volume(base._TextBox):
    """Widget that display and change volume

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
        ("emoji", False, "Use emoji to display volume states, only if ``theme_path`` is not set."
                         "The specified font needs to contain the correct unicode characters."),
        ("mute_command", None, "Mute command"),
        ("volume_app", None, "App to control volume"),
        ("volume_up_command", None, "Volume up command"),
        ("volume_down_command", None, "Volume down command"),
        ("get_volume_command", None, "Command to get the current volume"),
        ("step", 2, "Volume change for up an down commands in percentage."
                    "Only used if ``volume_up_command`` and ``volume_down_command`` are not set.")
    ]

    def __init__(self, **config):
        base._TextBox.__init__(self, '0', width=bar.CALCULATED, **config)
        self.add_defaults(Volume.defaults)
        if self.theme_path:
            self.length_type = bar.STATIC
            self.length = 0
        self.surfaces = {}
        self.volume = None

    def timer_setup(self):
        self.timeout_add(self.update_interval, self.update)
        if self.theme_path:
            self.setup_images()

    def create_amixer_command(self, *args):
        cmd = ['amixer']

        if (self.cardid is not None):
            cmd.extend(['-c', str(self.cardid)])

        if (self.device is not None):
            cmd.extend(['-D', str(self.device)])

        cmd.extend([x for x in args])
        return cmd

    def button_press(self, x, y, button):
        if button == BUTTON_DOWN:
            if self.volume_down_command is not None:
                subprocess.call(self.volume_down_command, shell=True)
            else:
                subprocess.call(self.create_amixer_command('-q',
                                                           'sset',
                                                           self.channel,
                                                           '{}%-'.format(self.step)))
        elif button == BUTTON_UP:
            if self.volume_up_command is not None:
                subprocess.call(self.volume_up_command, shell=True)
            else:
                subprocess.call(self.create_amixer_command('-q',
                                                           'sset',
                                                           self.channel,
                                                           '{}%+'.format(self.step)))
        elif button == BUTTON_MUTE:
            if self.mute_command is not None:
                subprocess.call(self.mute_command, shell=True)
            else:
                subprocess.call(self.create_amixer_command('-q',
                                                           'sset',
                                                           self.channel,
                                                           'toggle'))
        elif button == BUTTON_RIGHT:
            if self.volume_app is not None:
                subprocess.Popen(self.volume_app, shell=True)

        self.draw()

    def update(self):
        vol = self.get_volume()
        if vol != self.volume:
            self.volume = vol
            # Update the underlying canvas size before actually attempting
            # to figure out how big it is and draw it.
            self._update_drawer()
            self.bar.draw()
        self.timeout_add(self.update_interval, self.update)

    def _update_drawer(self):
        if self.theme_path:
            self.drawer.clear(self.background or self.bar.background)
            if self.volume <= 0:
                img_name = 'audio-volume-muted'
            elif self.volume <= 30:
                img_name = 'audio-volume-low'
            elif self.volume < 80:
                img_name = 'audio-volume-medium'
            else:  # self.volume >= 80:
                img_name = 'audio-volume-high'

            self.drawer.ctx.set_source(self.surfaces[img_name])
            self.drawer.ctx.paint()
        elif self.emoji:
            if self.volume <= 0:
                self.text = u'\U0001f507'
            elif self.volume <= 30:
                self.text = u'\U0001f508'
            elif self.volume < 80:
                self.text = u'\U0001f509'
            elif self.volume >= 80:
                self.text = u'\U0001f50a'
        else:
            if self.volume == -1:
                self.text = 'M'
            else:
                self.text = '{}%'.format(self.volume)

    def setup_images(self):
        from .. import images
        names = (
            'audio-volume-high',
            'audio-volume-low',
            'audio-volume-medium',
            'audio-volume-muted',
        )
        d_images = images.Loader(self.theme_path)(*names)
        for name, img in d_images.items():
            new_height = self.bar.height - 1
            img.resize(height=new_height)
            if img.width > self.length:
                self.length = img.width + self.actual_padding * 2
            self.surfaces[name] = img.pattern

    def get_volume(self):
        try:
            get_volume_cmd = self.create_amixer_command('sget',
                                                        self.channel)

            if self.get_volume_command:
                get_volume_cmd = self.get_volume_command

            mixer_out = self.call_process(get_volume_cmd)
        except subprocess.CalledProcessError:
            return -1

        if '[off]' in mixer_out:
            return -1

        volgroups = re_vol.search(mixer_out)
        if volgroups:
            return int(volgroups.groups()[0])
        else:
            # this shouldn't happen
            return -1

    def draw(self):
        if self.theme_path:
            self.drawer.draw(offsetx=self.offset, width=self.length)
        else:
            base._TextBox.draw(self)

    def cmd_increase_vol(self):
        # Emulate button press.
        self.button_press(0, 0, BUTTON_UP)

    def cmd_decrease_vol(self):
        # Emulate button press.
        self.button_press(0, 0, BUTTON_DOWN)

    def cmd_mute(self):
        # Emulate button press.
        self.button_press(0, 0, BUTTON_MUTE)

    def cmd_run_app(self):
        # Emulate button press.
        self.button_press(0, 0, BUTTON_RIGHT)
