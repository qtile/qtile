"""
A simple IPC mechanism for communicating between two local processes. Clients
must be trusted, as IPC commands such as `eval`, or the repl allow arbitrary
code execution.
"""

from __future__ import annotations

import asyncio
import enum
import fcntl
import json
import os.path
import socket
import struct
import threading
import traceback
from abc import ABCMeta, abstractmethod
from collections.abc import Callable, Coroutine, Iterator
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any, Self

from libqtile import hook
from libqtile.log_utils import logger
from libqtile.utils import get_cache_dir

if TYPE_CHECKING:
    from libqtile.command.graph import SelectorType

SOCKBASE = "qtilesocket.%s"


class IPCError(Exception):
    pass


def find_sockfile(display: str | None = None):
    """
    Finds the appropriate socket file for the given display.

    If unspecified, the socket file is determined as follows:

        - If WAYLAND_DISPLAY is set, use it.
        - else if DISPLAY is set, use that.
        - else check for the existence of a socket file for WAYLAND_DISPLAY=wayland-0
          and if it exists, use it.
        - else check for the existence of a socket file for DISPLAY=:0
          and if it exists, use it.
        - else raise an IPCError.

    """
    cache_directory = get_cache_dir()

    if display:
        return os.path.join(cache_directory, SOCKBASE % display)

    display = os.environ.get("WAYLAND_DISPLAY")
    if display:
        return os.path.join(cache_directory, SOCKBASE % display)

    display = os.environ.get("DISPLAY")
    if display:
        return os.path.join(cache_directory, SOCKBASE % display)

    sockfile = os.path.join(cache_directory, SOCKBASE % "wayland-0")
    if os.path.exists(sockfile):
        return sockfile

    sockfile = os.path.join(cache_directory, SOCKBASE % ":0")
    if os.path.exists(sockfile):
        return sockfile

    raise IPCError("Could not find socket file.")


class IPCStatus(enum.IntEnum):
    SUCCESS = 0
    ERROR = 1
    EXCEPTION = 2


class MessageType(enum.StrEnum):
    COMMAND = "command"
    REPLY = "reply"


class IPCMessage(metaclass=ABCMeta):
    """Abstract base class for all IPC messages"""

    @property
    @abstractmethod
    def message_type(self) -> MessageType:
        """Discrimantor for the message type of the instance"""

    @abstractmethod
    def to_json(self) -> dict:
        """Return the message content as a dict suitable for JSON serialization"""

    @classmethod
    @abstractmethod
    def from_json(cls, json: dict) -> Self:
        """Construct the message from a json dict"""

    @abstractmethod
    def __iter__(self) -> Iterator[Any]:
        """Enable unpacking syntax for the message"""


@dataclass
class IPCCommandMessage(IPCMessage):
    """Represents a command invoked via IPC"""

    selectors: list[SelectorType]
    name: str
    args: tuple
    kwargs: dict
    lifted: bool

    @property
    def message_type(self) -> MessageType:
        return MessageType.COMMAND

    def to_json(self):
        """A simple mapping with the variable names corresponding to the keys"""
        return asdict(self)

    @classmethod
    def from_json(cls, json: dict) -> IPCCommandMessage:
        return IPCCommandMessage(**json)

    def __iter__(self):
        return iter((self.selectors, self.name, self.args, self.kwargs, self.lifted))


@dataclass
class IPCReplyMessage(IPCMessage):
    """Represents a reply sent by the IPC server"""

    status: IPCStatus
    data: Any

    @property
    def message_type(self) -> MessageType:
        return MessageType.REPLY

    def to_json(self) -> dict:
        return {
            # DEV: Arguably, for the JSON_TAGGED format
            # we could use a string representation here
            "status": int(self.status),
            "data": self.data,
        }

    @classmethod
    def from_json(cls, json: dict) -> IPCReplyMessage:
        return IPCReplyMessage(**json)

    def __iter__(self):
        return iter((self.status, self.data))

    @staticmethod
    def success(data: Any) -> IPCReplyMessage:
        """Construct a reply message with status SUCCESS"""
        return IPCReplyMessage(status=IPCStatus.SUCCESS, data=data)

    @staticmethod
    def error(error: Any) -> IPCReplyMessage:
        """Construct a reply message with status ERROR"""
        return IPCReplyMessage(status=IPCStatus.ERROR, data=error)

    @staticmethod
    def exception(exception: Exception) -> IPCReplyMessage:
        """Construct a reply message from an exception
        with status EXCEPTION. The exception is formatted to
        provide useful information to the recipient"""
        # DEV: The original code only returned the last line
        # of the traceback, whereas this will return a list
        # containing the whole traceback
        data = traceback.format_exception(exception)
        return IPCReplyMessage(status=IPCStatus.EXCEPTION, data=data)


class _IPC:
    """A helper class to handle properly packing and unpacking messages"""

    @staticmethod
    def unpack(data: bytes) -> IPCMessage:
        """Unpack the incoming message

        Parameters
        ----------
        data: bytes
            The incoming message to unpack

        Returns
        -------
        IPCMessage
            The unpacked message
        """
        try:
            obj = json.loads(data.decode(), object_hook=_IPC._json_tuple_object_hook)
            match obj:
                case {"message_type": MessageType.COMMAND, "content": content}:
                    return IPCCommandMessage.from_json(content)

                case {"message_type": MessageType.REPLY, "content": content}:
                    return IPCReplyMessage.from_json(content)

                case {"message_type": typ, "content": _}:
                    raise IPCError(f"Unknown message type: '{typ}'")

                case _:
                    raise IPCError(
                        "Malformed JSON message. Expected dict with 'message_type' and 'content' keys"
                    )

        except (ValueError, KeyError) as e:
            raise IPCError("Unable to decode json data") from e

    @staticmethod
    def pack(msg: IPCMessage) -> bytes:
        """Pack the object into a message to pass"""
        tagged_dict = {
            "message_type": msg.message_type,
            "content": msg.to_json(),
        }
        json_obj = _IPC._HintTuplesJsonEncoder().encode(tagged_dict)
        return json_obj.encode()

    class _HintTuplesJsonEncoder(json.JSONEncoder):
        def encode(self, o):
            def hint_tuple(o):
                if isinstance(o, tuple):
                    return {"$tuple": list(o)}
                if isinstance(o, list):
                    return [hint_tuple(i) for i in o]
                if isinstance(o, dict):
                    return {key: hint_tuple(val) for key, val in o.items()}
                # This is to retain the old `_json_encoder` behavior
                # of converting a set to a list for serialization
                if isinstance(o, set):
                    return hint_tuple(list(o))
                return o

            return json.JSONEncoder.encode(self, hint_tuple(o))

    @staticmethod
    def _json_tuple_object_hook(o):
        if "$tuple" in o and len(o) == 1:
            return tuple(o["$tuple"])
        return o


class IPCStreamIO:
    """Wraps an asyncio `StreamReader` and `StreamWriter` and implements
    a simple framing protocol to handle sending and receiving IPCMessages
    """

    FRAME_HEADER_FORMAT = "!L"
    FRAME_HEADER_LENGTH = struct.calcsize(FRAME_HEADER_FORMAT)

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer

    async def write_frame(self, data: bytes):
        """Prepends the data with the frame header (length) and writes it to the writer"""
        frame_header = struct.pack(self.FRAME_HEADER_FORMAT, len(data))
        self.writer.write(frame_header)
        self.writer.write(data)
        await self.writer.drain()

    async def read_frame(self) -> bytes | None:
        """Reads the the frame header (length) and then reads and returns the expected
        number of bytes. Returns None if underlying stream has closed"""
        try:
            frame_header = await self.reader.readexactly(self.FRAME_HEADER_LENGTH)
            frame_length = struct.unpack(self.FRAME_HEADER_FORMAT, frame_header)[0]
            data = await self.reader.readexactly(frame_length)
            return data
        except asyncio.IncompleteReadError as e:
            if self.reader.at_eof():
                return None
            else:
                logger.debug(f"Received partial bytes: {e.partial!r}")
                raise IPCError("Invalid message framing, couldn't read the data")

    async def write_message(self, message: IPCMessage):
        await self.write_frame(_IPC.pack(message))

    async def read_message(self, *, timeout: float | None = None) -> IPCMessage | None:
        message_bytes = await asyncio.wait_for(self.read_frame(), timeout=timeout)
        if message_bytes is None:
            return None
        return _IPC.unpack(message_bytes)

    async def close(self):
        """Closes the connection"""
        self.writer.close()
        await self.writer.wait_closed()


class ReconnectingClient:
    def __init__(self, socket_path: str) -> None:
        """Create a new IPC client

        Parameters
        ----------
        socket_path: str
            The file path to the file that is used to open the connection to
            the running IPC server.
        """
        self.socket_path = socket_path

    def call(self, data: tuple) -> IPCReplyMessage:
        return self.send(data)

    def send(self, msg: tuple) -> IPCReplyMessage:
        """Send the message and return the response from the server

        If any exception is raised by the server, that will propogate out of
        this call.
        """
        return asyncio.run(self.async_send(msg))

    async def async_send(self, msg: tuple) -> IPCReplyMessage:
        """Send the message to the server

        Connect to the server, then pack and send the message to the server,
        then wait for and return the response from the server.
        """
        async with AsyncClient(self.socket_path) as c:
            return await c.send(IPCCommandMessage(*msg))


class PersistentClient:
    def __init__(self, socket_path: str) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()
        self._client = AsyncClient(socket_path)

    def _run[T](self, coro: Coroutine[Any, Any, T]) -> T:
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result()

    def connect(self) -> None:
        self._run(self._client.connect())

    def close(self) -> None:
        self._run(self._client.close())

    def send(self, msg: tuple) -> IPCReplyMessage:
        # Since the PersistentClient retains the connection,
        # the user should be aware of the need to close it.
        # This can be done manually via `self.close()`, or
        # using a with block. However, to remain compatible
        # with the old `Client` implementation, we're gonna
        # call `connect` ourselves here
        if not self._client.is_connected():
            # This should probably be a warning, but since none of the code
            # using an IPC client is aware of closing right now, that would
            # clutter the logs enormously
            logger.debug("send called on PersistenClient that's not connected")
            self._run(self._client.connect())

        message = IPCCommandMessage(*msg)
        return self._run(self._client.send(message))

    def __enter__(self):
        self.connect()

    def __exit__(self, _exc_type, _exc, _tb):
        self.close()


Client = ReconnectingClient


class AsyncClient:
    def __init__(self, socket_path: str) -> None:
        """Create a new asynchronous IPC client

        Parameters
        ----------
        socket_path: str
            The file path to the file that is used to open the connection to
            the running IPC server.
        """
        self.socket_path = socket_path
        self.stream: IPCStreamIO | None = None

    async def connect(self):
        """Open the unix domain socket connection to the IPC server"""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_unix_connection(path=self.socket_path), timeout=3
            )
            self.stream = IPCStreamIO(reader, writer)
        except (ConnectionRefusedError, FileNotFoundError):
            raise IPCError(f"Could not open {self.socket_path}")
        except asyncio.TimeoutError:
            raise IPCError("Connection to server timed out")

    def is_connected(self) -> bool:
        return self.stream is not None

    async def send(self, message: IPCCommandMessage) -> IPCReplyMessage:
        """Send the message to the server using the existing connection.
        `connect` must have been called, it is recommended to use async with:

        ```
        async with AsyncClient(sock_path) as c:
            c.send(my_message)
        ```
        """
        if self.stream is None:
            raise IPCError("AsyncClient is not connected, use 'async with' or call 'connect'")

        try:
            await self.stream.write_message(message)

            response = await self.stream.read_message(timeout=10.0)
            if not isinstance(response, IPCReplyMessage):
                raise IPCError("Expected a reply message from the server")

            return response
        except asyncio.TimeoutError:
            raise IPCError("Server not responding")

    async def close(self):
        if self.stream is not None:
            await self.stream.close()
            self.stream = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, _exc_type, _exc, _tb):
        assert self.stream is not None
        await self.stream.close()


class Server:
    def __init__(
        self, socket_path: str, handler: Callable[[IPCCommandMessage], IPCReplyMessage]
    ) -> None:
        self.socket_path = socket_path
        self.handler = handler
        self.server = None  # type: asyncio.AbstractServer | None

        # Use a flag to indicate if session is locked
        self.locked = asyncio.Event()
        hook.subscribe.locked(self.lock)
        hook.subscribe.unlocked(self.unlock)

        if os.path.exists(socket_path):
            os.unlink(socket_path)

        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM, 0)
        flags = fcntl.fcntl(self.sock.fileno(), fcntl.F_GETFD)
        fcntl.fcntl(self.sock.fileno(), fcntl.F_SETFD, flags | fcntl.FD_CLOEXEC)
        self.sock.bind(self.socket_path)

    def lock(self):
        self.locked.set()

    def unlock(self):
        self.locked.clear()

    async def _server_callback(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Callback when a connection is made to the server

        Read the data sent from the client, execute the requested command, and
        send the reply back to the client.
        """
        stream = IPCStreamIO(reader, writer)
        logger.debug("Connection made to server")

        try:
            while True:
                # There is no timeout here to enable long lived connections
                # by clients, without having to implement a heartbeat protocol
                # which would impose a huge burden on the current implementation.
                # Clients are assumed to be trusted, although there is no actual
                # verification mechanism for this
                req = await stream.read_message()
                # EOF
                if req is None:
                    logger.debug("Client disconnected")
                    break

                if not isinstance(req, IPCCommandMessage):
                    logger.error("Expected command message from client")
                    break

                # Don't handle requests when session is locked
                if self.locked.is_set():
                    rep = IPCReplyMessage.error({"error": "Session locked."})
                else:
                    # The handler shouldn't throw, but return an
                    # `IPCReplyMessage` with `IPCStatus.EXCEPTION`
                    rep = self.handler(req)

                logger.debug("Sending result")
                await stream.write_message(rep)
        # Consider trying to send the client an
        # `IPCReplyMessage` with `IPCStatus.EXCEPTION`
        except IPCError as e:
            logger.warning("Invalid data received, closing connection")
            logger.debug(e)
        finally:
            logger.debug("Closing connection")
            await stream.close()

    async def __aenter__(self) -> Server:
        """Start and return the server"""
        await self.start()
        return self

    async def __aexit__(self, _exc_type, _exc_value, _tb) -> None:
        """Close and shutdown the server"""
        await self.close()

    async def start(self) -> None:
        """Start the server"""
        assert self.server is None

        logger.debug("Starting server")
        server_coroutine = asyncio.start_unix_server(self._server_callback, sock=self.sock)
        self.server = await server_coroutine

    async def close(self) -> None:
        """Close and shutdown the server"""
        assert self.server is not None

        logger.debug("Stopping server on close")
        self.server.close()
        await self.server.wait_closed()

        self.server = None
