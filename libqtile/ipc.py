# Copyright (c) 2008, Aldo Cortesi. All rights reserved.
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

"""
    A simple IPC mechanism for communicating between two local processes. We
    use marshal to serialize data - this means that both client and server must
    run the same Python version, and that clients must be trusted (as
    un-marshalling untrusted data can result in arbitrary code execution).
"""
import marshal, select, os.path, socket

HDRLEN = 3
BUFSIZE = 1024 * 1024

class IPCError(Exception): pass


def multiord(x):
    """
        Like ord(), but takes multiple characters. I.e. calculate the
        base10 equivalent of a string considered as a set of base-256 digits.
    """
    num = 0
    scale = 1
    for i in range(len(x)-1, -1, -1):
        num = num + (ord(x[i])*scale)
        scale = scale*256
    return num


def multichar(a, width):
    """
        Like chr(), but takes a large integer that could fill many bytes,
        and returns a string. I.e. calculate the base256 equivalent string,
        from a given base10 integer.

        The return string will be padded to the left to ensure that it is of
        length "width".
    """
    a = int(a)
    chars = []
    while (a != 0):
        chars.insert(0, chr(a%256))
        a = a/256
    if len(chars) > width:
        raise ValueError, "Number too wide for width."
    ret = ["\0"]*(width-len(chars)) + chars
    return "".join(ret)


class _IPC:
    def _read(self, sock):
        size = multiord(sock.recv(HDRLEN))
        data = ""
        while len(data) < size:
            data += sock.recv(BUFSIZE)
        return marshal.loads(data)

    def _write(self, sock, msg):
        msg = marshal.dumps(msg)
        size = multichar(len(msg), HDRLEN)
        sock.sendall(size)
        sock.sendall(msg)


class Client(_IPC):
    def __init__(self, fname):
        self.fname = fname

    def send(self, msg):
        sock = socket.socket(
            socket.AF_UNIX,
            socket.SOCK_STREAM,
            0
        )
        try:
            sock.connect(self.fname)
        except socket.error:
            raise IPCError("Could not open %s"%self.fname)

        self._write(sock, msg)

        while 1:
            fds, _, _ = select.select([sock], [], [], 0)
            if fds:
                data = self._read(sock)
                sock.close()
                return data

    def call(self, data):
        return self.send(data)


class Server(_IPC):
    def __init__(self, fname, handler):
        self.fname, self.handler = fname, handler
        if os.path.exists(fname):
            os.unlink(fname)
        self.sock = socket.socket(
            socket.AF_UNIX,
            socket.SOCK_STREAM,
            0
        )
        self.sock.bind(self.fname)
        self.sock.listen(5)

    def close(self):
        self.sock.close()

    def receive(self):
        """
            Returns either None, or a single message.
        """
        fds, _, _ = select.select([self.sock], [], [], 0)
        if fds:
            conn, _ = self.sock.accept()
            try:
                data = self._read(conn)
            except socket.error:
                return
            try:
                ret = self.handler(data)
                self._write(conn, ret)
                conn.close()
            except socket.error:
                return
