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
import sys
from typing import Any, Optional, Tuple

from libqtile.log_utils import logger
from libqtile.utils import get_cache_dir

HDRFORMAT = "!L"
HDRLEN = struct.calcsize(HDRFORMAT)

SOCKBASE = "qtilesocket.%s"


def find_sockfile(display: str = None):
    """Finds the appropriate socket file for the given display"""
    display = display or os.environ.get("DISPLAY") or ":0.0"
    if "." not in display:
        display += ".0"
    cache_directory = get_cache_dir()
    return os.path.join(cache_directory, SOCKBASE % display)


class IPCError(Exception):
    pass


class _IPC:
    """A helper class to handle properly packing and unpacking messages"""

    @staticmethod
    def unpack(data: bytes, *, is_json: Optional[bool] = None) -> Tuple[Any, bool]:
        """Unpack the incoming message

        Parameters
        ----------
        data : bytes
            The incoming message to unpack
        is_json : Optional[bool]
            If the message should be unpacked as json.  By default, try to
            unpack json and fallback gracefully to marshalled bytes.

        Returns
        -------
        Tuple[Any, bool]
            A tuple of the unpacked object and a boolean denoting if the
            message was deserialized using json.  If True, the return message
            should be packed as json.
        """
        if is_json is None or is_json:
            try:
                return json.loads(data.decode()), True
            except ValueError as e:
                if is_json:
                    raise IPCError("Unable to decode json data") from e

        try:
            assert len(data) >= HDRLEN
            size = struct.unpack(HDRFORMAT, data[:HDRLEN])[0]
            assert size >= len(data[HDRLEN:])
            return marshal.loads(data[HDRLEN:HDRLEN + size]), False
        except AssertionError as e:
            raise IPCError(
                "error reading reply! (probably the socket was disconnected)"
            ) from e

    @staticmethod
    def pack(msg: Any, *, is_json: bool = False) -> bytes:
        """Pack the object into a message to pass"""
        if is_json:
            json_obj = json.dumps(msg)
            return json_obj.encode()

        msg_bytes = marshal.dumps(msg)
        size = struct.pack(HDRFORMAT, len(msg_bytes))
        return size + msg_bytes


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

    def call(self, data: Any) -> Any:
        return self.send(data)

    def send(self, msg: Any) -> Any:
        """Send the message and return the response from the server

        If any exception is raised by the server, that will propogate out of
        this call.
        """
        return self.loop.run_until_complete(self.async_send(msg))

    async def async_send(self, msg: Any) -> Any:
        """Send the message to the server

        Connect to the server, then pack and send the message to the server,
        then wait for and return the response from the server.
        """
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_unix_connection(path=self.fname), timeout=3
            )
        except (ConnectionRefusedError, FileNotFoundError):
            raise IPCError("Could not open {}".format(self.fname))

        try:
            send_data = _IPC.pack(msg, is_json=self.is_json)
            writer.write(send_data)
            writer.write_eof()

            read_data = await asyncio.wait_for(reader.read(), timeout=10)
        except asyncio.TimeoutError:
            raise IPCError("Server not responding")
        finally:
            # see the note in Server._server_callback()
            writer.close()
            if sys.version_info >= (3, 7):
                await writer.wait_closed()
            else:
                await asyncio.sleep(0)

        data, _ = _IPC.unpack(read_data, is_json=self.is_json)

        return data


class Server:
    def __init__(self, fname: str, handler) -> None:
        self.fname = fname
        self.handler = handler
        self.server = None  # type: Optional[asyncio.AbstractServer]

        if os.path.exists(fname):
            os.unlink(fname)

        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM, 0)
        flags = fcntl.fcntl(self.sock.fileno(), fcntl.F_GETFD)
        fcntl.fcntl(self.sock.fileno(), fcntl.F_SETFD, flags | fcntl.FD_CLOEXEC)
        self.sock.bind(self.fname)

    async def _server_callback(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Callback when a connection is made to the server

        Read the data sent from the client, execute the requested command, and
        send the reply back to the client.
        """
        try:
            logger.debug("Connection made to server")
            data = await reader.read()
            logger.debug("EOF received by server")

            req, is_json = _IPC.unpack(data)
        except IPCError:
            logger.warn("Invalid data received, closing connection")
        else:
            if req[1] == "restart":
                # if we are going to restart, close the connection first, as we won't be back
                logger.debug("Closing connection on restart")
                writer.write_eof()

            rep = self.handler(req)

            result = _IPC.pack(rep, is_json=is_json)

            logger.debug("Sending result on receive EOF")
            writer.write(result)
            logger.debug("Closing connection on receive EOF")
            writer.write_eof()
        finally:
            # the resoure isn't closed immediately on the close call, but is on
            # the next loop iteration, this is exposed as the wait_closed
            # method in 3.7, but requires a manual loop iteration in earlier
            # versions
            writer.close()
            if sys.version_info >= (3, 7):
                await writer.wait_closed()
            else:
                await asyncio.sleep(0)

    async def __aenter__(self) -> "Server":
        """Start and return the server"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_value, tb) -> None:
        """Close and shutdown the server"""
        await self.close()

    async def start(self) -> None:
        """Start the server"""
        assert self.server is None

        logger.debug("Starting server")
        server_coroutine = asyncio.start_unix_server(
            self._server_callback, sock=self.sock
        )
        self.server = await server_coroutine

    async def close(self) -> None:
        """Close and shutdown the server"""
        assert self.server is not None

        logger.debug("Stopping server on close")
        self.server.close()
        await self.server.wait_closed()

        self.server = None
