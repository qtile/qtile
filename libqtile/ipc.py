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
import logging
import os.path
import socket
import struct
import fcntl

from six.moves import asyncio

HDRLEN = 4


class IPCError(Exception):
    pass


class _IPC(object):
    def _unpack(self, data):
        try:
            assert len(data) >= HDRLEN
            size = struct.unpack("!L", data[:HDRLEN])[0]
            assert size >= len(data[HDRLEN:])
            return self._unpack_body(data[HDRLEN:HDRLEN + size])
        except AssertionError:
            raise IPCError(
                "error reading reply!"
                " (probably the socket was disconnected)"
            )

    def _unpack_body(self, body):
        return marshal.loads(body)

    def _pack(self, msg):
        msg = marshal.dumps(msg)
        size = struct.pack("!L", len(msg))
        return size + msg


class _ClientProtocol(asyncio.Protocol, _IPC):
    """IPC Client Protocol

    1. Once the connection is made, the client initializes a Future self.reply,
    which will hold the response from the server.

    2. The message is sent to the server with .send(msg), which closes the
    connection once the message is sent.

    3. The client then recieves data from the server until the server closes
    the connection, signalling that all the data has been sent.

    4. When the server sends on EOF, the data is unpacked and stored to the
    reply future.
    """
    def connection_made(self, transport):
        self.transport = transport
        self.recv = b''
        self.reply = asyncio.Future()

    def send(self, msg):
        self.transport.write(self._pack(msg))
        try:
            self.transport.write_eof()
        except AttributeError:
            log = logging.getLogger('qtile')
            log.exception('Swallowing AttributeError due to asyncio bug!')

    def data_received(self, data):
        self.recv += data

    def eof_received(self):
        # The server sends EOF when there is data ready to be processed
        try:
            data = self._unpack(self.recv)
        except IPCError as e:
            self.reply.set_exception(e)
        else:
            self.reply.set_result(data)

    def connection_lost(self, exc):
        # The client shouldn't just lose the connection without an EOF
        if exc:
            self.reply.set_exception(exc)
        if not self.reply.done():
            self.reply.set_exception(IPCError)


class Client(object):
    def __init__(self, fname):
        self.fname = fname
        self.loop = asyncio.get_event_loop()

    def send(self, msg):
        client_coroutine = self.loop.create_unix_connection(_ClientProtocol, path=self.fname)

        try:

            _, client_proto = self.loop.run_until_complete(client_coroutine)
        except OSError:
            raise IPCError("Could not open %s" % self.fname)

        client_proto.send(msg)

        try:
            self.loop.run_until_complete(asyncio.wait_for(client_proto.reply, timeout=10))
        except asyncio.TimeoutError:
            raise RuntimeError("Server not responding")

        return client_proto.reply.result()

    def call(self, data):
        return self.send(data)


class _ServerProtocol(asyncio.Protocol, _IPC):
    """IPC Server Protocol

    1. The server is initalized with a handler callback function for evaluating
    incoming queries and a log.

    2. Once the connection is made, the server initializes a data store for
    incoming data.

    3. The client sends all its data to the server, which is stored.

    4. The client signals that all data is sent by sending an EOF, at which
    point the server then unpacks the data and runs it through the handler.
    The result is returned to the client and the connection is closed.
    """
    def __init__(self, handler, log):
        asyncio.Protocol.__init__(self)
        self.handler = handler
        self.log = log

    def connection_made(self, transport):
        self.transport = transport
        self.log.info('Connection made to server')
        self.data = b''

    def data_received(self, recv):
        self.log.info('Data recieved by server')
        self.data += recv

    def eof_received(self):
        self.log.info('EOF recieved by server')
        try:
            req = self._unpack(self.data)
        except IPCError:
            self.log.info('Invalid data received, closing connection')
            self.transport.close()
            return
        finally:
            self.data = None

        if req[1] == 'restart':
            self.log.info('Closing connection on restart')
            self.transport.write_eof()

        rep = self.handler(req)
        result = self._pack(rep)
        self.log.info('Sending result on receive EOF')
        self.transport.write(result)
        self.log.info('Closing connection on receive EOF')
        self.transport.write_eof()


class Server(object):
    def __init__(self, fname, handler, loop):
        self.log = logging.getLogger('qtile')
        self.fname = fname
        self.handler = handler
        self.loop = loop

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

    def close(self):
        self.log.info('Stopping server on server close')
        self.server.close()
        self.sock.close()

    def start(self):
        serverprotocol = _ServerProtocol(self.handler, self.log)
        server_coroutine = self.loop.create_unix_server(lambda: serverprotocol, sock=self.sock, backlog=5)

        self.log.info('Starting server')
        self.server = self.loop.run_until_complete(server_coroutine)
