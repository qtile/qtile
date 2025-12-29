from subprocess import call

from libqtile.widget import base

from libqtile.widget.generic_poll_text import GenPollCommand

from libqtile.log_utils import logger


class Canto(GenPollCommand):
    """Display RSS feeds updates using the canto remote

    Widget requirements: canto_

    .. _canto: https://codezen.org/canto-ng/
    """

    defaults = [
        ("tags", [], "List of tags to display, empty for all"),
        ("one_format", "{name}: {number}", "One tag display format"),
        ("all_format", "{number}", "All tags display format"),
    ]

    def __init__(self, **config):
        config["cmd"] = ["canto-remote", "status", "--tags"]
        GenPollCommand.__init__(self, **config)
        self.add_defaults(Canto.defaults)

    def get_info(self, output):
        output = output.splitlines()
        if not self.tags:
            total_items = 0
            for line in output:
                if "maintag:" in line:
                    current_tag_items = line[line.index(":", line.index(":") + 1) + 2 :]
                    total_items += int(current_tag_items)
            return total_items
        else:
            all_tags_output = {}
            for line in output:
                second_colon_index = line.index(":", line.index(":") + 1)
                current_tag_name = line[:second_colon_index].strip()
                if current_tag_name in self.tags:
                    current_tag_items = line[second_colon_index + 2 :].strip()
                    all_tags_output.update({current_tag_name: current_tag_items})
            return all_tags_output

    def parse(self, output):
        output = self.get_info(output)
        if not self.tags:
            display = self.all_format.format(number=output)
            return display
        else:
            if not output:
                logger.debug("Canto remote found no tags")
                return ""
            display = []
            for key in output:
                current_tag_output = self.one_format.format(name=key, number=output[key])
                display.append(current_tag_output)
            return "".join(display)
