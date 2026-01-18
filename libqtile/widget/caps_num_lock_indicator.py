import re

from libqtile.widget.generic_poll_text import GenPollCommand


class CapsNumLockIndicator(GenPollCommand):
    """Really simple widget to show the current Caps/Num Lock state."""

    defaults = [("update_interval", 0.5, "Update Time in seconds.")]

    def __init__(self, **config):
        config["cmd"] = ["xset", "q"]
        GenPollCommand.__init__(self, **config)
        self.add_defaults(CapsNumLockIndicator.defaults)

    def parse(self, raw: str):
        if raw.startswith("Keyboard"):
            indicators = re.findall(r"(Caps|Num)\s+Lock:\s*(\w*)", raw)
            return " ".join([" ".join(indicator) for indicator in indicators])
        return ""
