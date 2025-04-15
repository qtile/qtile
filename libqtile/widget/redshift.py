# Copyright (c) 2024 Saath Satheeshkumar (saths008)
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
from shutil import which

from libqtile.command.base import expose_command
from libqtile.log_utils import logger
from libqtile.widget.base import _TextBox


class GammaGroup:
    """
    GammaGroup is a helper class to group redshift gamma settings.
    """

    def __init__(self, red: float, green: float, blue: float):
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


class Redshift(_TextBox):
    """
    Redshift widget provides the following functionality:
      - Call redshift with a specific brightness, temperature and gamma config without using your location.
      - Increase/Decrease the brightness/temperature

    The redshift command can be called by just left-clicking the widget and disabling it the same way.

    If the widget is enabled, scrolling through the widget will show the settings:
    - brightness (limited to 2 dp)
    - gamma (can't be increased/decreased)
    - temperature (limited to 2 dp)
    - finally back to the default enabled/disabled text

    When at the temperature/brightness settings, the left-click/right-click mouse buttons can be used to
    increase/decrease respectively.

    Widget requirements: redshift_

    .. _redshift: https://github.com/jonls/redshift
    """

    defaults = [
        (
            "brightness",
            1.0,
            "Redshift brightness. Brightness has a lower bound of 0.1 and an upper bound of 1.0",
        ),
        ("brightness_step", 0.1, "The amount to increase/decrease the brightness by. "),
        (
            "disabled_txt",
            "󱠃",
            "Text to show when redshift is disabled. NOTE: by default, a nerd icon is used. "
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
            "Text to show when redshift is disabled. NOTE: by default, a nerd icon is used. "
            "Available fields: see disabled_txt's available fields for all of them",
        ),
        (
            "gamma_red",
            1.0,
            "Redshift gamma red setting. "
            "gamma_red has a lower bound of 0.1 and an upper bound of 10.0 .",
        ),
        (
            "gamma_blue",
            1.0,
            "Redshift gamma blue. "
            "gamma_blue has a lower bound of 0.1 and an upper bound of 10.0 .",
        ),
        (
            "gamma_green",
            1.0,
            "Redshift gamma green. "
            "gamma_green has a lower bound of 0.1 and an upper bound of 10.0 .",
        ),
        ("font", "sans", "Default font"),
        ("fontsize", 20, "Font size"),
        ("foreground", "ffffff", "Font colour for information text"),
        ("redshift_path", which("redshift"), "Path to redshift executable"),
        (
            "temperature",
            1700,
            "Redshift temperature to set when enabled. "
            "Temperature has a lower bound of 1000 and an upper bound of 25000.",
        ),
        (
            "temperature_step",
            100,
            "The amount to increase/decrease the temperature by.",
        ),
        (
            "temperature_fmt",
            "Temperature: {temperature}",
            "Text to display when showing temperature text. "
            "Available fields: 'temperature' temperature to set when redshift is enabled. ",
        ),
        (
            "brightness_fmt",
            "Brightness: {brightness}",
            "Text to display when showing brightness text. "
            "Available fields: 'brightness' brightness to set when redshift is enabled. ",
        ),
        (
            "gamma_fmt",
            "Gamma: {gamma_red}:{gamma_green}:{gamma_blue}",
            "Text to display when showing gamma text. "
            "Available fields: 'gamma_red' gamma red value to set when redshift is enabled, "
            "'gamma_blue' gamma blue value to set when redshift is enabled, "
            "'gamma_green' gamma green value to set when redshift is enabled. ",
        ),
    ]

    # declare the same defaults as above but with types
    # to stop LSP complaints
    brightness: float
    brightness_step: float
    disabled_txt: str
    enabled_txt: str
    gamma_red: float
    gamma_blue: float
    gamma_green: float
    redshift_path: str
    temperature: float
    temperature_step: float
    temperature_fmt: str
    brightness_fmt: str
    gamma_fmt: str

    supported_backends = {"x11"}

    def __init__(self, **config):
        _TextBox.__init__(self, **config)
        self.add_defaults(Redshift.defaults)
        self.is_enabled = False
        self._line_index = 0
        self._lines = []
        self.brightness_idx = 1
        self.temperature_idx = 2
        self.gamma_idx = 3
        # redshift's limits
        self.brightness_lower_lim = 0.1
        self.brightness_upper_lim = 1.0
        self.temperature_lower_lim = 1000
        self.temperature_upper_lim = 25000
        self.gamma_lower_lim = 0.1
        self.gamma_upper_lim = 10.0
        # Make sure fields are initialised to values
        # in bounds
        self._assert_brightness()
        self._assert_temperature()
        self.gamma_val = self._assert_gamma()
        self.add_callbacks(
            {
                "Button1": self.click,
                "Button3": self.right_click,
                "Button4": self.scroll_up,
                "Button5": self.scroll_down,
            }
        )
        self.error = None

    def _configure(self, qtile, bar):
        _TextBox._configure(self, qtile, bar)
        # disable redshift so we have a known initial state
        self.reset_redshift()
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
        assert self._lines, "lines arr should have been initialised"

        line = self._lines[self._line_index]

        self.update(line)

    @expose_command
    def click(self):
        """
        Has no action for the gamma line.
        Either enable or disable the widget if we are currently on the
        first line.
        Else decrease brightness/temperature accordingly
        """
        if self.error or self._line_index == self.gamma_idx:
            return
        elif self._line_index == self.brightness_idx:
            self.decrease_brightness()
        elif self._line_index == self.temperature_idx:
            self.decrease_temperature()
        else:
            self.reset_redshift() if self.is_enabled else self.run_redshift()
            self.is_enabled = not self.is_enabled
        self._set_text()

    @expose_command
    def right_click(self):
        """
        Has no action for the first line of the widget nor the gamma line.
        Increase brightness/temperature accordingly.
        """
        if self.error or self._line_index == 0 or self._line_index == self.gamma_idx:
            return
        elif self._line_index == self.brightness_idx:
            self.increase_brightness()
        elif self._line_index == self.temperature_idx:
            self.increase_temperature()
        self._set_text()

    def _scroll(self, step):
        """
        Scroll up/down dictated by 'step' the items
        and then display that item.

        Has no effect if the widget is disabled.
        """
        if self.error or not self.is_enabled:
            return
        self._line_index = (self._line_index + step) % len(self._lines)
        self.show_line()

    @expose_command
    def decrease_brightness(self):
        """
        Decrease brightness by a single step.
        """
        step = self.brightness_step * -1
        self._change_brightness(step)

    @expose_command
    def increase_brightness(self):
        """
        Increase brightness by a single step.
        """
        self._change_brightness(self.brightness_step)

    def _change_brightness(self, step):
        """
        Control the change brightness logic for both
        decreasing and increasing.
        """
        # To limit the text displayed from float calcs
        self.brightness = round(self.brightness + step, 2)

        # ensure that brightness stays in the valid bounds
        if self.brightness < self.brightness_lower_lim:
            self.brightness = self.brightness_lower_lim
        elif self.brightness > self.brightness_upper_lim:
            self.brightness = self.brightness_upper_lim

        self.run_redshift()

    @expose_command
    def decrease_temperature(self):
        """
        Decrease redshift temperature by a single step.
        """
        step = self.temperature_step * -1
        self._change_temperature(step)

    @expose_command
    def increase_temperature(self):
        """
        Increase redshift temperature by a single step.
        """
        self._change_temperature(self.temperature_step)

    def _change_temperature(self, step):
        """
        Control the change temperature logic for both
        decreasing and increasing.
        """
        # To limit the text displayed from float calcs
        self.temperature = round(self.temperature + step, 2)

        # ensure that temperature stays in the valid bounds
        if self.temperature < self.temperature_lower_lim:
            self.temperature = self.temperature_lower_lim
        elif self.temperature > self.temperature_upper_lim:
            self.temperature = self.temperature_upper_lim

        self.run_redshift()

    def _set_lines(self):
        """
        Set the list of formatted text items to scroll through.
        """
        first_text = ""
        if self.is_enabled:
            first_text = self.enabled_txt
        else:
            first_text = self.disabled_txt

        first_text = self._format_first_text(first_text)

        self._lines = [first_text, "", "", ""]
        self._lines[self.brightness_idx] = self._format_brightness_text()
        self._lines[self.temperature_idx] = self._format_temp_text()
        self._lines[self.gamma_idx] = self._format_gamma_text()

    def _set_text(self):
        """
        Update the lines array and the widget text.
        """
        # Update in case values have changed
        if self.error:
            return
        self._set_lines()
        text = ""
        if self._line_index == 0:
            if self.is_enabled:
                text = self._format_first_text(self.enabled_txt)
            else:
                text = self._format_first_text(self.disabled_txt)
        else:
            text = self._lines[self._line_index]
        self.update(text)

    def _format_temp_text(self) -> str:
        """
        Format the temperature text.
        """
        return self.temperature_fmt.format(temperature=self.temperature)

    def _format_brightness_text(self) -> str:
        """
        Format the brightness text.
        """
        return self.brightness_fmt.format(brightness=self.brightness)

    def _format_gamma_text(self) -> str:
        """
        Format the gamma text.
        """
        return self.gamma_val._format_gamma(self.gamma_fmt)

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

    def _assert_brightness(self):
        """
        assert that self.brightness is within
        the correct limits
        """
        assert (
            self.brightness >= self.brightness_lower_lim
            and self.brightness <= self.brightness_upper_lim
        ), (
            f"redshift: self.brightness is not initialised within the acceptable range, see the widget defaults docs: {self.brightness}"
        )

    def _assert_gamma(self) -> GammaGroup:
        """
        assert that self.gamma is within
        the correct limits. If it is, produce
        a GammaGroup instance
        """
        gamma_vals = [
            self.gamma_red,
            self.gamma_green,
            self.gamma_blue,
        ]
        gamma_group = GammaGroup(self.gamma_red, self.gamma_green, self.gamma_blue)
        for _, val in enumerate(gamma_vals):
            assert val >= self.gamma_lower_lim and val <= self.gamma_upper_lim, (
                f"redshift: self.gamma_red, self.gamma_green or self.gamma_blue have not been initialised within the acceptable range, see the docs: {gamma_group}"
            )

        return gamma_group

    def _assert_temperature(self):
        """
        assert that self.temperature is within
        the correct limits
        """
        assert (
            self.temperature >= self.temperature_lower_lim
            and self.temperature <= self.temperature_upper_lim
        ), (
            f"redshift: self.temperature is not initialised within the acceptable range, see the docs: {self.temperature}"
        )

    @expose_command
    def reset_redshift(self):
        """
        Call reset on redshift to reset to default settings.
        """
        try:
            subprocess.run([self.redshift_path, "-x"], check=True)
        except (TypeError, FileNotFoundError) as e:
            self.widget_error(
                f"redshift: could not find redshift executable, check redshift_path: {e}"
            )
        except subprocess.CalledProcessError as e:
            self.widget_error(f"redshift: could not enable redshift: {e}")

    @expose_command
    def run_redshift(self):
        """
        Run redshift command with defined parameters.
        """
        try:
            subprocess.run(
                [
                    self.redshift_path,
                    "-P",
                    "-O",
                    str(self.temperature),
                    "-b",
                    str(self.brightness),
                    "-g",
                    self.gamma_val._redshift_fmt(),
                ],
                check=True,
            )
        except (TypeError, FileNotFoundError) as e:
            self.widget_error(
                f"redshift: could not find redshift executable, check redshift_path: {e}"
            )
        except subprocess.CalledProcessError as e:
            self.widget_error(f"redshift: could not enable redshift: {e}")

    def widget_error(self, error_msg: str):
        """
        Cause the widget to display an error
        and log the given error message
        """
        self.error = error_msg
        logger.exception(self.error)
        self.update("Redshift widget crashed!")
