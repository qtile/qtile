import subprocess
from subprocess import CalledProcessError
import base
import re


class KeyboardLayout(base.InLoopPollText):
    """
        Widget for changing and displaying the current keyboard layout.
        It requires setxkbmap to be available in the sytem.
    """
    defaults = [
        ("update_interval", 1, "Update time in seconds."),
        ("configured_keyboards", "us", "A list of predefined keyboard layouts "
            "represented as strings. For example: "
            "['us', 'us colemak', 'es', 'fr']."),
    ]

    def __init__(self, **config):
        base.InLoopPollText.__init__(self, **config)
        self.add_defaults(KeyboardLayout.defaults)

    def button_press(self, x, y, button):
        if button == 1:
            self.next_keyboard()

    def next_keyboard(self):
        """
            Set the next layout in the list of configured keyboard layouts as
            new current layout in use.
            If the current keyboard layout is not in the list, it will set as
            new layout the first one in the list.
        """

        current_keyboard = self.poll()
        if current_keyboard in self.configured_keyboards:
            # iterate the list circularly
            next_keyboard = self.configured_keyboards[
                (self.configured_keyboards.index(current_keyboard) + 1) %
                len(self.configured_keyboards)]
        else:
            next_keyboard = self.configured_keyboards[0]
        self._set_keyboard(next_keyboard)

    def poll(self):
        """
            Return the currently used keyboard layout as a string.
            Examples: "us", "us dvorak".
            In case of error returns "unknown".
        """
        try:
            xset_output = subprocess.check_output(["xset", "-q"])
            keyboard = _Keyboard(self.configured_keyboards).get_keyboard_layout(xset_output).upper()
            return str(keyboard)
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


class _Keyboard(object):

    def __init__(self, configured_keyboards):
        if len(configured_keyboards) == 1:
            self.languages = {
                'first': configured_keyboards[0],
                'second': 'None',
            }
        else:
            self.languages = {
                'first': configured_keyboards[0],
                'second': configured_keyboards[1],
            }
        self.regular_strings = {
            'hexadecimal': {
                'first': """\w{4}e\w{3}""",
                'second': """\w{4}f\w{3}""",
            },
            'binary': {
                'first': """\w{4}0\w{3}""",
                'second': """\w{4}1\w{3}""",
            },
            "inetger": "\d{8}",
            "led_mask": """LED mask:\s\s\w{8}""",
        }

    def get_keyboard_layout(self, xset_output):
        raw_list = []

        for item in xset_output.strip().splitlines():
            if re.search(self.regular_strings['led_mask'], item):
                raw_led_mask = re.search(self.regular_strings['led_mask'], item).group()
                raw_list = raw_led_mask.split(':')
                led_mask = raw_list[1].strip()
                break

        if not re.search(self.regular_strings['inetger'], led_mask):
            cur_regular_strings = self.regular_strings['hexadecimal']
        else:
            cur_regular_strings = self.regular_strings['binary']

        if re.search(cur_regular_strings['first'], led_mask):
            result = self.languages['first']
        elif re.search(cur_regular_strings['second'], led_mask):
            result = self.languages['second']
        else:
            result = "ERR"
        return result
