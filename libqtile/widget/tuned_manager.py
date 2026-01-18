import re
import subprocess

from libqtile import bar
from libqtile.widget import base


class TunedManager(base.BackgroundPoll):
    """
    A widget to interact with the Tuned power management daemon.
    It always displays the name of the currently active profile.

    The user can define a list of profiles to be used, 3 default
    profiles exist. These 3 are the default profiles on RHEL and
    Fedora Linux.

    A left click on the widget will go to the next layout in the
    list, a right click will go to the previous one.  If the end
    of the list is reached, it cycles back to the beginning.
    Scrolling can also be used to cycle through the list, though
    keep in mind that switching the profile takes a while and so
    scrolling through the list quickly is not feasible.
    """

    orientations = base.ORIENTATION_HORIZONTAL

    defaults = [
        (
            "modes",
            ["powersave", "balanced-battery", "throughput-performance"],
            "The modes to cycle through",
        )
    ]

    def __init__(self, **config):
        base.BackgroundPoll.__init__(self, "", **config)
        self.add_defaults(TunedManager.defaults)
        self.length_type = bar.CALCULATED
        self.regex = re.compile(r"Current active profile:\s+(\S+)")
        self.current_mode = self.find_mode()

        self.add_callbacks(
            {
                "Button1": self.next_mode,  # Left Click
                "Button3": self.previous_mode,  # Right Click
                "Button4": self.next_mode,  # Scroll up
                "Button5": self.previous_mode,  # Scroll down
            }
        )

    def _configure(self, qtile, bar):
        base.BackgroundPoll._configure(self, qtile, bar)
        self.text = self.find_mode()

    def poll(self):
        return self.find_mode()

    def find_mode(self):
        result = subprocess.run("tuned-adm active", shell=True, capture_output=True, text=True)
        output = result.stdout
        mode = self.regex.findall(output)
        if not mode:
            return ""
        return mode[0]

    def update_bar(self):
        self.current_mode = self.find_mode()
        self.text = self.current_mode
        self.bar.draw()

    def execute_command(self, index: int):
        argument = self.modes[index]  # pyright: ignore
        try:
            subprocess.run(["tuned-adm", "profile", argument], check=True)
            self.update_bar()
        except subprocess.CalledProcessError as e:
            self.update(f"Error setting mode: {e}")

    def _change_mode(self, step=1):
        next_index: int = (self.modes.index(self.current_mode) + step) % len(self.modes)  # pyright: ignore
        self.execute_command(next_index)

    def next_mode(self):
        self._change_mode()

    def previous_mode(self):
        self._change_mode(step=-1)
