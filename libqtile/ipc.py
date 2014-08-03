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
import marshal
import select
import logging
import os.path
import socket
import struct
import errno
import fcntl

from six.moves import gobject

HDRLEN = 4
BUFSIZE = 1024 * 1024


class IPCError(Exception):
    pass


class _IPC:
    def _read(self, sock):
        try:
            size = struct.unpack("!L", sock.recv(HDRLEN))[0]
            data = "".encode()
            while len(data) < size:
                data += sock.recv(BUFSIZE)
            return self._unpack_body(data)
        except struct.error:
            raise IPCError(
                "error reading reply!"
                " (probably the socket was disconnected)"
            )

    def _unpack_body(self, body):
        return marshal.loads(body)

    def _pack_reply(self, msg):
        msg = marshal.dumps(msg)
        size = struct.pack("!L", len(msg))
        return size + msg

    def _write(self, sock, msg):
        sock.sendall(self._pack_reply(msg))


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
            raise IPCError("Could not open %s" % self.fname)

        self._write(sock, msg)

        while True:
            fds, _, _ = select.select([sock], [], [], 1)
            if fds:
                data = self._read(sock)
                sock.close()
                return data
            else:
                raise RuntimeError("Server not responding")

    def call(self, data):
        return self.send(data)


class Server(_IPC):
    def __init__(self, fname, handler):
        self.log = logging.getLogger('qtile')
        self.fname = fname
        self.handler = handler
        if os.path.exists(fname):
            os.unlink(fname)
        self.sock = socket.socket(
            socket.AF_UNIX,
            socket.SOCK_STREAM,
            0
        )
        flags = fcntl.fcntl(self.sock, fcntl.F_GETFD)
        fcntl.fcntl(self.sock, fcntl.F_SETFD, flags | fcntl.FD_CLOEXEC)
        self.sock.bind(self.fname)
        self.sock.listen(5)

    def close(self):
        self.log.info('Remove source on server close')
        gobject.source_remove(self.gob_tag)
        self.sock.close()

    def start(self):
        self.log.info('Add io watch on server start')
        self.gob_tag = gobject.io_add_watch(
            self.sock, gobject.IO_IN, self._connection
        )

    def _connection(self, sock, cond):
        try:
            conn, _ = self.sock.accept()
        except socket.error as er:
            if er.errno in (errno.EAGAIN, errno.EINTR):
                return True
            raise
        else:
            flags = fcntl.fcntl(conn, fcntl.F_GETFD)
            fcntl.fcntl(conn, fcntl.F_SETFD, flags | fcntl.FD_CLOEXEC)
            conn.setblocking(0)
            data = {'buffer': ''.encode()}  # object which holds connection state
            self.log.info('Add io watch on _connection')
            gobject.io_add_watch(conn, gobject.IO_IN, self._receive, data)
            return True

    def _receive(self, conn, cond, data):
        try:
            recv = conn.recv(4096)
        except socket.error as er:
            if er.errno in (errno.EAGAIN, errno.EINTR):
                return True
            raise
        else:
            if recv == '':
                self.log.info('Remove source on receive')
                gobject.source_remove(data['tag'])
                conn.close()
                return True

            data['buffer'] += recv
            if 'header' not in data and len(data['buffer']) >= HDRLEN:
                data['header'] = struct.unpack("!L", data['buffer'][:HDRLEN])
                data['buffer'] = data['buffer'][HDRLEN:]
            if 'header' in data:
                if len(data['buffer']) < data['header'][0]:
                    return True

            req = self._unpack_body(data['buffer'])
            data['result'] = self._pack_reply(self.handler(req))
            self.log.info('Add io watch on receive')
            gobject.io_add_watch(conn, gobject.IO_OUT, self._send, data)
            return False

    def _send(self, conn, cond, data):
        try:
            bytes = conn.send(data['result'])
        except socket.error as er:
            if er.errno in (errno.EAGAIN, errno.EINTR, errno.EPIPE):
                return True
            raise
        else:
            if not bytes or bytes >= len(data['result']):
                conn.close()
                return False

            data['result'] = data['result'][bytes:]
            return True
