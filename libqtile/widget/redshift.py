# Copyright (c) 2024 Saath Satheeshkumar(saths008)
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
import subprocess

from libqtile.command.base import expose_command
from libqtile.widget import base
from libqtile.widget.base import _TextBox


class GammaGroup:
    """
    GammaGroup is a helper class to group redshift gamma settings.
    """

    def __init__(self, red, green, blue):
        self.gamma_red = red
        self.gamma_green = green
        self.gamma_blue = blue

    def _format_gamma(self, format_txt: str) -> str:
        return format_txt.format(
            gamma_red=self.gamma_red,
            gamma_green=self.gamma_green,
            gamma_blue=self.gamma_blue,
        )

    def _redshift_fmt(self) -> str:
        return f"{self.gamma_red}:{self.gamma_green}:{self.gamma_blue}"

    def __repr__(self) -> str:
        return f"Gamma: {self._redshift_fmt()}"

    def __str__(self) -> str:
        return (
            f"GammaGroup(red={self.gamma_red}, green={self.gamma_green}, blue={self.gamma_blue})"
        )


class RedshiftDriver:
    """
    RedshiftDriver is a helper class
    that executes all of the interactions with redshift.
    """

    def enable(self, temperature, gamma: GammaGroup, brightness):
        """
        Run redshift command with given parameters
        """
        subprocess.run(
            [
                "redshift",
                "-P",
                "-O",
                str(temperature),
                "-b",
                str(brightness),
                "-g",
                gamma._redshift_fmt(),
            ],
            check=True,
        )

    def reset(self):
        """
        Call reset on redshift to reset to default settings.
        """
        subprocess.run(["redshift", "-x"], check=True)


class Redshift(_TextBox, base.PaddingMixin):
    """
    Redshift widget provides the following functionality:
      - Call redshift with a specific brightness, temperature and gamma config without using your location.

    The redshift command can be called by just left-clicking the widget and disabling it the same way.

    Scrolling through the widget will show the settings,
    ie. the brightness, gamma and temperature that redshift
    will use if the widget is enabled.

    Widget requirements: redshift_

    .. _redshift: https://github.com/jonls/redshift
    """

    defaults = [
        ("brightness", 1.0, "Redshift brightness"),
        (
            "disabled_txt",
            "󱠃",
            "Text to show when redshift is disabled. NOTE: by default, a nerd icon is used."
            "Available fields: 'brightness' brightness to set when redshift is enabled, "
            "'is_enabled' boolean to state whether the widget is enabled or not, "
            "'gamma_blue' gamma blue value to set when redshift is enabled, "
            "'gamma_green' gamma green value to set when redshift is enabled, "
            "'gamma_red' gamma red value to set when redshift is enabled, "
            "'temperature' temperature to set when redshift is enabled, ",
        ),
        (
            "enabled_txt",
            "󰛨",
            "Text to show when redshift is disabled. NOTE: by default, a nerd icon is used."
            "Available fields: see disabled_txt's available fields for all of them",
        ),
        ("gamma_red", 1.0, "Redshift gamma red setting"),
        ("gamma_blue", 1.0, "Redshift gamma blue"),
        ("gamma_green", 1.0, "Redshift gamma green"),
        ("font", "sans", "Default font"),
        ("fontsize", 20, "Font size"),
        ("foreground", "ffffff", "Font colour for information text"),
        ("temperature", 1700, "Redshift temperature to set when enabled"),
        (
            "temperature_fmt",
            "Temperature: {temperature}",
            "Text to display when showing temperature text"
            "Available fields: 'temperature' temperature to set when redshift is enabled. ",
        ),
        (
            "brightness_fmt",
            "Brightness: {brightness}",
            "Text to display when showing brightness text"
            "Available fields: 'brightness' brightness to set when redshift is enabled. ",
        ),
        (
            "gamma_fmt",
            "Gamma: {gamma_red}:{gamma_green}:{gamma_blue}",
            "Text to display when showing gamma text"
            "Available fields: 'gamma_red' gamma red value to set when redshift is enabled. "
            "'gamma_blue' gamma blue value to set when redshift is enabled. "
            "'gamma_green' gamma green value to set when redshift is enabled. ",
        ),
    ]

    supported_backends = {"x11"}

    def __init__(self, **config):
        _TextBox.__init__(self, **config)
        self.add_defaults(Redshift.defaults)
        self.add_defaults(base.PaddingMixin.defaults)
        self.is_enabled = False
        self._line_index = 0
        self._lines = []
        self.redshift_driver = RedshiftDriver()
        self.add_callbacks(
            {
                "Button1": self.click,
                "Button4": self.scroll_up,
                "Button5": self.scroll_down,
            }
        )

    def _configure(self, qtile, bar):
        _TextBox._configure(self, qtile, bar)
        # disable redshift so we have a known initial state
        self.reset_redshift()
        self._set_lines()
        # set text after bar configuration is done
        self.qtile.call_soon(self._set_text)

    @expose_command
    def scroll_up(self):
        """
        Scroll up to next item.
        """
        self._scroll(1)

    @expose_command
    def scroll_down(self):
        """
        Scroll down to next item.
        """
        self._scroll(-1)

    def show_line(self):
        """
        Update the text with the the current index in lines.
        """
        if not self._lines:
            return

        line = self._lines[self._line_index]

        self.update(line)

    @expose_command
    def enable_redshift(self):
        """
        Enable redshift with the temp, gamma and brightness params.
        """
        gamma_val = GammaGroup(self.gamma_red, self.gamma_green, self.gamma_blue)
        try:
            self._get_rs_driver().enable(self.temperature, gamma_val, self.brightness)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"redshift: could not enable redshift: {e}")

    @expose_command
    def click(self):
        """
        Either enable or disable the widget ONLY if we are currently on the
        first line ie. the enabled/disabled text.
        """
        if self._line_index != 0:
            return
        if self.is_enabled:
            self.reset_redshift()
        else:
            self.enable_redshift()
        self.is_enabled = not self.is_enabled
        self._set_text()

    @expose_command
    def reset_redshift(self):
        """
        Make a call to redshift to reset everything.
        """
        try:
            self._get_rs_driver().reset()
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"redshift: could not reset redshift: {e}")

    def _scroll(self, step):
        """
        Scroll up/down dictated by 'step' the items
        and then display that item.
        """
        # Make sure that the lines var is set, maybe
        # some of the values have been updated?
        self._set_lines()
        self._line_index = (self._line_index + step) % len(self._lines)
        self.show_line()

    def _set_lines(self):
        """
        Set the list of formatted text items to scroll through.
        """
        first_text = ""
        if self.is_enabled:
            first_text = self.enabled_txt
        else:
            first_text = self.disabled_txt

        first_text = self._format_first_text(str(first_text))

        self._lines = [
            first_text,
            self._format_brightness_text(),
            self._format_temp_text(),
            self._format_gamma_text(
                GammaGroup(self.gamma_red, self.gamma_green, self.gamma_blue)
            ),
        ]

    def _set_text(self):
        """
        Update to the current index of lines.
        """
        text = ""
        if self._line_index == 0:
            if self.is_enabled:
                text = self._format_first_text(str(self.enabled_txt))
            else:
                text = self._format_first_text(str(self.disabled_txt))
        else:
            text = self._lines[self._line_index]
        self.update(text)

    def _format_temp_text(self) -> str:
        """
        Format the temperature text.
        """
        return str(self.temperature_fmt).format(temperature=self.temperature)

    def _format_brightness_text(self) -> str:
        """
        Format the brightness text.
        """
        return str(self.brightness_fmt).format(brightness=self.brightness)

    def _format_gamma_text(self, gamma: GammaGroup) -> str:
        """
        Format the gamma text.
        """
        return gamma._format_gamma(str(self.gamma_fmt))

    def _format_first_text(self, txt: str) -> str:
        """
        Format the enabled/disabled text (aka first_text).
        """
        return txt.format(
            brightness=self.brightness,
            temperature=self.temperature,
            gamma_red=self.gamma_red,
            gamma_green=self.gamma_green,
            gamma_blue=self.gamma_blue,
            is_enabled=self.is_enabled,
        )

    def _get_rs_driver(self):
        return self.redshift_driver
