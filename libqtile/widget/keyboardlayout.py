import subprocess
from subprocess import CalledProcessError
import base
from .. import bar


class KeyboardLayout(base._TextBox):
    """
        Widget for changing and displaying the current keyboard layout.
        It requires setxkbmap to be available in the sytem.
    """
    defaults = [
        ("update_interval", 1, "Update time in seconds."),
    ]

    def __init__(self, configured_keyboards=['us'],
                 width=bar.CALCULATED, **config):
        """
            :configured_keyboards A list of predefined keyboard layouts
            represented as strings. For example: ['us', 'us colemak', 'es', 'fr'].
        """
        base._TextBox.__init__(self, "", width, **config)
        self.add_defaults(KeyboardLayout.defaults)
        self.configured_keyboards = configured_keyboards
        self.text = self._get_keyboard()

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        self.text = self._get_keyboard()
        self.timeout_add(self.update_interval, self.update)

    def button_press(self, x, y, button):
        if button == 1:
            self.next_keyboard()

    def update(self):
        self.text = self._get_keyboard()
        self.bar.draw()
        return True

    def next_keyboard(self):
        """
            Set the next layout in the list of configured keyboard layouts as
            new current layout in use.
            If the current keyboard layout is not in the list, it will set as
            new layout the first one in the list.
        """

        current_keyboard = self._get_keyboard()
        if current_keyboard in self.configured_keyboards:
            # iterate the list circularly
            next_keyboard = self.configured_keyboards[
                (self.configured_keyboards.index(current_keyboard) + 1) %
                len(self.configured_keyboards)]
        else:
            next_keyboard = self.configured_keyboards[0]
        self._set_keyboard(next_keyboard)

    def _get_keyboard(self):
        """
            Return the currently used keyboard layout as a string.
            Examples: "us", "us dvorak".
            In case of error returns "unknown".
        """
        try:
            keyboard = subprocess.check_output(["python", "kb.py"]).strip().upper()
            return keyboard.__str__()
        except CalledProcessError as e:
            self.log.error('Can not change the keyboard layout: {0}'
                           .format(e))
        except OSError as e:
            self.log.error('Please, check that setxkbmap is available: {0}'
                           .format(e))
        return "unknown"

    def _set_keyboard(self, keyboard):
        command = ['setxkbmap']
        command.extend(keyboard.split(" "))
        try:
            subprocess.check_call(command)
        except CalledProcessError as e:
            self.log.error('Can not change the keyboard layout: {0}'
                           .format(e))
        except OSError as e:
            self.log.error('Please, check that setxkbmap is available: {0}'
                           .format(e))
