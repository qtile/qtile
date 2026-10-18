from __future__ import annotations

import asyncio
import contextlib
import json
import os
from dataclasses import dataclass, field
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

_serializers: list[tuple[type, Callable[[Any], Any]]] | None = None


def _load_serializers() -> list[tuple[type, Callable[[Any], Any]]]:
    """Defines a list of serialisers for qtile object types."""
    from libqtile.backend.base import Static, Window
    from libqtile.config import Screen
    from libqtile.group import _Group
    from libqtile.layout.base import Layout

    def window(w: Window | Static) -> dict[str, Any]:
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

    return [(Window, window), (_Group, group), (Screen, screen), (Layout, layout)]


def to_jsonable(obj: Any, _depth: int = 0) -> Any:
    """
    Convert a hook argument into something ``json.dumps`` accepts.

    Known qtile objects become small dicts of stable fields. Unknown objects
    fall back to ``repr`` so that a new hook argument type can never break the
    feed.
    """
    global _serializers

    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if _depth > 4:
        return repr(obj)
    if isinstance(obj, (list, tuple, set, frozenset)):
        return [to_jsonable(o, _depth + 1) for o in obj]
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v, _depth + 1) for k, v in obj.items()}

    if _serializers is None:
        _serializers = _load_serializers()
    for cls, fn in _serializers:
        if isinstance(obj, cls):
            try:
                return fn(obj)
            except Exception:
                logger.exception("Failed to serialize %r", obj)
                return repr(obj)
    return repr(obj)


@dataclass(eq=False)
class _Client:
    writer: asyncio.StreamWriter
    # None means "everything".
    events: set[str] | None = None
    task: asyncio.Task | None = field(default=None, repr=False)

    def wants(self, event: str) -> bool:
        return self.events is None or event in self.events


class EventServer:
    """
    Publish qtile hook events to subscribed clients.

    Clients connect to a Unix socket (default is current qtile socket plus ".events").
    Every message, in both directions, is a single JSON object terminated by a newline.

    Client -> server:

        {"subscribe": ["client_new", "setgroup"]}       replace the event filter
        {"subscribe": null}                             receive everything (default)
        {"subscribe": ["*"]}                            receive everything

    Server -> client:

        {"event": "hello", "args": [{"version": 1}]}
        {"event": "<hook name>", "args": [<jsonable>, ...]}

    ``args`` mirror what the hook was fired with, converted to serialisable data with `to_jsonable`.
    """

    def __init__(self, path: str) -> None:
        self.path = path
        self._clients: set[_Client] = set()
        self._server: asyncio.AbstractServer | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    async def start(self) -> None:
        self._loop = asyncio.get_running_loop()
        with contextlib.suppress(FileNotFoundError):
            os.unlink(self.path)

        self._server = await asyncio.start_unix_server(
            self._handle, path=self.path, limit=MAX_LINE
        )

        hook.add_observer(self.publish)

    async def stop(self) -> None:
        hook.remove_observer(self.publish)
        if self._server is not None:
            self._server.close()
        for client in list(self._clients):
            self._remove_client(client)
        if self._server is not None:
            await self._server.wait_closed()
            self._server = None
        with contextlib.suppress(FileNotFoundError):
            os.unlink(self.path)

    async def __aenter__(self) -> Self:
        """Start and return the event server"""
        await self.start()
        return self

    async def __aexit__(self, _exc_type, _exc_value, _tb) -> None:
        """Close and shutdown the event server"""
        await self.stop()

    @property
    def has_clients(self) -> bool:
        return bool(self._clients)

    def publish(self, event: str, *args: Any, **kwargs: Any) -> None:
        """Publish an event to all subscribed clients."""
        if not self._clients:
            return

        loop = self._loop
        if loop is None:
            return
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if running is loop:
            self._publish(event, args, kwargs)
        else:
            loop.call_soon_threadsafe(self._publish, event, args, kwargs)

    def _publish(self, event: str, args: tuple[Any, ...], kwargs: dict[str, Any]) -> None:
        targets = [c for c in self._clients if c.wants(event)]
        if not targets:
            return
        line = self._encode(
            event,
            [to_jsonable(a) for a in args],
            {k: to_jsonable(v) for k, v in kwargs.items()},
        )
        for client in targets:
            self._send(client, line)

    @staticmethod
    def _encode(event: str, args: list[Any], kwargs: dict[str, Any] | None = None) -> bytes:
        msg: dict[str, Any] = {"event": event, "args": args}
        if kwargs:
            msg["kwargs"] = kwargs
        return (json.dumps(msg) + "\n").encode()

    def _send(self, client: _Client, line: bytes) -> None:
        transport = client.writer.transport
        if transport.is_closing():
            self._remove_client(client)
        elif transport.get_write_buffer_size() > MAX_WRITE_BUFFER:
            logger.warning("Disconnecting slow event-feed client")
            self._remove_client(client)
        else:
            client.writer.write(line)

    def _remove_client(self, client: _Client) -> None:
        self._clients.discard(client)
        with contextlib.suppress(Exception):
            client.writer.close()
        # Don't cancel ourselves if called from within the client's own task.
        if client.task is not None and client.task is not asyncio.current_task():
            client.task.cancel()

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """
        Handles new client connection.

        Clients can update subscribed events during connection.
        """
        client = _Client(writer, task=asyncio.current_task())
        self._clients.add(client)
        try:
            self._send(client, self._encode("hello", [{"version": PROTOCOL_VERSION}]))
            while True:
                try:
                    raw = await reader.readline()
                except (asyncio.LimitOverrunError, ValueError):
                    break
                if not raw:
                    break
                self._process_command(client, raw)
        except (ConnectionError, asyncio.CancelledError):
            pass
        finally:
            self._remove_client(client)

    def _process_command(self, client: _Client, raw: bytes) -> None:
        try:
            msg = json.loads(raw)
        except ValueError:
            return
        if not isinstance(msg, dict):
            return

        wanted = msg.get("subscribe")
        if isinstance(wanted, list) and all(isinstance(w, str) for w in wanted):
            client.events = None if WILDCARD in wanted else set(wanted)
