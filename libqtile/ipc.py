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
import marshal
import os.path
import socket
import struct
import traceback
from abc import ABCMeta, abstractmethod
from collections.abc import Callable, Iterator
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any, Literal

from libqtile import hook
from libqtile.log_utils import logger
from libqtile.utils import get_cache_dir

if TYPE_CHECKING:
    from libqtile.command.graph import SelectorType

HDRFORMAT = "!L"
HDRLEN = struct.calcsize(HDRFORMAT)

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


class IPCWireFormat(enum.StrEnum):
    JSON_RAW = "json_raw"
    """Formats the message data directly as a tuple/list in json"""

    JSON_TAGGED = "json_tagged"
    """Formats the message as a dict, contained within a top level
    object that includes a 'message_type'"""

    BYTES = "bytes"
    """Uses python's marshall module to en/decode the message"""


class IPCStatus(enum.IntEnum):
    SUCCESS = 0
    ERROR = 1
    EXCEPTION = 2


class IPCMessage(metaclass=ABCMeta):
    """Abstract base class for all IPC messages"""

    @property
    @abstractmethod
    def message_type(self) -> Literal["command"] | Literal["reply"]:
        """Discrimantor for the message type of the instance"""

    @abstractmethod
    def to_list(self) -> list:
        """Return the message content as a flat list (used by the JSON_RAW format)"""

    @abstractmethod
    def to_dict(self) -> dict:
        """Return the message content as a dict (used by the JSON_TAGGED)"""

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
    def message_type(self) -> Literal["command"] | Literal["reply"]:
        return "command"

    def to_list(self):
        """Follows the original IPC format"""
        return [self.selectors, self.name, self.args, self.kwargs, self.lifted]

    def to_dict(self):
        """A simple mapping with the variable names corresponding to the keys"""
        return asdict(self)

    def __iter__(self):
        return iter((self.selectors, self.name, self.args, self.kwargs, self.lifted))


@dataclass
class IPCReplyMessage(IPCMessage):
    """Represents a reply sent by the IPC server"""

    status: IPCStatus
    data: Any

    @property
    def message_type(self) -> Literal["command"] | Literal["reply"]:
        return "reply"

    def to_list(self) -> list:
        """Follows the original IPC format"""
        return [int(self.status), self.data]

    def to_dict(self) -> dict:
        return {
            # DEV: Arguably, for the JSON_TAGGED format
            # we could use a string representation here
            "status": int(self.status),
            "data": self.data,
        }

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
    def unpack(
        data: bytes, *, wire_format: IPCWireFormat | None = None
    ) -> tuple[IPCMessage, IPCWireFormat]:
        """Unpack the incoming message

        Parameters
        ----------
        data: bytes
            The incoming message to unpack
        format: IPCWireFormat | None
            The format the message should be unpacked as. If None,
            try unpacking as json first. If unsuccessful, try to fall back
            to marshalled bytes.

        Returns
        -------
        tuple[Any, bool]
            A tuple of the unpacked message and the format used
        """
        if wire_format != IPCWireFormat.BYTES:
            try:
                obj = json.loads(data.decode())
                match obj:
                    # JSON_TAGGED format
                    case {"message_type": message_type, "content": content}:
                        msg = _IPC._from_tagged_dict(message_type, content)
                        return msg, IPCWireFormat.JSON_TAGGED

                    # JSON_RAW format
                    case list():
                        msg = _IPC._from_list(obj)
                        return msg, IPCWireFormat.JSON_RAW

                    # Valid json, but invalid data
                    case _:
                        raise IPCError(
                            f"Malformed JSON message. Expected dict with 'message_type' "
                            f"or list, got: {type(obj)}"
                        )

            except (ValueError, KeyError) as e:
                if wire_format in [IPCWireFormat.JSON_RAW, IPCWireFormat.JSON_TAGGED]:
                    raise IPCError("Unable to decode json data") from e

        try:
            assert len(data) >= HDRLEN
            size = struct.unpack(HDRFORMAT, data[:HDRLEN])[0]
            assert size >= len(data[HDRLEN:])
            message = marshal.loads(data[HDRLEN : HDRLEN + size])
            # List encoding to preserve the old format of marshalled messages
            return _IPC._from_list(message), IPCWireFormat.BYTES
        except AssertionError as e:
            raise IPCError("error reading reply! (probably the socket was disconnected)") from e

    @staticmethod
    def _from_list(data: list) -> IPCMessage:
        """Construct message from an untagged list"""
        match data:
            case [selectors, name, args, kwargs, lifted]:
                return IPCCommandMessage(
                    selectors=selectors,
                    name=name,
                    # For json, args is gonna be a list,
                    # so we convert it just in case
                    args=tuple(args),
                    kwargs=kwargs,
                    lifted=lifted,
                )
            case [status, data]:
                if status not in IPCStatus:
                    raise IPCError(f"Invalid status in reply message: {status}")
                return IPCReplyMessage(status=status, data=data)
            case _:
                raise IPCError(
                    f"Malformed list message. Expected 2 or 5 elements, got: {len(data)}"
                )

    @staticmethod
    def _from_tagged_dict(message_type: str, content: dict) -> IPCMessage:
        # There could be more type validation done here
        # before trying to unpack content
        match message_type:
            case "command":
                return IPCCommandMessage(**content)
            case "reply":
                return IPCReplyMessage(**content)
            case _:
                raise IPCError(f"Unknown message type: {message_type}")

    @staticmethod
    def pack(msg: IPCMessage, *, wire_format=IPCWireFormat.BYTES) -> bytes:
        """Pack the object into a message to pass"""
        match wire_format:
            case IPCWireFormat.JSON_RAW:
                json_obj = json.dumps(msg.to_list(), default=_IPC._json_encoder)
                return json_obj.encode()

            case IPCWireFormat.JSON_TAGGED:
                json_obj = json.dumps(msg.to_dict(), default=_IPC._json_encoder)
                return json_obj.encode()

            case IPCWireFormat.BYTES:
                # List encoding to preserve the old format of marshalled messages
                msg_bytes = marshal.dumps(msg.to_list())
                size = struct.pack(HDRFORMAT, len(msg_bytes))
                return size + msg_bytes

            case _:
                raise ValueError(f"Invalid wire format: {wire_format}")

    @staticmethod
    def _json_encoder(field: Any) -> Any:
        """Convert non-serializable types to ones understood by stdlib json module"""
        if isinstance(field, set):
            return list(field)
        raise ValueError(f"Tried to JSON serialize unsupported type {type(field)}: {field}")


class Client:
    def __init__(self, socket_path: str, wire_format=IPCWireFormat.BYTES) -> None:
        """Create a new IPC client

        Parameters
        ----------
        socket_path: str
            The file path to the file that is used to open the connection to
            the running IPC server.
        wire_format: IPCWireFormat
            The format to use to communicate via IPC
        """
        self.socket_path = socket_path
        self.wire_format = wire_format

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
            send_data = _IPC.pack(IPCCommandMessage(*msg), wire_format=self.wire_format)
            writer.write(send_data)
            writer.write_eof()

            read_data = await asyncio.wait_for(reader.read(), timeout=10)
        except asyncio.TimeoutError:
            raise IPCError("Server not responding")
        finally:
            # see the note in Server._server_callback()
            writer.close()
            await writer.wait_closed()

        data, _ = _IPC.unpack(read_data, wire_format=self.wire_format)
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

            req, wire_format = _IPC.unpack(data)
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

            result = _IPC.pack(rep, wire_format=wire_format)

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
