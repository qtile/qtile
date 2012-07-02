# -*- coding: utf-8 -*-

from .. import bar, manager
import base
from subprocess import check_output, call


class Canto(base._TextBox):
    defaults = manager.Defaults(
        ("font", "Arial", "Font"),
        ("fontsize", None, "Pixel size. Calculated if None."),
        ("padding", None, "Padding. Calculated if None."),
        ("background", "000000", "Background colour"),
        ("foreground", "ffffff", "Foreground colour"),
        ("fetch", False, "Whether to fetch new items on update"),
        ("feeds", [], "List of feeds to display, empty for all"),
        ("one_format", "{name}: {number}", "One feed display format"),
        ("all_format", "{number}", "All feeds display format"),
        ("update_delay", 600, "The delay in seconds between updates"),
    )

    def __init__(self, width=bar.CALCULATED, **config):
        base._TextBox.__init__(self, "N/A", width, **config)

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        self.timeout_add(self.update_delay, self.update)

    def _get_info(self):
        if not self.feeds:
            arg = "-a"
            if self.fetch:
                arg += "u"
            return self.all_format.format(
                number=check_output(["canto", arg])[:-1])
        else:
            if self.fetch:
                call(["canto", "-u"])
            return "".join([self.one_format.format(
                name=feed,
                number=check_output(["canto", "-n", feed])[:-1]
            ) for feed in self.feeds])

    def click(self, x, y, button):
        self.update()

    def update(self):
        ntext = self._get_info()
        if ntext != self.text:
            self.text = ntext
            self.bar.draw()
        return True
