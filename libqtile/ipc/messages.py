from __future__ import annotations

import enum
import json
import traceback
from abc import ABCMeta, abstractmethod
from collections.abc import Iterator
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any, Self

from libqtile.ipc import IPCError

if TYPE_CHECKING:
    from libqtile.command.graph import SelectorType


class IPCStatus(enum.IntEnum):
    SUCCESS = 0
    ERROR = 1
    EXCEPTION = 2


class MessageType(enum.StrEnum):
    COMMAND = "command"
    # Since this is just a `dict[Any]` bundled with a status,
    # it can be used for both the repl and command results. This
    # also simplifies the server's handler code, since it can always
    # return a `REPLY` message, e.g. on error.
    REPLY = "reply"
    # Maybe this could just be a repl_request?
    REPL_START = "repl_start"
    REPL_STOP = "repl_stop"
    REPL_REQUEST = "repl_request"
    # Event subscriptions
    EVENTS_SUBSCRIBE = "events_subscribe"
    EVENTS_UNSUBSCRIBE = "events_unsubscribe"
    EVENTS_NOTIFY = "events_notify"


class IPCMessage(metaclass=ABCMeta):
    """Abstract base class for all IPC messages"""

    @property
    @abstractmethod
    def message_type(self) -> MessageType:
        """Discriminator for the message type of the instance"""

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


@dataclass
class IPCReplStartMessage(IPCMessage):
    @property
    def message_type(self):
        return MessageType.REPL_START

    # This message doesn't carry any data
    def to_json(self) -> dict:
        return dict()

    @classmethod
    def from_json(cls, _json: dict) -> IPCReplStartMessage:
        return IPCReplStartMessage()

    def __iter__(self):
        return iter(())


@dataclass
class IPCReplStopMessage(IPCMessage):
    session_id: str

    @property
    def message_type(self):
        return MessageType.REPL_STOP

    def to_json(self) -> dict:
        return asdict(self)

    @classmethod
    def from_json(cls, json: dict) -> IPCReplStopMessage:
        return IPCReplStopMessage(**json)

    def __iter__(self):
        return iter(())


@dataclass
class IPCReplRequestMessage(IPCMessage):
    # We let the repl implementation decide what/how to
    # represent their messages, so we just pass them a dict
    session_id: str
    data: dict[str, Any]

    @property
    def message_type(self):
        return MessageType.REPL_REQUEST

    # This message doesn't carry any data
    def to_json(self) -> dict:
        return {**self.data, "session_id": self.session_id}

    @classmethod
    def from_json(cls, json: dict) -> IPCReplRequestMessage:
        if "session_id" not in json:
            raise IPCError("REPL request missing session id.")
        session_id = json.pop("session_id")
        return IPCReplRequestMessage(session_id, json)

    def __iter__(self):
        return iter(())


@dataclass
class IPCEventsSubscribeMessage(IPCMessage):
    events: list[str] | None = None

    @property
    def message_type(self):
        return MessageType.EVENTS_SUBSCRIBE

    def to_json(self) -> dict:
        return asdict(self)

    @classmethod
    def from_json(cls, json: dict) -> IPCEventsSubscribeMessage:
        return IPCEventsSubscribeMessage(**json)

    def __iter__(self):
        return iter(())


@dataclass
class IPCEventsUnsubscribeMessage(IPCMessage):
    @property
    def message_type(self):
        return MessageType.EVENTS_UNSUBSCRIBE

    def to_json(self) -> dict:
        return dict()

    @classmethod
    def from_json(cls, _json: dict) -> IPCEventsUnsubscribeMessage:
        return IPCEventsUnsubscribeMessage()

    def __iter__(self):
        return iter(())


@dataclass
class IPCEventsNotifyMessage(IPCMessage):
    event_name: str
    args: list[Any] = field(default_factory=list)
    kwargs: dict[str, Any] = field(default_factory=dict)

    @property
    def message_type(self):
        return MessageType.EVENTS_NOTIFY

    # This message doesn't carry any data
    def to_json(self) -> dict:
        return asdict(self)

    @classmethod
    def from_json(cls, json: dict) -> IPCEventsNotifyMessage:
        return IPCEventsNotifyMessage(**json)

    def __iter__(self):
        return iter(())


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
                # This could be made more succinct by mapping the `MessageType`
                # to the class, and then just calling `map[type].from_json(content)`.
                # On first pass, the implementation required special handling for
                # different message types, perhaps this might be useful in the future too.
                case {"message_type": MessageType.COMMAND, "content": content}:
                    return IPCCommandMessage.from_json(content)

                case {"message_type": MessageType.REPLY, "content": content}:
                    return IPCReplyMessage.from_json(content)

                case {"message_type": MessageType.REPL_START, "content": content}:
                    return IPCReplStartMessage.from_json(content)

                case {"message_type": MessageType.REPL_STOP, "content": content}:
                    return IPCReplStopMessage.from_json(content)

                case {"message_type": MessageType.REPL_REQUEST, "content": content}:
                    return IPCReplRequestMessage.from_json(content)

                case {"message_type": MessageType.EVENTS_SUBSCRIBE, "content": content}:
                    return IPCEventsSubscribeMessage.from_json(content)

                case {"message_type": MessageType.EVENTS_UNSUBSCRIBE, "content": content}:
                    return IPCEventsUnsubscribeMessage.from_json(content)

                case {"message_type": MessageType.EVENTS_NOTIFY, "content": content}:
                    return IPCEventsNotifyMessage.from_json(content)

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
