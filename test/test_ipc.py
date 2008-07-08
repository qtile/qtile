import os.path
import libpry
from libqtile import ipc as ipc


class uIPC(libpry.TmpDirMixin, libpry.AutoTree):
    def test_basic(self):
        fname = os.path.join(self["tmpdir"], "testpath")
        s = ipc.Server(fname)
        c = ipc.Client(fname)

        c.send("foo")
        assert s.receive() == "foo"

        c.send("bar")
        c.send("voing")
        assert s.receive() == "bar"
        assert s.receive() == "voing"

        expected = {
            "one": [1, 2, 3]
        }
        c.send(expected)
        assert s.receive() == expected

        expected = {
            "one": [1, 2, 3]*10
        }
        c.send(expected)
        assert s.receive() == expected

    def test_read_nodata(self):
        fname = os.path.join(self["tmpdir"], "testpath")
        s = ipc.Server(fname)
        assert s.receive() == None


tests = [
    uIPC()
]
