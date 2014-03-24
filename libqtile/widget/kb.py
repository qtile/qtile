import subprocess
from gi.repository import Xkl, Gdk, GdkX11


class KeyBoard():

    def __init__(self):
        display = GdkX11.x11_get_default_xdisplay()
        self.engine = Xkl.Engine.get_instance(display)

    def get_cur_layout(self):
        t = subprocess.check_output(["xset", "-q"])
        num = int(t.splitlines()[1].split()[9][4])
        groups = self.engine.get_groups_names()
        if (len(groups) > num):
            result = str(groups[int(num)])[:2]
        else:
            result = "Err"
        return result

k = KeyBoard()
print(k.get_cur_layout())
