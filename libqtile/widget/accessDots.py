# Copyright (c) 2021, Bhavuk Sharma
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

from libqtile.widget import base
import os


class active(base.ThreadPoolText):
    """
    This widget will show an indicator on satusbar if Camera or Microphone is being used by an application on
    your machine.
    This is similar like what is being offered in iOS 14 and Android 12, firefox also has a similar feature.
    WARNING: IF update_interval IS HIGH THAN IT WILL NOT BE ABLE TO DETECT IF CAMERA OR MIC IS BEING USED IN BETWEEN
    THAT INTERVAL, SO IT IS BETTER TO USE SMALL VALUE FOR update_interval (DEFAULT IS SET TO 1).
    """

    defaults = [
        (
            "update_interval",
            1,
            "Update interval in seconds, if none, the "
            "widget updates whenever it's done'.",
        ),
        ("format", "{mic_str} {cam_str}", "Display format for output"),
        ("cam_device", "/dev/video0", "Path to camera device"),
        ("mic_device", "/dev/snd/pcmC0D0c", "Path to Microphone device"),
        ("cam_active", "📸", "Indication when camera active"),
        ("cam_inactive", "", "Indication when camera is inactive"),
        ("mic_active", "📢", "Indication when Microphone active"),
        ("mic_inactive", "", "Indication when mic is inactive"),
    ]

    def __init__(self, **config):
        super().__init__("", **config)
        self.add_defaults(active.defaults)

    def poll(self):

        mic = os.system(f"fuser {self.mic_device}")
        camera = os.system(f"fuser {self.cam_device}")

        vals = dict(
            mic_str=self.mic_inactive if mic == 256 else self.mic_active,
            cam_str=self.cam_inactive if camera == 256 else self.cam_active,
        )
        return self.format.format(**vals)
