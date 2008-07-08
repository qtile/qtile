import subprocess, os, time
import Xlib.display
import libpry
import libqtile

DISPLAY = ":1"

class QTileTruss(libpry.TestContainer):
    def setUp(self):
        self.sub = subprocess.Popen(
                        ["Xnest", "-geometry", "800x600", DISPLAY, "-ac"],
                        stderr = subprocess.PIPE,
                        stdout = subprocess.PIPE
                    )
        # Try until XNest is up
        for i in range(20):
            try:
                d = Xlib.display.Display(DISPLAY)
                break
            except Xlib.error.DisplayConnectionError:
                time.sleep(0.1)
        d.close()

    def tearDown(self):
        os.kill(self.sub.pid, 9)


class uQTile(libpry.AutoTree):
    def test_init(self):
        q = libqtile.QTile(DISPLAY)


tests = [
    QTileTruss(), [
        uQTile()
    ]
]
