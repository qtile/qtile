import subprocess, os, time
import Xlib.display
import libpry
import libqtile

DISPLAY = ":1"

class QTileTruss(libpry.TmpDirMixin, libpry.TestContainer):
    """
        This class starts up Xnest, and then fires up a QTile instance on it.
    """
    def setUp(self):
        libpry.TmpDirMixin.setUp(self)
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
        self["fname"] = os.path.join(self["tmpdir"], "qtilesocket")
        pid = os.fork()
        if pid == 0:
            q = libqtile.QTile(DISPLAY, self["fname"])
            q.loop()
        else:
            self.qtilepid = pid
            time.sleep(0.1)

    def tearDown(self):
        os.kill(self.qtilepid, 9)
        os.kill(self.sub.pid, 9)


class uQTile(libpry.AutoTree):
    def test_events(self):
        c = libqtile.ipc.Client(self["fname"])
        print c.send(("qtile.status", {}))


tests = [
    QTileTruss(), [
        uQTile()
    ]
]
