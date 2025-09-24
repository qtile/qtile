import datetime

from libqtile.widget.generic_poll_text import GenPollUrl


class IdleRPG(GenPollUrl):
    """
    A widget for monitoring and displaying IdleRPG stats.

    ::

        # display idlerpg stats for the player 'pants' on freenode's #idlerpg
        widget.IdleRPG(url="http://xethron.lolhosting.net/xml.php?player=pants")

    Widget requirements: xmltodict_.

    .. _xmltodict: https://pypi.org/project/xmltodict/
    """

    defaults = [
        ("format", "IdleRPG: {online} TTL: {ttl}", "Display format"),
    ]

    def __init__(self, **config):
        GenPollUrl.__init__(self, **config)
        self.add_defaults(IdleRPG.defaults)
        self.json = False
        self.xml = True

    def parse(self, body):
        formatted = {}
        for k, v in body["player"].items():
            if k == "ttl":
                formatted[k] = str(datetime.timedelta(seconds=int(v)))
            elif k == "online":
                formatted[k] = "online" if v == "1" else "offline"
            else:
                formatted[k] = v

        return self.format.format(**formatted)
