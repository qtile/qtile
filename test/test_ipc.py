import os.path
import thread
import time
import socket
import Queue
import libpry
from libqtile import ipc as ipc


class TestServer(ipc.Server):
    last = None

    def __init__(self, fname):
        ipc.Server.__init__(self, fname, self.command)

    def command(self, data):
        self.last = data
        return "OK"


class uIPC(libpry.AutoTree):
    def send(self, fname, data, q):
        c = ipc.Client(fname)
        while 1:
            try:
                d = c.send(data)
            except socket.error:
                continue
            q.put(d)
            return

    def response(self, s, data):
        """
            Returns serverData, clientData
        """
        q = Queue.Queue()
        thread.start_new_thread(self.send, (s.fname, data, q))
        while 1:
            d = s.receive()
            if s.last:
                ret = s.last
                break
        s.last = None
        return ret, q.get()

    def test_basic(self):
        fname = os.path.join(self.tmpdir(), "testpath")
        server = TestServer(fname)
        assert self.response(server, "foo") == ("foo", "OK")

        expected = {
            "one": [1, 2, 3]
        }
        assert self.response(server, expected) == (expected, "OK")

    def test_big(self):
        fname = os.path.join(self.tmpdir(), "testpath")
        server = TestServer(fname)
        expected = {
            "one": [1, 2, 3] * 1024 * 5
        }
        assert self.response(server, expected) == (expected, "OK")

    def test_read_nodata(self):
        fname = os.path.join(self.tmpdir(), "testpath")
        s = TestServer(fname)
        assert s.receive() == None

    def test_close(self):
        fname = os.path.join(self.tmpdir(), "testpath")
        s = TestServer(fname)
        s.close()


tests = [
    # FIXME: Either add tests, or just remove this.
    #uIPC(),
]
