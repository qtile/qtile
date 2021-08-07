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
# modification suggested by elParaguayo (https://github.com/elParaguayo)
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
        ("camDev", "/dev/video0", "Path to camera device"),
        ("micDev", "/dev/snd/pcmC0D0c", "Path to Microphone device"),
        ("camAct", "📸", "Indication when camera active"),
        ("micAct", "📢", "Indication when Microphone active"),
    ]

    def __init__(self, **config):
        super().__init__("", **config)
        self.add_defaults(active.defaults)

    def poll(self):

        mic = os.system(f"fuser {self.micDev}")
        camera = os.system(f"fuser {self.camDev}")

        mic_str = "" if mic == 256 else self.micAct
        cam_str = "" if camera == 256 else self.camAct
        return f"{mic_str} {cam_str}"
