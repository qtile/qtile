# A qtile widget written to show active indication for mic or camera
# written by bhauvk sharma (https://github.com/desdemona2)

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
            "widget updates whenever it's done'."
            ),
    ]


    def __init__(self, **config):
        super().__init__("", **config)
        self.add_defaults(active.defaults)


    def poll(self):
        camera = os.system("fuser /dev/video0")
        mic = os.system("fuser /dev/snd/pcmC0D0c")
    
        def mictest():
            if mic == 256:
                return ""
            else:
                return "📢"
        
        def camtest():
            if camera == 256:
                return ""
            else:
                return "📸"

        return f"{mictest()} {camtest()}"
