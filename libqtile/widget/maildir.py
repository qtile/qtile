from __future__ import annotations

import mailbox
import os.path

from libqtile.widget import base


class Maildir(base.BackgroundPoll):
    """A simple widget showing the number of new mails in maildir mailboxes"""

    defaults = [
        ("maildir_path", "~/Mail", "path to the Maildir folder"),
        (
            "sub_folders",
            [{"path": "INBOX", "label": "Home mail"}, {"path": "spam", "label": "Home junk"}],
            "List of subfolders to scan. Each subfolder is a dict of `path` and `label`.",
        ),
        ("separator", " ", "the string to put between the subfolder strings."),
        (
            "total",
            False,
            "Whether or not to sum subfolders into a grand \
            total. The first label will be used.",
        ),
        (
            "hide_when_empty",
            False,
            "Whether not to display anything if the subfolder has no new mail",
        ),
        ("empty_color", None, "Display color when no new mail is available"),
        ("nonempty_color", None, "Display color when new mail is available"),
        ("subfolder_fmt", "{label}: {value}", "Display format for one subfolder"),
    ]

    def __init__(self, **config):
        base.BackgroundPoll.__init__(self, "", **config)
        self.add_defaults(Maildir.defaults)

        # if it looks like a list of strings then we just convert them
        # and use the name as the label
        if isinstance(self.sub_folders[0], str):
            self.sub_folders = [{"path": folder, "label": folder} for folder in self.sub_folders]

    def poll(self):
        """Scans the mailbox for new messages

        Returns
        =======
        A string representing the current mailbox state
        """
        state = {}

        def to_maildir_fmt(paths):
            for path in iter(paths):
                yield path.rsplit(":")[0]

        for sub_folder in self.sub_folders:
            path = os.path.join(os.path.expanduser(self.maildir_path), sub_folder["path"])
            maildir = mailbox.Maildir(path)
            state[sub_folder["label"]] = 0

            for file in to_maildir_fmt(os.listdir(os.path.join(path, "new"))):
                if file in maildir:
                    state[sub_folder["label"]] += 1

        return self.format_text(state)

    def _format_one(self, label: str, value: int) -> str:
        if value == 0 and self.hide_when_empty:
            return ""

        s = self.subfolder_fmt.format(label=label, value=value)
        color = self.empty_color if value == 0 else self.nonempty_color

        if color is None:  # default to self.foreground
            return s

        return s.join((f'<span foreground="{color}">', "</span>"))

    def format_text(self, state: dict[str, int]) -> str:
        """Converts the state of the subfolders to a string

        Parameters
        ==========
        state: dict[str, int]
            a dictionary mapping subfolder labels to new mail values

        Returns
        =======
        a string representation of the given state
        """
        if self.total:
            return self._format_one(self.sub_folders[0]["label"], sum(state.values()))
        else:
            return self.separator.join(self._format_one(*item) for item in state.items())
