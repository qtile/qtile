# A qtile widget written to show active indication for mic or camera
# my github (https://github.com/desdemona2).
# maybe this is not well formatted as i am still a learner so feel free to modify this file.
# This feature is also included in iOS 14 and Android 12 and inspired from an app AccessDots for Android.

from libqtile.widget import base
import os


class active(base.ThreadPoolText):
    """widget to show indication if
    camera and mic are active in status bar"""

    defaults = [
        (
            "update_interval",
            1,
            "Update interval in seconds, if none, the "
            "widget updates whenever it's done'.",
        ),
        # ("fmt", "{mic_str} {cam_str}", "Display format for output"),
    ]

    def __init__(
        self, camDev="video0", sndDev="pcmC0D0c", camAct="📸", micAct="📢", **config
    ):
        super().__init__("", **config)
        self.add_defaults(active.defaults)

        self.camDev = camDev
        self.micDev = sndDev

        self.camAct = camAct
        self.micAct = micAct

    def poll(self):

        mic = os.system(f"fuser /dev/snd/{self.micDev}")
        camera = os.system(f"fuser /dev/{self.camDev}")

        mic_str = "" if mic == 256 else self.micAct
        cam_str = "" if camera == 256 else self.camAct

        return f"{mic_str}{cam_str}"
