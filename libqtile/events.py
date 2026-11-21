from __future__ import annotations

import asyncio
import contextlib
import json
import math
import os
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Self

from libqtile import hook
from libqtile.log_utils import logger

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

PROTOCOL_VERSION = 1

# Clients whose unsent backlog exceeds this are disconnected rather than
# allowed to grow qtile's memory use or stall the event loop.
MAX_WRITE_BUFFER = 256 * 1024

# Longest line we accept from a client.
MAX_LINE = 64 * 1024

WILDCARD = "*"

# Unpaired surrogates are not valid Unicode and so are not allowed in I-JSON strings.
SURROGATES = re.compile("[\ud800-\udfff]")

serializers: list[tuple[type, Callable[[Any], Any]]] | None = None


def load_serializers() -> list[tuple[type, Callable[[Any], Any]]]:
    """Defines a list of serialisers for qtile object types."""
    from libqtile.backend.base import Window
    from libqtile.config import Screen
    from libqtile.group import _Group
    from libqtile.layout.base import Layout

    def window(w: Window) -> dict[str, Any]:
        group = getattr(w, "group", None)
        return {
            "wid": w.wid,
            "name": w.name,
            "group": group.name if group is not None else None,
        }

    def group(g: _Group) -> dict[str, Any]:
        return {
            "name": g.name,
            "windows": [window(w) for w in g.windows],
            "screen": screen(g.screen) if g.screen else None,
        }

    def screen(s: Screen) -> dict[str, Any]:
        return {"index": s.index}

    def layout(layout_: Layout) -> dict[str, Any]:
        return {"name": layout_.name}

    return [
        (Window, window),
        (_Group, group),
        (Screen, screen),
        (Layout, layout),
    ]


def to_jsonable(obj: Any, _depth: int = 0) -> Any:
    """
    Convert a hook argument into something ``json.dumps`` accepts.

    Known qtile objects become small dicts of stable fields. Unknown objects
    fall back to ``repr`` so that a new hook argument type can never break the
    feed. The result is valid JSON (and I-JSON): non-finite floats become
    ``None`` and unpaired surrogates in strings are replaced.
    """
    global serializers

    if obj is None or isinstance(obj, (bool, int)):
        return obj
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, str):
        return SURROGATES.sub("\ufffd", obj)
    if _depth > 4:
        return repr(obj)
    if isinstance(obj, (list, tuple, set)):
        return [to_jsonable(o, _depth + 1) for o in obj]
    if isinstance(obj, dict):
        return {
            SURROGATES.sub("\ufffd", str(k)): to_jsonable(v, _depth + 1) for k, v in obj.items()
        }

    if serializers is None:
        serializers = load_serializers()
    for cls, fn in serializers:
        if isinstance(obj, cls):
            try:
                return fn(obj)
            except Exception:
                logger.exception("Failed to serialize %r", obj)
                return repr(obj)
    return repr(obj)


def encode_message(message: dict[str, Any]) -> bytes:
    """Encode one protocol message as a line of strict JSON."""
    return (json.dumps(message, allow_nan=False) + "\n").encode()


@dataclass(eq=False)
class EventClient:
    writer: asyncio.StreamWriter
    # None means "everything".
    events: set[str] | None = None

    def wants(self, event: str) -> bool:
        return self.events is None or event in self.events


class EventServer:
    """
    Publish qtile hook events to subscribed clients.

    Clients connect to a Unix socket (default is current qtile socket plus ".events").
    Every message, in both directions, is a single JSON object terminated by a newline.
    Every message has a ``type`` member. Receivers ignore unknown types and unknown members.

    Client -> server:

        {"type": "subscribe", "events": ["client_new", "setgroup"]}   replace the event filter
        {"type": "subscribe", "events": null}                         receive everything (default)
        {"type": "subscribe", "events": ["*"]}                        receive everything

    Server -> client:

        {"type": "hello", "version": 1}
        {"type": "event", "event": "<hook name>", "args": [<jsonable>, ...]}

    ``args`` mirror what the hook was fired with, converted to serialisable data with
    `to_jsonable`. A ``kwargs`` object is added only if the hook was fired with keyword arguments.
    """

    def __init__(self, path: str) -> None:
        self.path = path
        self.clients: set[EventClient] = set()
        self.server: asyncio.AbstractServer | None = None

    async def start(self) -> None:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(self.path)

        self.server = await asyncio.start_unix_server(
            self.handle_new_client, path=self.path, limit=MAX_LINE
        )

        hook.add_observer(self.publish)

    async def stop(self) -> None:
        hook.remove_observer(self.publish)
        if self.server is not None:
            self.server.close()
        for client in list(self.clients):
            self.remove_client(client)
        if self.server is not None:
            await self.server.wait_closed()
            self.server = None
        with contextlib.suppress(FileNotFoundError):
            os.unlink(self.path)

    async def __aenter__(self) -> Self:
        """Start and return the event server"""
        await self.start()
        return self

    async def __aexit__(self, _exc_type, _exc_value, _tb) -> None:
        """Close and shutdown the event server"""
        await self.stop()

    def publish(self, event: str, *args: Any, **kwargs: Any) -> None:
        """
        Publish an event to subscribed clients.

        Must be called on the event loop's thread, like ``hook.fire``.
        """
        targets = [c for c in self.clients if c.wants(event)]
        if not targets:
            return
        line = self.encode_event(
            event,
            [to_jsonable(a) for a in args],
            {k: to_jsonable(v) for k, v in kwargs.items()},
        )
        for client in targets:
            self.send_to_client(client, line)

    @staticmethod
    def encode_event(event: str, args: list[Any], kwargs: dict[str, Any] | None = None) -> bytes:
        msg: dict[str, Any] = {"type": "event", "event": event, "args": args}
        if kwargs:
            msg["kwargs"] = kwargs
        return encode_message(msg)

    def send_to_client(self, client: EventClient, line: bytes) -> None:
        transport = client.writer.transport
        if transport.is_closing():
            self.remove_client(client)
        elif transport.get_write_buffer_size() > MAX_WRITE_BUFFER:
            logger.warning("Disconnecting slow event-feed client")
            self.remove_client(client)
        else:
            client.writer.write(line)

    def remove_client(self, client: EventClient) -> None:
        self.clients.discard(client)
        # abort(), not close(): close() flushes the write buffer first, which never
        # finishes for a stuck client, leaving the socket open and blocking stop().
        with contextlib.suppress(Exception):
            client.writer.transport.abort()

    async def handle_new_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """
        Handles new client connection.

        Clients can update subscribed events during connection.
        """
        client = EventClient(writer)
        self.clients.add(client)
        try:
            self.send_to_client(
                client, encode_message({"type": "hello", "version": PROTOCOL_VERSION})
            )
            while True:
                try:
                    raw = await reader.readline()
                except (asyncio.LimitOverrunError, ValueError):
                    break
                if not raw:
                    break
                self.process_client_command(client, raw)
        except ConnectionError:
            pass
        finally:
            self.remove_client(client)

    def process_client_command(self, client: EventClient, raw: bytes) -> None:
        """Apply a client message. Invalid or unrecognised messages are ignored."""
        try:
            msg = json.loads(raw)
        except ValueError:
            return
        if not isinstance(msg, dict) or msg.get("type") != "subscribe" or "events" not in msg:
            return

        wanted = msg["events"]
        if wanted is None:
            client.events = None
        elif isinstance(wanted, list) and all(isinstance(w, str) for w in wanted):
            client.events = None if WILDCARD in wanted else set(wanted)
