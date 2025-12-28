from subprocess import call

from libqtile.widget import base


class Canto(base.BackgroundPoll):
    """Display RSS tags updates using the canto console reader

    Widget requirements: canto_

    .. _canto: https://codezen.org/canto-ng/
    """

    defaults = [
        ("fetch", False, "Whether to fetch new items on update"),
        ("tags", [], "List of tags to display, empty for all"),
        ("one_format", "{name}: {number}", "One feed display format"),
        ("all_format", "{number}", "All feeds display format"),
    ]

    def __init__(self, **config):
        base.BackgroundPoll.__init__(self, "", **config)
        self.add_defaults(Canto.defaults)

    def poll(self):
        if self.fetch:
            call(["canto-remote", "force-update"])
        if not self.tags:
            output = self.all_format.format(number=self.call_process(["canto-remote", "status"]))
            return output
        else:
            return "".join(
                [
                    self.one_format.format(
                        name=tag,
                        number=self.call_process(["canto-remote", "status", "--tag", tag])[:-1],
                    )
                    for tag in self.tags
                ]
            )
