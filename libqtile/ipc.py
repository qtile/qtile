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
import asyncio
import fcntl
import json
import marshal
import os.path
import socket
import struct
from typing import Any, Callable, Optional, Tuple, cast

from libqtile.log_utils import logger
from libqtile.utils import get_cache_dir

HDRLEN = 4

SOCKBASE = "qtilesocket.%s"


def find_sockfile(display: str = None):
    """Finds the appropriate socket file for the given display"""
    display = display or os.environ.get('DISPLAY') or ':0.0'
    if '.' not in display:
        display += '.0'
    cache_directory = get_cache_dir()
    return os.path.join(cache_directory, SOCKBASE % display)


class IPCError(Exception):
    pass


class _IPC:
    """A helper class to handle properly packing and unpacking messages"""

    @classmethod
    def unpack(cls, data: Optional[bytes]) -> Tuple[Any, bool]:
        """Unpack the incoming message

        Parameters
        ----------
        data : Optional[bytes]
            The incoming message to unpack, if None, an IPCError is raised.

        Returns
        -------
        Tuple[Any, bool]
            A tuple of the unpacked object and a boolean denoting if the
            message was deserialized using json.  If True, the return message
            should be packed as json.
        """
        if data is None:
            raise IPCError("received data is None")
        try:
            return json.loads(data.decode("utf-8")), True
        except ValueError:
            pass

        try:
            assert len(data) >= HDRLEN
            size = struct.unpack("!L", data[:HDRLEN])[0]
            assert size >= len(data[HDRLEN:])
            return cls._unpack_body(data[HDRLEN:HDRLEN + size]), False
        except AssertionError:
            raise IPCError(
                "error reading reply!"
                " (probably the socket was disconnected)"
            )

    @staticmethod
    def pack_json(msg: Any) -> bytes:
        json_obj = json.dumps(msg)
        return json_obj.encode('utf-8')

    @staticmethod
    def pack(msg: Any) -> bytes:
        msg_bytes = marshal.dumps(msg)
        size = struct.pack("!L", len(msg_bytes))
        return size + msg_bytes

    @staticmethod
    def _unpack_body(body: bytes) -> Any:
        # mashal seems incorrectly annotated to take and return str
        return marshal.loads(body)


class _ClientProtocol(asyncio.Protocol):
    """IPC Client Protocol

    1. Once the connection is made, the client initializes a Future self.reply,
    which will hold the response from the server.

    2. The message is sent to the server with .send(msg), which closes the
    connection once the message is sent.

    3. The client then receives data from the server until the server closes
    the connection, signalling that all the data has been sent.

    4. When the server sends on EOF, the data is unpacked and stored to the
    reply future.
    """
    def __init__(self) -> None:
        self.transport = None  # type: Optional[asyncio.WriteTransport]
        self.recv = None  # type: Optional[bytes]
        self.reply = None  # type: Optional[asyncio.Future]

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        assert isinstance(transport, asyncio.WriteTransport)
        self.transport = transport
        self.recv = b''
        self.reply = asyncio.Future()

    def send(self, msg: Any, is_json=False) -> None:
        assert self.transport is not None

        if is_json:
            send_data = _IPC.pack_json(msg)
        else:
            send_data = _IPC.pack(msg)

        self.transport.write(send_data)

        try:
            self.transport.write_eof()
        except AttributeError:
            logger.exception('Swallowing AttributeError due to asyncio bug!')

    def data_received(self, data: bytes) -> None:
        assert self.recv is not None
        self.recv += data

    def eof_received(self) -> None:
        assert self.reply is not None

        # The server sends EOF when there is data ready to be processed
        try:
            data, _ = _IPC.unpack(self.recv)
        except IPCError as e:
            self.reply.set_exception(e)
        else:
            self.reply.set_result(data)

    def connection_lost(self, exc) -> None:
        assert self.reply is not None

        # The client shouldn't just lose the connection without an EOF
        if exc:
            self.reply.set_exception(exc)

        if not self.reply.done():
            self.reply.set_exception(IPCError)


class Client:
    def __init__(self, fname: str, is_json=False) -> None:
        """Create a new IPC client

        Parameters
        ----------
        fname : str
            The file path to the file that is used to open the connection to
            the running IPC server.
        is_json : bool
            Pack and unpack messages as json
        """
        self.fname = fname
        self.loop = asyncio.get_event_loop()
        self.is_json = is_json

    def send(self, msg: Any) -> Any:
        """Send the message and return the response from the server

        If any exception is raised by the server, that will propogate out of
        this call.

        Parameters
        ----------
        """
        client_coroutine = self.loop.create_unix_connection(_ClientProtocol, path=self.fname)

        try:
            _, client_proto = self.loop.run_until_complete(client_coroutine)
        except OSError:
            raise IPCError("Could not open %s" % self.fname)

        client_proto = cast(_ClientProtocol, client_proto)
        client_proto.send(msg, is_json=self.is_json)
        assert client_proto.reply is not None

        try:
            self.loop.run_until_complete(asyncio.wait_for(client_proto.reply, timeout=10))
        except asyncio.TimeoutError:
            raise RuntimeError("Server not responding")

        return client_proto.reply.result()

    def call(self, data: Any) -> Any:
        return self.send(data)


class _ServerProtocol(asyncio.Protocol):
    """IPC Server Protocol

    1. The server is initialized with a handler callback function for evaluating
    incoming queries.

    2. Once the connection is made, the server initializes a data store for
    incoming data.

    3. The client sends all its data to the server, which is stored.

    4. The client signals that all data is sent by sending an EOF, at which
    point the server then unpacks the data and runs it through the handler.
    The result is returned to the client and the connection is closed.
    """
    def __init__(self, handler: Callable) -> None:
        super().__init__()

        self.handler = handler
        self.transport = None  # type: Optional[asyncio.WriteTransport]
        self.data = None  # type: Optional[bytes]

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        assert isinstance(transport, asyncio.WriteTransport)
        self.transport = transport
        logger.debug('Connection made to server')
        self.data = b''

    def data_received(self, recv: bytes) -> None:
        logger.debug('Data received by server')
        assert self.data is not None
        self.data += recv

    def eof_received(self) -> None:
        assert self.transport is not None
        logger.debug('EOF received by server')
        try:
            req, is_json = _IPC.unpack(self.data)
        except IPCError:
            logger.warn('Invalid data received, closing connection')
            self.transport.close()
            return
        finally:
            self.data = None

        if req[1] == 'restart':
            logger.debug('Closing connection on restart')
            self.transport.write_eof()

        rep = self.handler(req)

        if is_json:
            result = _IPC.pack_json(rep)
        else:
            result = _IPC.pack(rep)

        logger.debug('Sending result on receive EOF')
        self.transport.write(result)
        logger.debug('Closing connection on receive EOF')
        self.transport.write_eof()

        self.data = None
        self.transport = None


class Server:
    def __init__(self, fname: str, handler, loop) -> None:
        self.fname = fname
        self.handler = handler
        self.loop = loop
        self.server = None  # type: Optional[asyncio.BaseTransport]

        if os.path.exists(fname):
            os.unlink(fname)

        self.sock = socket.socket(
            socket.AF_UNIX,
            socket.SOCK_STREAM,
            0
        )
        flags = fcntl.fcntl(self.sock.fileno(), fcntl.F_GETFD)
        fcntl.fcntl(self.sock.fileno(), fcntl.F_SETFD, flags | fcntl.FD_CLOEXEC)
        self.sock.bind(self.fname)

    def __enter__(self) -> "Server":
        """Start and return the server"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, tb) -> None:
        """Close and shutdown the server"""
        self.close()

    def start(self) -> None:
        """Start the server"""
        assert self.server is None
        server_coroutine = self.loop.create_unix_server(lambda: _ServerProtocol(self.handler), sock=self.sock)

        logger.debug('Starting server')
        self.server = self.loop.run_until_complete(server_coroutine)

    def close(self) -> None:
        """Close and shutdown the server"""
        logger.debug('Stopping server on server close')
        assert self.server is not None
        self.server.close()
        self.sock.close()
