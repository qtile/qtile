from libqtile.utils import acall_process
from libqtile.widget import base


class GenPollText(base.BackgroundPoll):
    """A generic text widget that polls using poll function to get the text

    Widget requirements: aiohttp_.

    .. _aiohttp: https://pypi.org/project/aiohttp/
    """

    defaults = [
        ("func", None, "Poll Function"),
    ]

    def __init__(self, **config):
        base.BackgroundPoll.__init__(self, "", **config)
        self.add_defaults(GenPollText.defaults)

    def poll(self):
        if not self.func:
            return "You need a poll function"
        return self.func()


class GenPollCommand(base.BackgroundPoll):
    """A generic text widget to display output from scripts or shell commands"""

    defaults = [
        ("update_interval", 60, "update time in seconds"),
        ("cmd", None, "command line as a string or list of arguments to execute"),
        ("shell", False, "run command through shell to enable piping and shell expansion"),
        ("parse", None, "Function to parse output of command"),
    ]

    def __init__(self, **config):
        base.BackgroundPoll.__init__(self, "", **config)
        self.add_defaults(GenPollCommand.defaults)

    def _configure(self, qtile, bar):
        base.BackgroundPoll._configure(self, qtile, bar)
        self.add_callbacks({"Button1": self.force_update})

    async def apoll(self):
        out = await acall_process(self.cmd, self.shell)
        if self.parse:
            return self.parse(out)

        return out.strip()
