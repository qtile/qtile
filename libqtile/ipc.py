"""
    A simple IPC mechanism for communicating between two local processes. We
    use marshal to serialize data - this means that both client and server must
    run the same Python version, and that clients must be trusted (as
    un-marshalling untrusted data can result in arbitrary code execution).
"""
import marshal, socket, select

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
        sock.close()


class Server:
    def __init__(self, fname):
        self.fname = fname
        self.sock = socket.socket(
            socket.AF_UNIX,
            socket.SOCK_STREAM,
            0
        )
        self.sock.setblocking(0)
        self.sock.bind(self.fname)
        self.sock.listen(5)

    def receive(self):
        """
            Returns either None, or a single message.
        """
        fds, _, _ = select.select([self.sock], [], [], 0)
        if fds:
            conn, _ = self.sock.accept()
            data, _ = conn.recvfrom(BUFSIZE)
            conn.close()
            return marshal.loads(data)
        else:
            return None
