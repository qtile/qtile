"""
    A simple IPC mechanism for communicating between two local processes. We
    use marshal to serialize data - this means that both client and server must
    run the same Python version, and that clients must be trusted (as
    un-marshalling untrusted data can result in arbitrary code execution).
"""
import marshal, socket, select, os.path

BUFSIZE = 1024 * 1024

class Client:
    def __init__(self, fname):
        self.fname = fname

    def send(self, msg):
        sock = socket.socket(
            socket.AF_UNIX,
            socket.SOCK_STREAM,
            0
        )
        sock.connect(self.fname)
        data = marshal.dumps(msg)
        sock.sendall(data)
        while 1:
            fds, _, _ = select.select([sock], [], [], 0)
            if fds:
                data, _ = sock.recvfrom(BUFSIZE)
                sock.close()
                return marshal.loads(data)

    def call(self, func, *args, **kwargs):
        return self.send((func, args, kwargs))


class Server:
    def __init__(self, fname, handler):
        self.fname, self.handler = fname, handler
        self.sock = socket.socket(
            socket.AF_UNIX,
            socket.SOCK_STREAM,
            0
        )
        self.sock.bind(self.fname)
        self.sock.listen(5)

    def receive(self):
        """
            Returns either None, or a single message.
        """
        fds, _, _ = select.select([self.sock], [], [], 0)
        if fds:
            conn, _ = self.sock.accept()
            try:
                data, _ = conn.recvfrom(BUFSIZE)
            except socket.error:
                return
            ret = self.handler(marshal.loads(data))
            conn.sendall(marshal.dumps(ret))
            conn.close()
