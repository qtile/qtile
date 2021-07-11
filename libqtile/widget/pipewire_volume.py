import subprocess

from libqtile import bar
from libqtile.widget import base

__all__ = [
    'PWVolume',
]

class PWVolume(base._TextBox):
    """Widget that can display and change volume when using pipewire

    By default, this widget uses ``pamixer`` to get and set the volume so users
    will need to make sure this is installed. Alternatively, users may set the
    relevant parameters for the widget to use a different application.

    If theme_path is set it draw widget as icons.
    """
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ("sink", None, "Sink Id"),
        ("source", None, "Source Id"),
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
        self.add_defaults(PWVolume.defaults)
        if self.theme_path:
            self.length_type = bar.STATIC
            self.length = 0
        self.surfaces = {}
        self.volume = None

        self.add_callbacks({
            'Button1': self.cmd_mute,
            'Button3': self.cmd_run_app,
            'Button4': self.cmd_increase_vol,
            'Button5': self.cmd_decrease_vol,
        })

    def timer_setup(self):
        self.timeout_add(self.update_interval, self.update)
        if self.theme_path:
            self.setup_images()

    def create_pamixer_command(self, *args):
        cmd = ['pamixer']

        if (self.sink is not None):
            cmd.extend(['--sink', str(self.cardid)])

        if (self.source is not None):
            cmd.extend(['--source', str(self.device)])

        cmd.extend([x for x in args])
        return cmd

    def button_press(self, x, y, button):
        base._TextBox.button_press(self, x, y, button)
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
        from libqtile import images
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

    def get_mute(self):
        try:
            get_mute_cmd = self.create_pamixer_command('--get-mute')

            mute_status = self.call_process(get_mute_cmd)
        except subprocess.CalledProcessError:
            return False

        return bool(mute_status)

    def get_volume(self):
        try:
            get_volume_cmd = self.create_pamixer_command('--get-volume')

            if self.get_volume_command:
                get_volume_cmd = self.get_volume_command

            mixer_out = self.call_process(get_volume_cmd)
        except subprocess.CalledProcessError:
            return -1

        if self.get_mute():
            return -1

        return int(mixer_out)

    def draw(self):
        if self.theme_path:
            self.drawer.draw(offsetx=self.offset, width=self.length)
        else:
            base._TextBox.draw(self)

    def cmd_increase_vol(self):
        if self.volume_up_command is not None:
            subprocess.call(self.volume_up_command, shell=True)
        else:
            subprocess.call(self.create_pamixer_command('-i',
                                                       str(self.step)))

    def cmd_decrease_vol(self):
        if self.volume_down_command is not None:
            subprocess.call(self.volume_down_command, shell=True)
        else:
            subprocess.call(self.create_pamixer_command('-d',
                                                       str(self.step)))

    def cmd_mute(self):
        if self.mute_command is not None:
            subprocess.call(self.mute_command, shell=True)
        else:
            if self.get_mute():
                subprocess.call(self.create_pamixer_command('-u'))
            else:
                subprocess.call(self.create_pamixer_command('-m'))

    def cmd_run_app(self):
        if self.volume_app is not None:
            subprocess.Popen(self.volume_app, shell=True)
