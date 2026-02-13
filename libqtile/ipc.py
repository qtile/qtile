"""
A simple IPC mechanism for communicating between two local processes. We
use marshal to serialize data - this means that both client and server must
run the same Python version, and that clients must be trusted (as
un-marshalling untrusted data can result in arbitrary code execution).
"""

from __future__ import annotations

import asyncio
import enum
import fcntl
import json
import os.path
import socket
import traceback
from abc import ABCMeta, abstractmethod
from collections.abc import Callable, Iterator
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

from typing_extensions import Self

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
        msg = IPCCommandMessage(**json)
        # Must always lift a message deserialized from JSON
        msg.lifted = True
        return msg

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


class Client:
    def __init__(self, socket_path: str) -> None:
        """Create a new IPC client

        Parameters
        ----------
        socket_path: str
            The file path to the file that is used to open the connection to
            the running IPC server.
        is_json: bool
            Pack and unpack messages as json
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
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_unix_connection(path=self.socket_path), timeout=3
            )
        except (ConnectionRefusedError, FileNotFoundError):
            raise IPCError(f"Could not open {self.socket_path}")

        try:
            send_data = _IPC.pack(IPCCommandMessage(*msg))
            writer.write(send_data)
            writer.write_eof()

            read_data = await asyncio.wait_for(reader.read(), timeout=10)
        except asyncio.TimeoutError:
            raise IPCError("Server not responding")
        finally:
            # see the note in Server._server_callback()
            writer.close()
            await writer.wait_closed()

        data = _IPC.unpack(read_data)
        if not isinstance(data, IPCReplyMessage):
            raise IPCError("Expected a reply message from the server")
        return data


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
        try:
            logger.debug("Connection made to server")
            data = await reader.read()
            logger.debug("EOF received by server")

            req = _IPC.unpack(data)
            if not isinstance(req, IPCCommandMessage):
                logger.error("Expected command message from client")
                return
        except IPCError as e:
            logger.warning("Invalid data received, closing connection")
            logger.debug(e)
        else:
            # Don't handle requests when session is locked
            if self.locked.is_set():
                rep = IPCReplyMessage.error({"error": "Session locked."})
            else:
                rep = self.handler(req)

            result = _IPC.pack(rep)

            logger.debug("Sending result on receive EOF")
            writer.write(result)
            logger.debug("Closing connection on receive EOF")
            writer.write_eof()
        finally:
            writer.close()
            await writer.wait_closed()

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
