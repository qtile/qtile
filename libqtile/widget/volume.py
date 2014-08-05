import os
import re
import subprocess

import cairocffi

from . import base
from .. import bar
from six import u

__all__ = [
    'Volume',
]

re_vol = re.compile('\[(\d?\d?\d?)%\]')


class Volume(base._TextBox):
    ''' Widget that display and change volume
        if theme_path is set it draw widget as
        icons '''
    defaults = [
        ("cardid", 0, "Card Id"),
        ("channel", "Master", "Channel"),
        ("padding", 3, "Padding left and right. Calculated if None."),
        ("theme_path", None, "Path of the icons"),
        ("update_interval", 0.2, "Update time in seconds."),
        ("emoji", False, "Use emoji to display volume states"),
    ]

    def __init__(self, **config):
        base._TextBox.__init__(self, '0', width=bar.CALCULATED, **config)
        self.add_defaults(Volume.defaults)
        if self.theme_path:
            self.width_type = bar.STATIC
            self.width = 0
        self.surfaces = {}
        self.volume = None
        self.timeout_add(self.update_interval, self.update)

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        if self.theme_path:
            self.setup_images()

    def button_press(self, x, y, button):
        if button == 5:
            subprocess.call([
                'amixer',
                '-q',
                '-c',
                str(self.cardid),
                'sset',
                self.channel,
                '2dB-'
            ])
        elif button == 4:
            subprocess.call([
                'amixer',
                '-q',
                '-c',
                str(self.cardid),
                'sset',
                self.channel,
                '2dB+'
            ])
        elif button == 1:
            subprocess.call([
                'amixer',
                '-q',
                '-c',
                str(self.cardid),
                'sset',
                self.channel,
                'toggle'
            ])
        self.draw()

    def update(self):
        if self.configured:
            vol = self.get_volume()
            if vol != self.volume:
                self.volume = vol
                # Update the underlying canvas size before actually attempting
                # to figure out how big it is and draw it.
                self._update_drawer()
                self.bar.draw()
        return True

    def _update_drawer(self):
        if self.theme_path:
            self.drawer.clear(self.background or self.bar.background)
            if self.volume <= 0:
                img_name = 'audio-volume-muted'
            elif self.volume <= 30:
                img_name = 'audio-volume-low'
            elif self.volume < 80:
                img_name = 'audio-volume-medium'
            elif self.volume >= 80:
                img_name = 'audio-volume-high'

            self.drawer.ctx.set_source(self.surfaces[img_name])
            self.drawer.ctx.paint()
        elif self.emoji:
            if self.volume <= 0:
                self.text = u('\U0001f507')
            elif self.volume <= 30:
                self.text = u('\U0001f508')
            elif self.volume < 80:
                self.text = u('\U0001f509')
            elif self.volume >= 80:
                self.text = u('\U0001f50a')
        else:
            if self.volume == -1:
                self.text = 'M'
            else:
                self.text = '%s%%' % self.volume

    def setup_images(self):
        for img_name in (
            'audio-volume-high',
            'audio-volume-low',
            'audio-volume-medium',
            'audio-volume-muted'
        ):

            try:
                img = cairocffi.ImageSurface.create_from_png(
                    os.path.join(self.theme_path, '%s.png' % img_name)
                )
            except cairocffi.Error:
                self.theme_path = None
                self.width_type = bar.CALCULATED
                self.qtile.log.exception('Volume switching to text mode')
                return
            input_width = img.get_width()
            input_height = img.get_height()

            sp = input_height / float(self.bar.height - 1)

            width = input_width / sp
            if width > self.width:
                self.width = int(width) + self.actual_padding * 2

            imgpat = cairocffi.SurfacePattern(img)

            scaler = cairocffi.Matrix()

            scaler.scale(sp, sp)
            scaler.translate(self.actual_padding * -1, 0)
            imgpat.set_matrix(scaler)

            imgpat.set_filter(cairocffi.FILTER_BEST)
            self.surfaces[img_name] = imgpat

    def get_volume(self):
        mixerprocess = subprocess.Popen(
            [
                'amixer',
                '-c',
                str(self.cardid),
                'sget',
                self.channel
            ],
            stdout=subprocess.PIPE
        )
        mixer_out = mixerprocess.communicate()[0]
        if mixerprocess.returncode:
            return -1

        if '[off]' in mixer_out:
            return -1

        volgroups = re_vol.search(mixer_out)
        if volgroups:
            return int(volgroups.groups()[0])
        else:
            # this shouldn't happend
            return -1

    def draw(self):
        if self.theme_path:
            self.drawer.draw(self.offset, self.width)
        else:
            base._TextBox.draw(self)
